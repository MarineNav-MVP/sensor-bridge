# test_subscriber.py - Проверка, что данные приходят в топик
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    """Сработает, когда придет сообщение"""
    print(f"\n ПОЛУЧЕНО ИЗ {msg.topic}:")
    try:
        data = json.loads(msg.payload.decode())
        print(f"   Данные: {data}")
        print(f"   ✅ JSON валидный!")
    except:
        print(f"   ❌ Ошибка парсинга JSON: {msg.payload.decode()}")

# Создаем клиента
client = mqtt.Client(client_id="test-subscriber")
client.on_message = on_message

# Подключаемся
print("🔄 Подключение к брокеру...")
client.connect("localhost", 1883, 60)

# Подписываемся на топик SensorBridge
client.subscribe("sensors/nmea/raw")
print("📡 Подписка на sensors/nmea/raw...")
print("👂 Жду данные (нажми Ctrl+C для выхода)\n")

# Запускаем цикл
client.loop_forever()