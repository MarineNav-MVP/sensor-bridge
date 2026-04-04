# main.py - SensorBridge с реалистичной физикой и живым трафиком

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
from core.ship_state import ShipState, Position, Controls, RadarTarget
from core.ship_dynamics import ShipDynamics, ShipParameters, Environment
from sensors.gps_emulator import GPSEmulator
from sensors.radar_emulator import RadarEmulator

# Загружаем настройки из .env
load_dotenv()

# === КОНФИГУРАЦИЯ ===
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
SHIP_TYPE = os.getenv("SHIP_TYPE", "cargo")
USE_CURRENT = os.getenv("USE_CURRENT", "false").lower() == "true"
CURRENT_SPEED = float(os.getenv("CURRENT_SPEED", "2.0"))
CURRENT_DIRECTION = float(os.getenv("CURRENT_DIRECTION", "90.0"))

# Режим управления
STEERING_MODE = os.getenv("STEERING_MODE", "manual")
MANUAL_COURSE = float(os.getenv("MANUAL_COURSE", "180.0"))
MANUAL_SPEED = float(os.getenv("MANUAL_SPEED", "10.5"))

# Режим целей (random, traffic, scenario)
TARGET_MODE = os.getenv("TARGET_MODE", "random")
AREA_CONFIG = os.getenv("AREA_CONFIG", "config/ports.json")
SCENARIO_NAME = os.getenv("SCENARIO_NAME", "")

# Будущее: подписка на команды
LISTEN_FOR_COMMANDS = os.getenv("LISTEN_FOR_COMMANDS", "false").lower() == "true"
COMMAND_TOPIC = os.getenv("COMMAND_TOPIC", "control/autopilot/command")

# Глобальное состояние
connected = False
client = None
external_command = None


def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        print(f"✅ Подключено к MQTT брокеру {MQTT_HOST}:{MQTT_PORT}")
        connected = True
        if LISTEN_FOR_COMMANDS:
            client.subscribe(COMMAND_TOPIC)
            print(f"📡 Подписка на {COMMAND_TOPIC}")
    else:
        print(f"❌ Ошибка подключения. Код: {rc}")
        connected = False


def on_message(client, userdata, msg):
    global external_command
    if LISTEN_FOR_COMMANDS and msg.topic == COMMAND_TOPIC:
        try:
            external_command = json.loads(msg.payload.decode())
            print(f"📥 Получена команда: {external_command}")
        except Exception as e:
            print(f"❌ Ошибка парсинга команды: {e}")


def on_disconnect(client, userdata, rc):
    global connected
    print("🔌 Отключено от брокера")
    connected = False


def create_own_ship() -> ShipState:
    return ShipState(
        position=Position(lat=OWN_LAT, lon=OWN_LON),
        course=OWN_COURSE,
        speed=OWN_SPEED,
        timestamp=time.time(),
        ship_id="OWN",
        ship_type=SHIP_TYPE
    )


def create_environment() -> Environment:
    if USE_CURRENT:
        return Environment(
            current_speed=CURRENT_SPEED,
            current_direction=CURRENT_DIRECTION
        )
    return Environment.calm()


