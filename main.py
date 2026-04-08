# main.py - Sensor Bridge для морского эмулятора MarineNav
# Модуль эмулирует сенсоры судна и публикует данные в MQTT

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
from scenarios.loader import load_scenario, create_moving_targets, MovingTarget

# Загружаем настройки из .env
load_dotenv()

# === КОНФИГУРАЦИЯ ===
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "sensor-bridge")

# Топики MQTT (ровно 6 штук по спецификации)
TOPIC_NMEA_RAW = "sensors/nmea/raw"
TOPIC_RADAR_TARGETS = "sensors/radar/targets"
TOPIC_WORLD_STATE = "sensors/world_state"
TOPIC_CAMERA_STATUS = "camera/status"
TOPIC_PTZ_COMMAND = "control/ptz/command"
TOPIC_SIMULATION_COMMAND = "control/simulation/command"

# Настройки эмуляции
#UPDATE_INTERVAL = float(os.getenv("UPDATE_INTERVAL", "0.02"))
RADAR_RANGE_NM = float(os.getenv("RADAR_RANGE_NM", "12.0"))
DEFAULT_TIMESCALE = float(os.getenv("DEFAULT_TIMESCALE", "1.0"))

# Глобальное состояние
connected = False
client = None
simulation_running = False
time_scale = DEFAULT_TIMESCALE
own_ship = None
moving_targets = []
camera_state = {
    "pan": 0.0,
    "tilt": 0.0,
    "zoom": 1,
    "moving": False,
    "target_pan": 0.0,
    "target_tilt": 0.0
}
last_radar_update = 0
last_world_update = 0
WORLD_STATE_HZ = 10.0  # ← 5 Гц для веб-панели

def on_connect(client, userdata, flags, rc):
    """Callback при подключении к MQTT"""
    global connected
    if rc == 0:
        print(f"✅ Подключено к MQTT брокеру {MQTT_HOST}:{MQTT_PORT}")
        connected = True
        # Подписка на команды
        client.subscribe(TOPIC_PTZ_COMMAND)
        client.subscribe(TOPIC_SIMULATION_COMMAND)
        print(f"📡 Подписка на {TOPIC_PTZ_COMMAND} и {TOPIC_SIMULATION_COMMAND}")
    else:
        print(f"❌ Ошибка подключения. Код: {rc}")
        connected = False


def on_message(client, userdata, msg):
    """Callback при получении сообщения"""
    global simulation_running, time_scale, camera_state
    
    try:
        payload = json.loads(msg.payload.decode())
        
        if msg.topic == TOPIC_SIMULATION_COMMAND:
            handle_simulation_command(payload)
        elif msg.topic == TOPIC_PTZ_COMMAND:
            handle_ptz_command(payload)
    except Exception as e:
        print(f"❌ Ошибка обработки сообщения: {e}")


def handle_simulation_command(cmd):
    """Обработка команд симуляции"""
    global simulation_running, time_scale, own_ship, moving_targets
    
    action = cmd.get("action", "")
    
    if action == "start":
        scenario_name = cmd.get("scenario", "crossing_starboard")
        time_scale = cmd.get("timescale", DEFAULT_TIMESCALE)
        start_simulation(scenario_name)
    elif action == "stop":
        simulation_running = False
        print("⏹ Симуляция остановлена")
    elif action == "timescale":
        time_scale = float(cmd.get("value", DEFAULT_TIMESCALE))
        print(f"⏩ Time scale: {time_scale}x")
    elif action == "restart":
        scenario_name = cmd.get("scenario", "crossing_starboard")
        time_scale = cmd.get("timescale", DEFAULT_TIMESCALE)
        start_simulation(scenario_name)


def handle_ptz_command(cmd):
    """Обработка команд PTZ камеры"""
    global camera_state
    
    mode = cmd.get("mode", "absolute")
    
    if mode == "stop":
        camera_state["moving"] = False
    else:
        camera_state["target_pan"] = float(cmd.get("pan", camera_state["pan"]))
        camera_state["target_tilt"] = float(cmd.get("tilt", camera_state["tilt"]))
        camera_state["zoom"] = int(cmd.get("zoom", camera_state["zoom"]))
        camera_state["moving"] = True
        print(f"📷 Камера: pan={camera_state['target_pan']}°, tilt={camera_state['target_tilt']}°, zoom={camera_state['zoom']}x")


