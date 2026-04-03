# main.py - SensorBridge с реалистичной физикой движения

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import time
import json
import random
import math
from datetime import datetime, timezone
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

# Импорт наших модулей
from core.ship_state import ShipState, Position, Controls
from core.ship_dynamics import ShipDynamics, ShipParameters, Environment
from sensors.gps_emulator import GPSEmulator
from sensors.radar_emulator import RadarEmulator

from scenarios.loader import load_scenario, create_own_ship_from_scenario, create_targets_from_scenario

# Загружаем настройки из .env
load_dotenv()

# === КОНФИГУРАЦИЯ MQTT ===
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "sensor-bridge")

# Топики
TOPIC_NMEA_RAW = os.getenv("TOPIC_NMEA_RAW", "sensors/nmea/raw")
TOPIC_NMEA_STRING = os.getenv("TOPIC_NMEA_STRING", "sensors/nmea/raw_string")
TOPIC_RADAR_TARGETS = os.getenv("TOPIC_RADAR_TARGETS", "sensors/radar/targets")

# Настройки эмуляции
UPDATE_INTERVAL = float(os.getenv("UPDATE_INTERVAL", "3.0"))
OWN_LAT = float(os.getenv("OWN_LAT", "55.751244"))
OWN_LON = float(os.getenv("OWN_LON", "37.618423"))
OWN_COURSE = float(os.getenv("OWN_COURSE", "180.0"))
OWN_SPEED = float(os.getenv("OWN_SPEED", "10.5"))

# Настройки физики
SHIP_TYPE = os.getenv("SHIP_TYPE", "cargo")  # yacht, fishing, cargo, tanker, passenger
USE_CURRENT = os.getenv("USE_CURRENT", "false").lower() == "true"
CURRENT_SPEED = float(os.getenv("CURRENT_SPEED", "2.0"))
CURRENT_DIRECTION = float(os.getenv("CURRENT_DIRECTION", "90.0"))

# Автопилот (для тестов)
AUTOPILOT_ENABLED = os.getenv("AUTOPILOT_ENABLED", "false").lower() == "true"
TARGET_COURSE = float(os.getenv("TARGET_COURSE", "180.0"))
TARGET_SPEED = float(os.getenv("TARGET_SPEED", "10.5"))

#Сценарии
SCENARIO_NAME = os.getenv("SCENARIO_NAME", "") 

# Глобальное состояние
connected = False
client = None


def on_connect(client, userdata, flags, rc):
    """Callback при подключении к MQTT брокеру"""
    global connected
    if rc == 0:
        print(f"✅ Подключено к MQTT брокеру {MQTT_HOST}:{MQTT_PORT}")
        connected = True
    else:
        print(f"❌ Ошибка подключения. Код: {rc}")
        connected = False


def on_disconnect(client, userdata, rc):
    """Callback при отключении"""
    global connected
    print("🔌 Отключено от брокера")
    connected = False


def create_own_ship() -> ShipState:
    """Создаёт объект нашего судна с начальными параметрами"""
    return ShipState(
        position=Position(lat=OWN_LAT, lon=OWN_LON),
        course=OWN_COURSE,
        speed=OWN_SPEED,
        timestamp=time.time(),
        ship_id="OWN",
        ship_type=SHIP_TYPE
    )


def create_environment() -> Environment:
    """Создаёт объект внешних условий"""
    if USE_CURRENT:
        return Environment(
            current_speed=CURRENT_SPEED,
            current_direction=CURRENT_DIRECTION,
            wind_speed=0.0,
            wind_direction=0.0,
            wave_height=0.0
        )
    return Environment.calm()


def calculate_autopilot_controls(ship: ShipState, 
                                  target_course: float, 
                                  target_speed: float) -> Controls:
    """
    Рассчитывает управление для автопилота.
    
    Args:
        ship: Текущее состояние судна
        target_course: Целевой курс
        target_speed: Целевая скорость
        
    Returns:
        Controls с throttle и rudder_angle
    """
    # === Управление скоростью ===
    speed_error = target_speed - ship.speed
    throttle = max(0.0, min(1.0, 0.5 + speed_error * 0.1))
    
    # === Управление курсом ===
    # Разница курсов с учётом перехода через 360°
    course_error = (target_course - ship.course + 180) % 360 - 180
    
    # Пропорциональное управление рулём
    rudder_angle = max(-35.0, min(35.0, course_error * 1.5))
    
    return Controls(throttle=throttle, rudder_angle=rudder_angle)  # ✅ Исправлено


