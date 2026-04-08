# FusionCore Integration

## MQTT Flow

```
┌─────────────────┐     sensors/radar/targets     ┌──────────────────┐
│  Sensor Bridge  │ ────────────────────────────▶ │  FusionCore      │
│  (эмулятор)     │                               │  (внешний модуль)│
│                 │ ◀───────────────────────────  │                  │
└─────────────────┘   control/ptz/command         └──────────────────┘
         │
         │ camera/status
         ▼
┌─────────────────┐
│   Web-панель    │
│  (визуализация) │
└─────────────────┘
```

### Последовательность работы:

1. **Sensor Bridge** публикует данные радара в `sensors/radar/targets`
2. **FusionCore** получает список целей, выбирает одну для трекинга
3. **FusionCore** рассчитывает углы камеры (pan/tilt/zoom) для выбранной цели
4. **FusionCore** отправляет команду в `control/ptz/command`
5. **Sensor Bridge** эмулирует поворот камеры
6. **Sensor Bridge** публикует статус камеры в `camera/status` (2 Гц)
7. **Web-панель** отображает направление камеры

---

## Топики MQTT

| Топик | Направление | Формат | Частота | Описание |
|-------|-------------|--------|---------|----------|
| `sensors/radar/targets` | → | JSON Array | 1 Гц | Цели с радара (bearing, distance, absolute_position) |
| `control/ptz/command` | ← | JSON | По событию | Команда поворота камеры |
| `camera/status` | → | JSON | 2 Гц | Текущий статус камеры |

---

## Форматы сообщений

### `sensors/radar/targets` (выходящее)

```json
[
  {
    "id": "TR01",
    "bearing": 45.5,
    "distance": 2.3,
    "course": 180.0,
    "speed": 8.5,
    "absolute_position": {
      "lat": 59.9950,
      "lon": 29.7700
    },
    "relative_position": {
      "x": 1.2,
      "y": 1.8
    }
  }
]
```

### `control/ptz/command` (входящее)

```json
{
  "pan": 45.0,
  "tilt": -5.0,
  "zoom": 2,
  "speed": 50,
  "mode": "absolute"
}
```

**Параметры:**
- `pan`: Угол поворота камеры (градусы, 0 = прямо по носу судна)
- `tilt`: Угол наклона (градусы, + = вверх, - = вниз)
- `zoom`: Уровень зума (1-10)
- `speed`: Скорость поворота (градусы/сек)
- `mode`: Режим управления
  - `absolute`: Абсолютные координаты
  - `relative`: Относительное смещение
  - `continuous`: Непрерывное движение

### `camera/status` (выходящее)

```json
{
  "pan": 45.5,
  "tilt": -5.0,
  "zoom": 2,
  "moving": false,
  "timestamp": 1709750000
}
```

---

## Пример команды

```bash
# Поворот камеры на 45° вправо
mosquitto_pub -t "control/ptz/command" -m '{"pan": 45.0, "tilt": 0, "zoom": 1, "speed": 50, "mode": "absolute"}'

# Наклон камеры вниз на 5°
mosquitto_pub -t "control/ptz/command" -m '{"pan": 0, "tilt": -5.0, "zoom": 1, "speed": 30, "mode": "absolute"}'

# Увеличение зума
mosquitto_pub -t "control/ptz/command" -m '{"pan": 0, "tilt": 0, "zoom": 5, "speed": 50, "mode": "absolute"}'
```

---

## Интеграция с FusionCore

### Шаг 1: Подключение к MQTT

```python
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.connect("localhost", 1883)
client.subscribe("sensors/radar/targets")
```

### Шаг 2: Обработка данных радара

```python
def on_message(client, userdata, msg):
    targets = json.loads(msg.payload.decode('utf-8'))
    
    # Выбери цель для трекинга
    target = select_target(targets)
    
    if target:
        # Рассчитай углы камеры
        pan, tilt, zoom = calculate_angles(target)
        
        # Отправь команду камере
        send_command(pan, tilt, zoom)

client.on_message = on_message
client.loop_forever()
```

### Шаг 3: Критерии выбора цели

Примеры критериев для реализации:

- **Ближайшая цель**: минимальная дистанция
- **Самая опасная**: минимальный CPA/TCPA
- **Ручной выбор**: пользователь выбирает в веб-интерфейсе
- **Приоритет по типу**: грузовые > пассажирские > прогулочные

### Шаг 4: Расчёт углов камеры

Используй утилиты из `core/camera_utils.py`:

```python
from core.camera_utils import (
    calculate_bearing,
    calculate_distance_nm,
    calculate_relative_bearing,
    bearing_to_pan,
    elevation_to_tilt
)

# Абсолютный пеленг на цель
bearing = calculate_bearing(
    own_ship.lat, own_ship.lon,
    target.lat, target.lon
)

# Относительный пеленг (относительно курса судна)
rel_bearing = calculate_relative_bearing(own_ship.course, bearing)

# Угол pan камеры
pan = bearing_to_pan(rel_bearing)

# Угол tilt (если известна высота цели)
tilt = elevation_to_tilt(distance, target_height, camera_height)
```

---

## Тестирование

### 1. Запусти Sensor Bridge

```bash
cd /workspace
python main.py --scenario crossing_starboard
```

### 2. Открой веб-панель

```
http://localhost:8000
```

Проверь:
- Виджет камеры отображается
- Статус камеры обновляется (pan, tilt, zoom)
- Ручное управление работает (слайдеры + кнопка "Move")

### 3. Протестируй ручное управление

В веб-панели:
- Измени pan/tilt слайдерами
- Нажми "Move"
- Проверь, что камера повернулась

### 4. Запусти FusionCore Stub

```bash
python integrations/fusioncore_stub.py
```

Проверь:
- Stub подключается к MQTT
- Получает данные радара
- Отправляет команды камере

### 5. Реализуй логику в FusionCore

Открой `integrations/fusioncore_stub.py` и реализуй:

- [ ] `select_target()` — критерии выбора цели
- [ ] `calculate_camera_angles()` — расчёт углов
- [ ] Автоматическое сопровождение цели

### 6. Проверь авто-трекинг

- Запусти сценарий с целями
- Запусти FusionCore с реализованной логикой
- Камера должна автоматически поворачиваться на цель

---

## Отладка

### Просмотр топиков MQTT

```bash
# Статус камеры
mosquitto_sub -t "camera/status"

# Команды камере
mosquitto_sub -t "control/ptz/command"

# Данные радара
mosquitto_sub -t "sensors/radar/targets"
```

### Логирование

Sensor Bridge выводит логи:

```
📹 Camera emulator started
🎯 PTZ command: pan=45.0°, tilt=-5.0°, zoom=2
```

FusionCore Stub выводит логи:

```
🔗 FusionCore Stub подключён к MQTT
📡 Подписка на sensors/radar/targets
🎯 Выбрана цель: TR01
📹 Команда камере: pan=45.0°, tilt=0°, zoom=3x
```

---

## Расширение функциональности

### Идеи для улучшения:

1. **Предсказание движения**: учитывать скорость цели для упреждения
2. **Стабилизация**: сглаживание резких движений камеры
3. **Несколько целей**: переключение между целями по таймеру
4. **Распознавание**: интеграция с CV для идентификации типа судна
5. **Запись видео**: сохранение трекинга в файл

---

## Контакты

По вопросам интеграции обращайся к Леониду (разработчик FusionCore).