def start_simulation(scenario_name):
    """Запуск сценария симуляции"""
    global simulation_running, own_ship, moving_targets
    
    try:
        scenario_path = f"scenarios/{scenario_name}.json"
        scenario = load_scenario(scenario_path)
        
        # Создаём наше судно из сценария
        own_data = scenario.get("own_ship", {})
        own_ship = ShipState(
            position=Position(
                lat=float(own_data.get("start", {}).get("lat", 55.751244)),
                lon=float(own_data.get("start", {}).get("lon", 37.618423))
            ),
            course=float(own_data.get("course", 0)),
            speed=float(own_data.get("speed", 10)),
            ship_id=own_data.get("id", "OWN"),
            ship_type=own_data.get("ship_type", "cargo"),
            timestamp=time.time()
        )
        
        # Создаём движущиеся цели
        moving_targets = create_moving_targets(scenario)
        
        simulation_running = True
        print(f"🚀 Запущен сценарий: {scenario_name} ({len(moving_targets)} целей)")
        
    except Exception as e:
        print(f"❌ Ошибка запуска сценария: {e}")
        simulation_running = False


def update_ship_positions(dt):
    """Обновление позиций всех судов"""
    global own_ship, moving_targets
    
    if own_ship:
        # Движение нашего судна по прямой
        distance_nm = own_ship.speed * (dt / 3600)  # мили
        course_rad = math.radians(own_ship.course)
        
        delta_lat = (distance_nm * math.cos(course_rad)) / 60
        delta_lon = (distance_nm * math.sin(course_rad)) / (60 * math.cos(math.radians(own_ship.position.lat)))
        
        own_ship.position.lat += delta_lat
        own_ship.position.lon += delta_lon
        own_ship.timestamp = time.time()
    
    # Обновление целей
    for target in moving_targets:
        target.update(dt)


def get_radar_targets():
    """Получение целей радара (в пределах 12 миль)"""
    global own_ship, moving_targets
    
    targets = []
    
    for mt in moving_targets:
        distance = own_ship.position.distance_to(mt.position)
        
        # Фильтр: только цели в радиусе 12 миль
        if distance <= RADAR_RANGE_NM:
            bearing = own_ship.position.bearing_to(mt.position)
            relative_bearing = (bearing - own_ship.course + 360) % 360
            
            targets.append({
                "id": mt.id,
                "bearing": round(relative_bearing, 2),
                "distance": round(distance, 2),
                "course": mt.course,
                "speed": mt.speed,
                "timestamp": int(time.time()),
                "absolute_position": {
                    "lat": mt.position.lat,
                    "lon": mt.position.lon
                }
            })
    
    return targets


def publish_nmea_raw():
    """Публикация данных GPS (NMEA raw)"""
    global own_ship, client
    
    if not own_ship or not client:
        return
    
    data = {
        "type": "GPRMC",
        "lat": round(own_ship.position.lat, 6),
        "lon": round(own_ship.position.lon, 6),
        "course": round(own_ship.course, 1),
        "speed": round(own_ship.speed, 1),
        "timestamp": int(own_ship.timestamp)
    }
    
    client.publish(TOPIC_NMEA_RAW, json.dumps(data))


def publish_radar_targets(targets):
    """Публикация целей радара"""
    global client
    
    if not client:
        return
    
    client.publish(TOPIC_RADAR_TARGETS, json.dumps(targets))


def publish_world_state(radar_targets):
    """Публикация полного состояния мира (для веб-панели)"""
    global own_ship, moving_targets, client
    
    if not client or not own_ship:
        return
    
    all_targets = []
    for mt in moving_targets:
        all_targets.append({
            "id": mt.id,
            "course": mt.course,
            "speed": mt.speed,
            "absolute_position": {  # ← Добавили вложенный объект!
                "lat": round(mt.position.lat, 6),
                "lon": round(mt.position.lon, 6)
            }
        })
    
    data = {
        "own_ship": {
            "lat": round(own_ship.position.lat, 6),
            "lon": round(own_ship.position.lon, 6),
            "course": round(own_ship.course, 1),
            "speed": round(own_ship.speed, 1)
        },
        "all_targets": all_targets,
        "timestamp": int(time.time())
    }
    
    client.publish(TOPIC_WORLD_STATE, json.dumps(data))


