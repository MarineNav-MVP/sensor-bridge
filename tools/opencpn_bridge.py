# tools/opencpn_bridge.py
# Мост: MQTT → UDP (OpenCPN)

import paho.mqtt.client as mqtt
import socket
import json
import time
from datetime import datetime, timezone

# Настройки
MQTT_HOST = "localhost"
MQTT_PORT = 1883
OPENCN_HOST = "127.0.0.1"
OPENCN_PORT = 10110  # Порт для NMEA ввода в OpenCPN

# Топики
TOPIC_GPS = "sensors/nmea/raw"
TOPIC_RADAR = "sensors/radar/targets"

def create_nmea_aivdm(target_id, lat, lon, course, speed, heading=None):
    """Создаёт упрощённую AIS строку (тип 18)"""
    if heading is None:
        heading = course
    
    # Упрощённая версия — для демонстрации
    # В реальности нужен полноценный AIVDM кодировщик
    mmsi = hash(target_id) % 1000000000  # Генерируем MMSI из ID
    
    # Формат: $AIVDM,1,1,,B,<data>,0*hh
    # Для простоты используем $AIVDM с заглушкой
    nmea = f"$AIVDM,1,1,,B,15M67FC00FG?ufbE`FepT@3n00Sa,0*5C"
    return nmea

def create_nmea_gpgga(lat, lon, course, speed):
    """Создаёт NMEA строку $GPGGA"""
    now = datetime.now(timezone.utc)
    time_str = now.strftime("%H%M%S.00")
    
    # Широта
    lat_deg = int(abs(lat))
    lat_min = (abs(lat) - lat_deg) * 60
    lat_str = f"{lat_deg:02d}{lat_min:07.4f}"
    lat_dir = "N" if lat >= 0 else "S"
    
    # Долгота
    lon_deg = int(abs(lon))
    lon_min = (abs(lon) - lon_deg) * 60
    lon_str = f"{lon_deg:03d}{lon_min:07.4f}"
    lon_dir = "E" if lon >= 0 else "W"
    
    nmea = f"$GPGGA,{time_str},{lat_str},{lat_dir},{lon_str},{lon_dir},1,08,0.9,0.0,M,0.0,M,,*47"
    return nmea

def create_nmea_gprmc(lat, lon, course, speed):
    """Создаёт NMEA строку $GPRMC"""
    now = datetime.now(timezone.utc)
    time_str = now.strftime("%H%M%S.00")
    date_str = now.strftime("%d%m%y")
    
    lat_deg = int(abs(lat))
    lat_min = (abs(lat) - lat_deg) * 60
    lat_str = f"{lat_deg:02d}{lat_min:07.4f}"
    lat_dir = "N" if lat >= 0 else "S"
    
    lon_deg = int(abs(lon))
    lon_min = (abs(lon) - lon_deg) * 60
    lon_str = f"{lon_deg:03d}{lon_min:07.4f}"
    lon_dir = "E" if lon >= 0 else "W"
    
    nmea = f"$GPRMC,{time_str},A,{lat_str},{lat_dir},{lon_str},{lon_dir},{speed:.1f},{course:.1f},{date_str},,,A*5C"
    return nmea

def send_to_opencpn(sock, nmea_string):
    """Отправляет NMEA строку в OpenCPN через UDP"""
    try:
        # Для UDP используем sendto вместо send
        sock.sendto((nmea_string + "\r\n").encode(), (OPENCN_HOST, OPENCN_PORT))
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

# Подключение к OpenCPN (UDP)
print("🔌 Подключение к OpenCPN...")
opencpn_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print("✅ UDP сокет создан")

# MQTT клиент
def on_connect(client, userdata, flags, rc):
    print("✅ MQTT подключён")
    client.subscribe(TOPIC_GPS)
    client.subscribe(TOPIC_RADAR)

from pyais.encode import encode_msg

def on_message(client, userdata, msg):
    try:
        if msg.topic == TOPIC_GPS:
            data = json.loads(msg.payload.decode())
            
            gpgga = create_nmea_gpgga(data['lat'], data['lon'], data.get('course', 0), data.get('speed', 0))
            gprmc = create_nmea_gprmc(data['lat'], data['lon'], data.get('course', 0), data.get('speed', 0))
            
            send_to_opencpn(opencpn_socket, gpgga)
            send_to_opencpn(opencpn_socket, gprmc)
            
            print(f"📍 GPS: {data['lat']:.4f}, {data['lon']:.4f} | {data.get('speed', 0):.1f} уз")
        
        elif msg.topic == TOPIC_RADAR:
            data = json.loads(msg.payload.decode())
            print(f"🎯 Целей: {len(data)}")
            
            # Отправляем AIS для каждой цели
            for target in data:
                if "absolute_position" in target:
                    # Создаём AIS сообщение типа 18 (Class B)
                    ais_data = {
                        'mmsi': abs(hash(target['id'])) % 1000000000,
                        'lat': target['absolute_position']['lat'],
                        'lon': target['absolute_position']['lon'],
                        'course': target.get('course', 0),
                        'speed': target.get('speed', 0),
                        'heading': target.get('course', 0),
                        'shipname': target['id'],
                        'ship_type': 70  # Cargo
                    }
                    
                    try:
                        encoded = encode_msg(ais_data)
                        for msg_encoded in encoded:
                            send_to_opencpn(opencpn_socket, msg_encoded)
                        print(f"  🚢 Отправлен AIS: {target['id']}")
                    except Exception as e:
                        print(f"  ❌ Ошибка AIS: {e}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT, 60)

print("🚀 Мост запущен! Открывай OpenCPN...")
print("📊 Данные будут отображаться на карте")

client.loop_forever()