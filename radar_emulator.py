# radar_emulator.py - Эмулятор радара с циклической отправкой целей
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
TOPIC_RADAR = os.getenv("TOPIC_RADAR_TARGETS", "sensors/radar/targets")
INTERVAL = int(os.getenv("EMULATOR_INTERVAL_SECONDS", 3))

# Счётчик целей (для уникальных ID)
target_counter = 0

def generate_fake_target():
    """Генерирует одну фейковую цель радара"""
    global target_counter
    target_counter += 1
    
    return {
        "id": f"R{target_counter:02d}",
        "bearing": round(random.uniform(0, 360), 2),    # Пеленг 0-360°
        "distance": round(random.uniform(0.5, 10), 2),  # Дистанция 0.5-10 миль
        "course": round(random.uniform(0, 360), 2),     # Курс цели
        "speed": round(random.uniform(5, 20), 1),       # Скорость 5-20 узлов
        "timestamp": int(time.time())
    }

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Эмулятор радара подключен к {MQTT_HOST}:{MQTT_PORT}")
    else:
        print(f"❌ Ошибка подключения. Код: {rc}")

# Создаем клиента
client = mqtt.Client(client_id="radar-emulator")
client.on_connect = on_connect

# Подключаемся
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()

# Ждем подключения
time.sleep(1)

print(f"📡 Эмулятор радара запущен. Интервал: {INTERVAL} сек.")
print(f"📤 Публикация в топик: {TOPIC_RADAR}")
print("👉 Нажми Ctrl+C для остановки\n")

# Основной цикл
try:
    while True:
        # Генерируем 1-3 цели за раз (как реальный радар)
        num_targets = random.randint(1, 3)
        targets = [generate_fake_target() for _ in range(num_targets)]
        
        # Отправляем массив целей
        client.publish(TOPIC_RADAR, json.dumps(targets))
        
        print(f"📤 Отправлено {num_targets} целей:")
        for t in targets:
            print(f"   • {t['id']}: пеленг={t['bearing']}°, дистанция={t['distance']}миль")
        
        time.sleep(INTERVAL)
        
except KeyboardInterrupt:
    print("\n👋 Эмулятор остановлен")
    client.loop_stop()
    client.disconnect()