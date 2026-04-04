# test_config.py - Проверка конфига акватории

import json

with open('config/ports.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Карта:", data['name'])
print("Портов:", len(data['ports']))
print("Маршрутов:", len(data['shipping_lanes']))

print("\nПорты:")
for port in data['ports']:
    print(f"  - {port['id']}: {port['name']} ({port['lat']}, {port['lon']})")

print("\nМаршруты:")
for lane in data['shipping_lanes']:
    print(f"  - {lane['id']}: {lane['from']} -> {lane['to']}")

print("\nКонфиг валиден!")