# tools/mqtt_viewer.py - Простой просмотрщик данных
import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

import paho.mqtt.client as mqtt

TOPICS = ["sensors/nmea/raw", "sensors/radar/targets"]

def on_message(client, userdata, msg):
    print(f"\n[{msg.topic}]")
    try:
        data = json.loads(msg.payload.decode())
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(msg.payload.decode())

client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883, 60)

for topic in TOPICS:
    client.subscribe(topic)
    print(f"✅ Подписка на {topic}")

print("👂 Жду данные (Ctrl+C для выхода)...\n")
client.loop_forever()