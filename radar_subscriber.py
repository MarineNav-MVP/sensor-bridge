# radar_subscriber.py - Проверка получения целей радара
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    """Сработает, когда придут данные радара"""
    print(f"\n📥 ПОЛУЧЕНО ИЗ {msg.topic}:")
    try:
        targets = json.loads(msg.payload.decode())
        print(f"   Количество целей: {len(targets)}")
        for t in targets:
            print(f"   • {t['id']}: пеленг={t['bearing']}°, дистанция={t['distance']}миль, курс={t['course']}°")
        print(f"   ✅ JSON валидный!")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

# Создаем клиента
client = mqtt.Client(client_id="radar-subscriber")
client.on_message = on_message

# Подключаемся
print("🔄 Подключение к брокеру...")
client.connect("localhost", 1883, 60)

# Подписываемся на топик радара
client.subscribe("sensors/radar/targets")
print("📡 Подписка на sensors/radar/targets...")
print("👂 Жду цели радара (нажми Ctrl+C для выхода)\n")

# Запускаем цикл
client.loop_forever()