def publish_camera_status():
    """Публикация статуса камеры"""
    global camera_state, client
    
    if not client:
        return
    
    data = {
        "pan": round(camera_state["pan"], 1),
        "tilt": round(camera_state["tilt"], 1),
        "zoom": camera_state["zoom"],
        "moving": camera_state["moving"],
        "timestamp": int(time.time())
    }
    
    client.publish(TOPIC_CAMERA_STATUS, json.dumps(data))


def update_camera(dt):
    """Обновление состояния камеры (плавный поворот)"""
    global camera_state
    
    if camera_state["moving"]:
        speed = 50  # градусов в секунду
        
        # Поворот pan
        pan_diff = camera_state["target_pan"] - camera_state["pan"]
        if abs(pan_diff) > 0.1:
            step = speed * dt
            if abs(pan_diff) < step:
                camera_state["pan"] = camera_state["target_pan"]
            else:
                camera_state["pan"] += step * (1 if pan_diff > 0 else -1)
        else:
            camera_state["pan"] = camera_state["target_pan"]
        
        # Поворот tilt
        tilt_diff = camera_state["target_tilt"] - camera_state["tilt"]
        if abs(tilt_diff) > 0.1:
            step = speed * dt
            if abs(tilt_diff) < step:
                camera_state["tilt"] = camera_state["target_tilt"]
            else:
                camera_state["tilt"] += step * (1 if tilt_diff > 0 else -1)
        else:
            camera_state["tilt"] = camera_state["target_tilt"]
        
        # Проверка остановки
        if abs(pan_diff) < 0.1 and abs(tilt_diff) < 0.1:
            camera_state["moving"] = False


def main():
    """Главный цикл симуляции"""
    global connected, client, simulation_running, own_ship, time_scale, last_radar_update, last_world_update, WORLD_STATE_HZ
    
    print("=" * 60)
    print("🚢 MarineNav Sensor Bridge")
    print("=" * 60)
    print(f"📡 MQTT: {MQTT_HOST}:{MQTT_PORT}")
    print(f"🎯 Time Scale: {time_scale}x")
    print(f"📡 Радар: {RADAR_RANGE_NM} миль")
    print("=" * 60)
    
    # Инициализация MQTT
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"\n🔄 Подключение к {MQTT_HOST}:{MQTT_PORT}...")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    time.sleep(1)
    
    if not connected:
        print("❌ Нет подключения к брокеру!")
        return
    
    print("\n🎉 Sensor Bridge готов! Ожидание команд...")
    print("Команды:")
    print('  {"action": "start", "scenario": "crossing_starboard", "timescale": 1.0}')
    print('  {"action": "stop"}')
    print('  {"action": "timescale", "value": 10.0}')
    print("=" * 60)
    
    last_update = time.time()
    
    try:
        while True:
            current_time = time.time()
            dt = current_time - last_update
            last_update = current_time
            
            if simulation_running:
                # Обновление позиций с учётом time scale
                update_ship_positions(dt * time_scale)
                
                # Публикация GPS (1 Гц)
                publish_nmea_raw()
                
                # Публикация радара (0.3 Гц)
                if current_time - last_radar_update >= (1.0 / 0.3):
                    radar_targets = get_radar_targets()
                    publish_radar_targets(radar_targets)
                    publish_world_state(radar_targets)
                    last_radar_update = current_time

                    # World State (5 Гц) - только для веб-панели!
                if current_time - last_world_update >= (1.0 / WORLD_STATE_HZ):
                    publish_world_state(get_radar_targets())
                    last_world_update = current_time

                # Обновление камеры
                update_camera(dt)
                publish_camera_status()
                
                # Вывод статистики
                print(f"\r📍 {own_ship.position.lat:.6f}, {own_ship.position.lon:.6f} | "
                      f"Курс={own_ship.course:5.1f}° | Скорость={own_ship.speed:5.1f} уз | "
                      f"Целей={len(moving_targets)} (видим={len(get_radar_targets())}) | "
                      f"Time={time_scale}x", end="", flush=True)
            
            #time.sleep(UPDATE_INTERVAL)
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n\n👋 Остановка по команде пользователя...")
    finally:
        client.loop_stop()
        client.disconnect()
        print("✅ Sensor Bridge остановлен")


if __name__ == "__main__":
    main()
