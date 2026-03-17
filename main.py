"""
# SensorBridge Module

Модуль для эмуляции сенсоров судна (GPS + Радар).

## Что делает:
- Эмулирует GPS-приёмник (координаты, курс, скорость своего судна)
- Эмулирует радар (обнаружение целей: пеленг, дистанция, курс, скорость)
- Публикует данные в MQTT-топики

## Топики MQTT:
- `sensors/nmea/raw` — данные GPS своего судна
- `sensors/radar/targets` — цели от радара (массив)

## Как запустить:
1. Установи зависимости: `pip install -r requirements.txt`
2. Настрой `.env` (адрес брокера, интервал)
3. Запусти: `python main.py`

## Контракты:
https://github.com/dlameros/project-config/blob/main/CONTRACTS.md
"""

# main.py - SensorBridge: GPS + Радар эмулятор
import os
import time
import json
import random
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

# Загружаем настройки
load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
TOPIC_NMEA = os.getenv("TOPIC_NMEA_RAW", "sensors/nmea/raw")
TOPIC_RADAR = os.getenv("TOPIC_RADAR_TARGETS", "sensors/radar/targets")
INTERVAL = int(os.getenv("EMULATOR_INTERVAL_SECONDS", 3))

# Счётчик целей радара
target_counter = 0

# Координаты своего судна (будем менять для имитации движения)
own_lat = 55.751244
own_lon = 37.618423
own_course = 180.0
own_speed = 10.5

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ SensorBridge подключен к {MQTT_HOST}:{MQTT_PORT}")
    else:
        print(f"❌ Ошибка подключения. Код: {rc}")

def generate_gps_data():
    """Генерирует данные GPS своего судна"""
    global own_lat, own_lon
    # Немного меняем координаты (имитация движения)
    own_lat += 0.0001
    own_lon += 0.0001
    
    return {
        "type": "GPRMC",
        "lat": round(own_lat, 6),
        "lon": round(own_lon, 6),
        "course": own_course,
        "speed": own_speed,
        "timestamp": int(time.time())
    }

def generate_radar_targets():
    """Генерирует 1-3 цели радара"""
    global target_counter
    num_targets = random.randint(1, 3)
    targets = []
    
    for _ in range(num_targets):
        target_counter += 1
        targets.append({
            "id": f"R{target_counter:02d}",
            "bearing": round(random.uniform(0, 360), 2),
            "distance": round(random.uniform(0.5, 10), 2),
            "course": round(random.uniform(0, 360), 2),
            "speed": round(random.uniform(5, 20), 1),
            "timestamp": int(time.time())
        })
    
    return targets

# Создаем клиента
client = mqtt.Client(client_id="sensor-bridge")
client.on_connect = on_connect

# Подключаемся
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()

# Ждем подключения
time.sleep(1)

print("🚀 SensorBridge запущен!")
print(f"📤 GPS → {TOPIC_NMEA}")
print(f"📤 Радар → {TOPIC_RADAR}")
print(f"⏱ Интервал: {INTERVAL} сек.")
print("👉 Нажми Ctrl+C для остановки\n")

# Основной цикл
try:
    while True:
        # 1. Отправляем GPS
        gps_data = generate_gps_data()
        client.publish(TOPIC_NMEA, json.dumps(gps_data))
        print(f"📡 GPS: {gps_data['lat']:.6f}, {gps_data['lon']:.6f}, курс={gps_data['course']}°")
        
        # 2. Отправляем цели радара
        radar_targets = generate_radar_targets()
        client.publish(TOPIC_RADAR, json.dumps(radar_targets))
        print(f"📡 Радар: {len(radar_targets)} целей (R{target_counter - len(radar_targets) + 1:02d}-R{target_counter:02d})")
        
        print("-" * 50)
        
        time.sleep(INTERVAL)
        
except KeyboardInterrupt:
    print("\n👋 SensorBridge остановлен")
    client.loop_stop()
    client.disconnect()