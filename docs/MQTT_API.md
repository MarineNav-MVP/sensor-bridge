```powershell
# Создай папку и файл
New-Item -ItemType Directory -Path docs -Force
notepad docs/MQTT_API.md
```

**Вставь содержимое:**

```markdown
# 📡 MQTT API Specification — Sensor Bridge ↔ FusionCore

## Broker Settings
| Параметр | Значение |
|----------|----------|
| Хост | `localhost` (или из `.env`) |
| Порт (TCP) | `1883` |
| Порт (WebSocket) | `8081` (для веб-панели) |
| QoS | `0` (at most once) |
| Retain | `false` |

---

## 🔻 Топики: Sensor Bridge → FusionCore

### `sensors/nmea/raw` (GPS нашего судна)
**Частота:** 1 Гц  
**Формат:**
```json
{
  "type": "GPRMC",
  "lat": 59.993300,
  "lon": 29.765800,
  "course": 90.0,
  "speed": 10.5,
  "timestamp": 1709750000
}
```

**Поля:**
| Поле | Тип | Описание |
|------|-----|----------|
| `lat` | float | Широта (градусы, WGS84) |
| `lon` | float | Долгота (градусы, WGS84) |
| `course` | float | Курс (0-360°, истинный) |
| `speed` | float | Скорость (узлы) |
| `timestamp` | int | Unix time (сек) |

---

### `sensors/radar/targets` (Цели в радиусе радара)
**Частота:** 0.3 Гц (~3 сек)  
**Формат:** `Array<Target>`
```json
[
  {
    "id": "TR01",
    "bearing": 45.2,
    "distance": 2.5,
    "course": 180.0,
    "speed": 12.0,
    "timestamp": 1709750000,
    "absolute_position": {
      "lat": 59.9950,
      "lon": 29.7800
    }
  }
]
```

**Поля цели:**
| Поле | Тип | Описание |
|------|-----|----------|
| `id` | string | Уникальный ID цели |
| `bearing` | float | Пеленг относительно курса (0-360°) |
| `distance` | float | Дистанция (морские мили) |
| `course` | float | Курс цели (0-360°) |
| `speed` | float | Скорость цели (узлы) |
| `absolute_position` | object | Абсолютные координаты (опционально) |

---

### `camera/status` (Статус камеры)
**Частота:** 2 Гц  
**Формат:**
```json
{
  "pan": 45.0,
  "tilt": -5.0,
  "zoom": 2,
  "moving": false,
  "timestamp": 1709750000
}
```

---

### `sensors/world_state` (Все суда — для отладки)
**Частота:** 5 Гц  
**Формат:**
```json
{
  "own_ship": {
    "lat": 59.9933,
    "lon": 29.7658,
    "course": 90.0,
    "speed": 10.5
  },
  "all_targets": [
    {
      "id": "TR01",
      "course": 180.0,
      "speed": 12.0,
      "absolute_position": {
        "lat": 59.9950,
        "lon": 29.7800
      }
    }
  ],
  "timestamp": 1709750000
}
```

> ⚠️ **Не используй для принятия решений** — только для визуализации/отладки.

---

## 🔺 Топики: FusionCore → Sensor Bridge

### `control/ptz/command` (Управление камерой)
**Частота:** По событию  
**Формат:**
```json
{
  "pan": 45.0,
  "tilt": -5.0,
  "zoom": 2,
  "speed": 50,
  "mode": "absolute"
}
```

**Поля:**
| Поле | Тип | Диапазон | Описание |
|------|-----|----------|----------|
| `pan` | float | -180…+180 | Угол поворота (0° = по курсу) |
| `tilt` | float | -30…+30 | Угол наклона (- = вниз) |
| `zoom` | int | 1…10 | Кратность увеличения |
| `speed` | int | 1…100 | Скорость движения (% от макс) |
| `mode` | string | `absolute`/`relative`/`stop` | Режим управления |

**Режимы:**
- `absolute`: установить точные углы
- `relative`: повернуть относительно текущего (+/- градусов)
- `stop`: остановить движение

---

### `control/simulation/command` (Управление симуляцией)
**Формат:**
```json
{"action": "start", "scenario": "crossing_starboard", "timescale": 1.0}
{"action": "stop"}
{"action": "timescale", "value": 10.0}
```

---

## 🧪 Тестирование интеграции

### 1. Проверка подключения
```bash
# Подписаться на все топики
mosquitto_sub -h localhost -t "sensors/#" -v
mosquitto_sub -h localhost -t "control/#" -v
```

### 2. Отправка тестовой команды
```bash
# Повернуть камеру на 45°
mosquitto_pub -h localhost -t "control/ptz/command" \
  -m '{"pan":45.0,"tilt":0,"zoom":1,"speed":50,"mode":"absolute"}'