def main():
    global connected, client
    
    print("🚀 SensorBridge запускается (с физикой и трафиком)...")
    print("=" * 70)
    print(f"📍 Позиция: {OWN_LAT}, {OWN_LON}")
    print(f"🧭 Курс: {OWN_COURSE}°, Скорость: {OWN_SPEED} уз")
    print(f"🚢 Тип: {SHIP_TYPE}")
    print(f"🎛 Управление: {STEERING_MODE}")
    print(f"🎯 Цели: {TARGET_MODE}")
    print(f"📡 MQTT: {MQTT_HOST}:{MQTT_PORT}")
    print("=" * 70)
    
    # === ИНИЦИАЛИЗАЦИЯ ===
    ship_params = ShipParameters.for_type(SHIP_TYPE)
    dynamics = ShipDynamics(ship_params)
    gps_emulator = GPSEmulator(update_rate=1.0, noise_std=0.00001)
    radar_emulator = RadarEmulator(range_nm=12.0, update_interval=UPDATE_INTERVAL)
    environment = create_environment()
    
    # Инициализация целей
    traffic = None
    scenario_targets = []
    moving_targets = []
    current_target_mode = TARGET_MODE  # ✅ Копируем в локальную переменную
    
    if current_target_mode == "traffic":
        from sensors.traffic_emulator import TrafficEmulator
        traffic = TrafficEmulator(config_path=AREA_CONFIG)
        print(f"🚢 Трафик: {len(traffic.ships)} судов")
    elif current_target_mode == "scenario" and SCENARIO_NAME:
        from scenarios.loader import load_scenario
        try:
            scenario_path = f"scenarios/{SCENARIO_NAME}.json"
            scenario_data = load_scenario(scenario_path)
            scenario_targets = scenario_data.get('targets', [])
            print(f"📋 Сценарий: {scenario_data['name']} ({len(scenario_targets)} целей)")
        except Exception as e:
            print(f"⚠️ Ошибка сценария: {e}. Режим: random")
            current_target_mode = "random"  # ✅ Меняем локальную копию
    else:
        print("🎲 Цели: рандомные")
    
    own_ship = create_own_ship()
    controls = Controls(throttle=0.5, rudder_angle=0.0)
    
    # MQTT подключение
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    print(f"\n🔄 Подключение к {MQTT_HOST}:{MQTT_PORT}...")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    time.sleep(1)
    
    if not connected:
        print("❌ Нет подключения к брокеру!")
        return
    
    print("\n🎉 SensorBridge готов!\n")
    
    last_update = time.time()
    
    try:
        while True:
            current_time = time.time()
            delta = current_time - last_update
            
            # === 1. Управление ===
            if STEERING_MODE == "manual":
                controls = Controls(throttle=1.0 if MANUAL_SPEED > 0 else 0.0, rudder_angle=0.0)
                # Физику применим ниже, а курс/скорость перезапишем ПОСЛЕ неё
                own_ship.course = MANUAL_COURSE % 360
                own_ship.speed = MANUAL_SPEED
            elif STEERING_MODE == "steady":
                course_error = (MANUAL_COURSE - own_ship.course + 180) % 360 - 180
                rudder_angle = max(-35.0, min(35.0, course_error * 1.5))
                speed_error = MANUAL_SPEED - own_ship.speed
                throttle = max(0.0, min(1.0, 0.5 + speed_error * 0.1))
                controls = Controls(throttle=throttle, rudder_angle=rudder_angle)
            elif STEERING_MODE == "external" and external_command:
                controls = Controls(
                    throttle=external_command.get('throttle', 0.5),
                    rudder_angle=external_command.get('rudder', 0.0)
                )
            
            # === 2. Физика ===
            own_ship = dynamics.update(own_ship, controls, delta, environment)
            
            # В ручном режиме перезаписываем курс/скорость (чтобы не падали от сопротивления)
            if STEERING_MODE == "manual":
                own_ship.course = MANUAL_COURSE % 360
                own_ship.speed = MANUAL_SPEED
            
            # === 3. GPS ===
            gps_json = gps_emulator.generate_json(own_ship)
            client.publish(TOPIC_NMEA_RAW, json.dumps(gps_json))
            
            # === 4. Цели радара ===
            radar_targets = []
            
            if current_target_mode == "traffic" and traffic:
                traffic.update(delta)
                targets_data = traffic.get_radar_targets(own_ship, range_nm=12.0)

                # 🔍 ОТЛАДКА: покажи все суда
                print(f"   📊 Всего судов в трафике: {len(traffic.ships)}")
                for ship in traffic.ships:
                    dist = own_ship.position.distance_to(ship.state.position)
                    print(f"      • {ship.id}: {ship.state.position.lat:.4f}, {ship.state.position.lon:.4f} (дистанция: {dist:.2f} NM)")
                
                print(f"   ✅ Видим целей радаром: {len(targets_data)}")
    
                for t in targets_data:
                    
                    # Создаём RadarTarget с absolute_position
                    rt = RadarTarget(
                        target_id=t['id'], 
                        bearing=t['bearing'], 
                        distance=t['distance'],
                        course=t['course'], 
                        speed=t['speed'], 
                        timestamp=t['timestamp']
                    )
                    # Добавляем абсолютную позицию отдельно (для карты)
                    if 'absolute_position' in t:
                        rt.absolute_position = t['absolute_position']
                    radar_targets.append(rt)
            elif current_target_mode == "scenario" and scenario_targets:
                # Для сценария используем статичные данные (упрощённо)
                radar_targets = radar_emulator.update(own_ship, scenario_targets=scenario_targets)
            else:
                radar_targets = radar_emulator.update(own_ship, num_targets=random.randint(1, 3))
            
            # Публикация целей
            client.publish(TOPIC_RADAR_TARGETS, json.dumps([t.to_dict() for t in radar_targets]))
            
            # === 5. Вывод ===
            print(f"📡 GPS: {own_ship.position.lat:.6f}, {own_ship.position.lon:.6f} | "
                  f"Курс={own_ship.course:5.1f}° | Скорость={own_ship.speed:5.1f} уз")
            print(f"   Радар: {len(radar_targets)} целей ({TARGET_MODE})")
            
            # NMEA строки
            for sentence in gps_emulator.generate_nmea_sentences(own_ship):
                client.publish(TOPIC_NMEA_STRING, sentence)
            for target in radar_targets:
                client.publish(TOPIC_NMEA_STRING, radar_emulator.generate_nmea_ttm(target))
            
            last_update = current_time
            time.sleep(UPDATE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n👋 Остановка...")
    finally:
        client.loop_stop()
        client.disconnect()
        print("✅ SensorBridge остановлен")


if __name__ == "__main__":
    main()