def main():
    """Основная функция SensorBridge"""
    global connected, client
    
    print("🚀 SensorBridge запускается (с физикой движения)...")
    print("=" * 70)
    print(f"📍 Начальная позиция: {OWN_LAT}, {OWN_LON}")
    print(f"🧭 Курс: {OWN_COURSE}°, Скорость: {OWN_SPEED} уз")
    print(f"🚢 Тип судна: {SHIP_TYPE}")
    print(f"🌊 Течение: {'включено' if USE_CURRENT else 'выключено'}")
    if USE_CURRENT:
        print(f"   Скорость: {CURRENT_SPEED} уз, Направление: {CURRENT_DIRECTION}°")
    print(f"🤖 Автопилот: {'включен' if AUTOPILOT_ENABLED else 'выключен'}")
    if AUTOPILOT_ENABLED:
        print(f"   Целевой курс: {TARGET_COURSE}°, Целевая скорость: {TARGET_SPEED} уз")
    print(f"📡 MQTT: {MQTT_HOST}:{MQTT_PORT}")
    print(f"📤 Топики:")
    print(f"   - {TOPIC_NMEA_RAW} (JSON)")
    print(f"   - {TOPIC_NMEA_STRING} (NMEA строки)")
    print(f"   - {TOPIC_RADAR_TARGETS} (цели)")
    print(f"⏱ Интервал обновления: {UPDATE_INTERVAL} сек")
    print("=" * 70)
    
    # === ИНИЦИАЛИЗАЦИЯ ===
    
    # Создаём параметры судна и физику
    ship_params = ShipParameters.for_type(SHIP_TYPE)
    dynamics = ShipDynamics(ship_params)
    
    print(f"\n📊 Параметры судна ({SHIP_TYPE}):")
    print(f"   Длина: {ship_params.length_m} м")
    print(f"   Водоизмещение: {ship_params.displacement_t} т")
    print(f"   Макс. скорость: {ship_params.max_speed_knots} уз")
    print(f"   Тормозной путь с {OWN_SPEED} уз: {dynamics.estimate_stop_distance(OWN_SPEED):.2f} NM")
    
    # Создаём эмуляторы
    gps_emulator = GPSEmulator(update_rate=1.0, noise_std=0.00001)
    radar_emulator = RadarEmulator(
        range_nm=12.0,
        update_interval=UPDATE_INTERVAL,
        noise_bearing=2.0,
        noise_distance=0.01
    )
    
    # === ИНИЦИАЛИЗАЦИЯ СЦЕНАРИЯ ===
    scenario_data = None
    scenario_targets = []
    
    if SCENARIO_NAME:
        try:
            scenario_path = f"scenarios/{SCENARIO_NAME}.json"
            scenario_data = load_scenario(scenario_path)
            own_ship = create_own_ship_from_scenario(scenario_data)
            scenario_targets = create_targets_from_scenario(scenario_data)
            print(f"📋 Загружен сценарий: {scenario_data['name']}")
            print(f"   Правило: {scenario_data['rule']}")
            print(f"   Описание: {scenario_data['description']}")
            print(f"   Целей: {len(scenario_targets)}")
        except FileNotFoundError:
            print(f"⚠️  Сценарий '{SCENARIO_NAME}' не найден. Используем рандомные цели.")
            own_ship = create_own_ship()
        except Exception as e:
            print(f"⚠️  Ошибка загрузки сценария: {e}. Используем рандомные цели.")
            own_ship = create_own_ship()
    else:
        own_ship = create_own_ship()
    
    environment = create_environment()
    
    # Начальное управление
    controls = Controls(throttle=0.5, rudder_angle=0.0)
    
    # Подключаемся к MQTT
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    
    print(f"\n🔄 Подключение к {MQTT_HOST}:{MQTT_PORT}...")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    
    # Ждём подключения
    time.sleep(1)
    
    if not connected:
        print("❌ Не удалось подключиться к MQTT брокеру!")
        print("Проверь: docker ps (должен работать mqtt_broker)")
        return
    
    print("\n🎉 SensorBridge готов к работе!\n")
    
    last_update = time.time()
    step_count = 0
    
    try:
        while True:
            current_time = time.time()
            delta = current_time - last_update
            
            # === 1. Обновляем управление (автопилот или ручное) ===
            if AUTOPILOT_ENABLED:
                controls = calculate_autopilot_controls(own_ship, TARGET_COURSE, TARGET_SPEED)
            
            # === 2. Обновляем состояние судна через физику ===
            own_ship = dynamics.update(own_ship, controls, delta, environment)
            
            # === 3. Генерируем GPS данные ===
            gps_nmea = gps_emulator.generate_nmea_sentences(own_ship)
            gps_json = gps_emulator.generate_json(own_ship)
            
            # Публикуем GPS JSON
            client.publish(TOPIC_NMEA_RAW, json.dumps(gps_json))
            
            # === 4. Генерируем цели радара ===
            if scenario_data and scenario_targets:
                # Используем цели из сценария
                radar_targets = radar_emulator.update(own_ship, scenario_targets=scenario_targets)
            else:
                # Рандомные цели
                radar_targets = radar_emulator.update(own_ship, num_targets=random.randint(1, 3))
            
            # Публикуем цели JSON
            client.publish(TOPIC_RADAR_TARGETS, json.dumps(radar_emulator.generate_json(radar_targets)))
            
            # === 5. Вывод в консоль ===
            step_count += 1
            if step_count % 10 == 0:  # Каждые 10 шагов печатаем подробно
                print(f"📡 GPS: {own_ship.position.lat:.6f}, {own_ship.position.lon:.6f} | "
                      f"Курс={own_ship.course:5.1f}° | Скорость={own_ship.speed:5.1f} уз | "
                      f"Руль={controls.rudder_angle:5.1f}° | Газ={controls.throttle:.2f}")
                print(f"📡 Радар: {len(radar_targets)} целей")
                if radar_targets:
                    dangerous = [t for t in radar_targets if t.cpa and t.cpa < 0.5 and t.tcpa and t.tcpa > 0]
                    if dangerous:
                        print(f"   ⚠️  ОПАСНЫЕ ЦЕЛИ: {len(dangerous)}")
                        for t in dangerous:
                            print(f"      {t.target_id}: CPA={t.cpa:.2f} NM, TCPA={t.tcpa:.1f} мин")
                print("-" * 70)
            
            # Публикуем NMEA строки (для тестов парсера)
            for sentence in gps_nmea:
                client.publish(TOPIC_NMEA_STRING, sentence)
            
            # Публикуем NMEA $TTM строки
            for target in radar_targets:
                ttm = radar_emulator.generate_nmea_ttm(target)
                client.publish(TOPIC_NMEA_STRING, ttm)
            
            last_update = current_time
            time.sleep(UPDATE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n👋 Остановка SensorBridge...")
    finally:
        client.loop_stop()
        client.disconnect()
        print("✅ SensorBridge остановлен")


if __name__ == "__main__":
    main()