```

### 3. Валидация данных
- [ ] `lat/lon` в диапазоне -90…+90 / -180…+180
- [ ] `course` в 0…360
- [ ] `speed` >= 0
- [ ] `bearing` в 0…360
- [ ] `distance` >= 0

---

## 🔄 Обработка ошибок

| Ситуация | Действие FusionCore |
|----------|-------------------|
| Нет данных > 5 сек | Логировать предупреждение, использовать последнее известное |
| Некорректный JSON | Игнорировать сообщение, логировать ошибку |
| Камера не отвечает | Повторить команду 1 раз, затем логировать |
| Конфликт команд | Последняя команда имеет приоритет |

---

## 📦 Пример кода для FusionCore (Python)

```python
# fusioncore_template.py
import paho.mqtt.client as mqtt
import json
import time
from core.camera_utils import calculate_camera_pan_tilt  # из Sensor Bridge

class FusionCore:
    def __init__(self, host="localhost", port=1883):
        self.client = mqtt.Client(client_id="fusioncore")
        self.client.connect(host, port)
        self.client.subscribe("sensors/radar/targets")
        self.client.on_message = self.on_radar_data
        self.targets = []
        
    def select_target(self, targets):
        """🎯 ТВОЯ ЛОГИКА: выбери цель для трекинга"""
        # Пример: ближайшая опасная цель
        dangerous = [t for t in targets if t['distance'] < 3.0]
        return min(dangerous, key=lambda t: t['distance']) if dangerous else None
    
    def on_radar_data(self, client, userdata, msg):
        targets = json.loads(msg.payload.decode())
        target = self.select_target(targets)
        
        if target:
            # Рассчитать углы камеры
            pan, tilt = calculate_camera_pan_tilt(
                target['bearing'], 
                target['distance']
            )
            self.send_ptz_command(pan, tilt, zoom=2)
    
    def send_ptz_command(self, pan, tilt, zoom):
        cmd = {"pan": pan, "tilt": tilt, "zoom": zoom, "speed": 50, "mode": "absolute"}
        self.client.publish("control/ptz/command", json.dumps(cmd))
        print(f"📷 Camera: pan={pan}°, tilt={tilt}°, zoom={zoom}")
    
    def run(self):
        print("🚀 FusionCore started")
        self.client.loop_forever()

if __name__ == "__main__":
    fc = FusionCore()
    fc.run()
```

---

## 📝 Чек-лист интеграции

- [ ] FusionCore подключается к MQTT брокеру
- [ ] Получает `sensors/radar/targets` и парсит JSON
- [ ] Реализует `select_target()` с критериями МППСС
- [ ] Рассчитывает `pan/tilt` через `calculate_camera_pan_tilt`
- [ ] Отправляет `control/ptz/command` в правильном формате
- [ ] Обрабатывает ошибки (таймауты, некорректные данные)
- [ ] Тестирует на всех 3 сценариях (crossing, head-on, overtaking)

---

## 🆘 Поддержка

**Вопросы по API:**  
- Создай Issue в репозитории Sensor Bridge  
- Или напиши в `docs/CONTACT.md`

**Версия API:** `v1.0` (от 2026-04-09)
```
