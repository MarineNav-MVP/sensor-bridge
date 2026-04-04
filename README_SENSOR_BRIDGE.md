# 🚢 MarineNav Sensor Bridge

Модуль эмуляции сенсоров судна для тестирования алгоритмов МППСС (COLREGS).

## Архитектура

```
sensor-bridge/
├── main.py                    # Точка входа, главный цикл симуляции
├── .env                       # Конфигурация
├── requirements.txt           # Зависимости
│
├── core/                      # Физика мира
│   ├── ship_state.py          # Классы ShipState, Position, RadarTarget
│   └── ship_dynamics.py       # Физика движения судна
│
├── sensors/                   # Эмуляторы приборов
│   ├── gps_emulator.py        # GPS эмулятор
│   └── radar_emulator.py      # Радар эмулятор
│
├── scenarios/                 # JSON сценарии МППСС
│   ├── crossing_starboard.json
│   ├── head_on.json
│   └── overtaking.json
│
├── web/                       # Веб-панель управления
│   ├── index.html             # Главная страница
│   ├── map.js                 # Leaflet карта
│   ├── control.js             # MQTT управление
│   └── style.css              # Стили
│
└── tools/                     # Утилиты
    └── mqtt_viewer.py         # Просмотр MQTT сообщений
```

## MQTT Топики

| # | Топик | Направление | Формат | Частота |
|---|-------|-------------|--------|---------|
| 1 | `sensors/nmea/raw` | Publish | JSON | 1 Гц |
| 2 | `sensors/radar/targets` | Publish | JSON Array | 0.3 Гц |
| 3 | `sensors/world_state` | Publish | JSON | 0.3 Гц |
| 4 | `camera/status` | Publish | JSON | 2 Гц |
| 5 | `control/ptz/command` | Subscribe | JSON | По событию |
| 6 | `control/simulation/command` | Subscribe | JSON | По событию |

## Запуск

### 1. Запустить MQTT брокер

```bash
docker run -d -p 1883:1883 -p 9001:9001 eclipse-mosquitto
```

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

### 3. Запустить Sensor Bridge

```bash
python main.py
```

### 4. Открыть веб-панель

```bash
cd web
python -m http.server 8000
```

Открыть в браузере: http://localhost:8000

## Управление симуляцией

### Команды MQTT (JSON)

**Запуск сценария:**
```json
{"action": "start", "scenario": "crossing_starboard", "timescale": 1.0}
```

**Остановка:**
```json
{"action": "stop"}
```

**Изменение времени:**
```json
{"action": "timescale", "value": 10.0}
```

**Поворот камеры:**
```json
{"pan": 45.5, "tilt": 5.0, "zoom": 2, "speed": 50, "mode": "absolute"}
```

## Форматы сообщений

### `sensors/nmea/raw`
```json
{
  "type": "GPRMC",
  "lat": 55.751244,
  "lon": 37.618423,
  "course": 180.0,
  "speed": 10.5,
  "timestamp": 1709750000
}
```

### `sensors/radar/targets`
```json
[
  {
    "id": "TR01",
    "bearing": 45.2,
    "distance": 2.5,
    "course": 180.0,
    "speed": 12.5,
    "timestamp": 1709750000,
    "absolute_position": {"lat": 55.75, "lon": 37.62}
  }
]
```

### `sensors/world_state`
```json
{
  "own_ship": {
    "lat": 55.751244,
    "lon": 37.618423,
    "course": 180.0,
    "speed": 10.5
  },
  "all_targets": [
    {"id": "TR01", "lat": 55.75, "lon": 37.62, "course": 180.0, "speed": 12.5}
  ],
  "timestamp": 1709750000
}
```

### `camera/status`
```json
{
  "pan": 45.5,
  "tilt": 0.0,
  "zoom": 2,
  "moving": false,
  "timestamp": 1709750000
}
```

## Сценарии

Формат JSON сценария:

```json
{
  "name": "Crossing Situation",
  "own_ship": {
    "id": "OWN",
    "start": {"lat": 55.751244, "lon": 37.618423},
    "course": 0.0,
    "speed": 10.5,
    "ship_type": "cargo"
  },
  "targets": [
    {
      "id": "TR01",
      "start": {"lat": 55.752000, "lon": 37.620000},
      "course": 270.0,
      "speed": 12.0,
      "ship_type": "cargo"
    }
  ],
  "simulation": {
    "duration_min": 30,
    "update_hz": 1.0,
    "radar_range_nm": 12.0
  }
}
```

## Принципы работы

1. **Sensor Bridge не принимает решений** — только эмулирует данные
2. **Корабли «тупые»** — идут по курсу, столкновения возможны
3. **Радар фильтрует** — только цели в 12 милях
4. **Камера управляемая** — поворот по командам извне
5. **Веб-панель для людей** — управление + отладка

## Требования

- Python 3.10+
- MQTT Broker (Mosquitto)
- Веб-браузер с поддержкой WebSocket

## Лицензия

MIT
