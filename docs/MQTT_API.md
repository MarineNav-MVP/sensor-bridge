# MQTT API Specification

Полная спецификация MQTT топиков и форматов сообщений для Sensor Bridge.

## Обзор

Sensor Bridge использует MQTT broker для обмена данными между компонентами системы MarineNav.

**Broker настройки:**
- Хост: `localhost` (или из переменной `MQTT_HOST`)
- Порт: `1883` (или из переменной `MQTT_PORT`)
- QoS: `1` (at least once) для критичных данных, `0` для телеметрии
- Retain: `false` для всех динамических данных

---

## Топики сенсоров (Sensor → System)

### `sensors/nmea/raw`

NMEA-подобные данные GPS в JSON формате.

**Направление:** Sensor Bridge → FusionCore / NavLogic  
**Частота:** 1 Гц (1 сообщение в секунду)  
**QoS:** 0  
**Retain:** false

**Формат сообщения:**
```json
{
  "type": "GPRMC",
  "lat": 59.993300,
  "lon": 29.765800,
  "course": 90.0,
  "speed": 10.5,
  "timestamp": 1709750000,
  "status": "A"
}
```

**Поля:**
| Поле | Тип | Описание |
|------|-----|----------|
| `type` | string | Тип сообщения: `GPRMC`, `GPGGA`, `GPVTG` |
| `lat` | float | Широта (градусы, WGS84), -90..+90 |
| `lon` | float | Долгота (градусы, WGS84), -180..+180 |
| `course` | float | Курс относительно истинного севера (градусы), 0..360 |
| `speed` | float | Скорость относительно земли (узлы), 0..50 |
| `timestamp` | integer | Unix timestamp (секунды) |
| `status` | string | Статус: `A` = OK, `V` = warning |

**Пример:**
```json
{"type":"GPRMC","lat":59.9933,"lon":29.7658,"course":90.0,"speed":10.5,"timestamp":1709750000,"status":"A"}
```

---

### `sensors/radar/targets`

Данные о целях радара (пеленг, дистанция, скорость).

**Направление:** Sensor Bridge → FusionCore  
**Частота:** 0.5 Гц (2 секунды)  
**QoS:** 0  
**Retain:** false

**Формат сообщения:**
```json
{
  "scan_id": 12345,
  "timestamp": 1709750000,
  "targets": [
    {
      "id": "target_001",
      "bearing": 45.0,
      "range_nm": 2.5,
      "range_m": 4630.0,
      "rcs_dbsm": 10.0,
      "relative_speed": -5.2
    },
    {
      "id": "target_002",
      "bearing": 120.0,
      "range_nm": 5.0,
      "range_m": 9260.0,
      "rcs_dbsm": 15.0,
      "relative_speed": 2.1
    }
  ]
}
```

**Поля объекта `targets[]`:**
| Поле | Тип | Описание |
|------|-----|----------|
| `id` | string | Уникальный идентификатор цели |
| `bearing` | float | Пеленг на цель (градусы), 0..360 |
| `range_nm` | float | Дистанция до цели (морские мили) |
| `range_m` | float | Дистанция до цели (метры) |
| `rcs_dbsm` | float | Эффективная площадь рассеяния (дБ·м²) |
| `relative_speed` | float | Радиальная скорость (м/с), отрицательная = сближение |

**Пример:**
```json
{"scan_id":12345,"timestamp":1709750000,"targets":[{"id":"target_001","bearing":45.0,"range_nm":2.5,"range_m":4630.0,"rcs_dbsm":10.0,"relative_speed":-5.2}]}
```

---

### `sensors/camera/status`

Текущее состояние PTZ камеры.

**Направление:** Sensor Bridge → FusionCore / Web UI  
**Частота:** 1 Гц или по изменению состояния  
**QoS:** 0  
**Retain:** true (последнее известное состояние)

**Формат сообщения:**
```json
{
  "pan": 45.0,
  "tilt": -5.0,
  "zoom": 2,
  "focus": "auto",
  "mode": "absolute",
  "moving": false,
  "timestamp": 1709750000
}
```

**Поля:**
| Поле | Тип | Описание |
|------|-----|----------|
| `pan` | float | Горизонтальный угол (градусы), -180..+180 |
| `tilt` | float | Вертикальный угол (градусы), -90..+90 |
| `zoom` | integer | Уровень зума, 1..10 |
| `focus` | string | Режим фокуса: `auto`, `manual` |
| `mode` | string | Режим управления: `absolute`, `continuous` |
| `moving` | boolean | Камера в движении |
| `timestamp` | integer | Unix timestamp последнего обновления |

---

## Топики управления (System → Sensor Bridge)

### `control/ptz/command`

Команды управления PTZ камерой.

**Направление:** FusionCore / Web UI → Sensor Bridge  
**QoS:** 1  
**Retain:** false

**Формат сообщения (режим `absolute`):**
```json
{
  "pan": 45.0,
  "tilt": -5.0,
  "zoom": 2,
  "speed": 50,
  "mode": "absolute"
}
```

**Формат сообщения (режим `continuous`):**
```json
{
  "direction": "left",
  "speed": 30,
  "mode": "continuous"
}
```

**Поля:**
| Поле | Тип | Описание | Обязательность |
|------|-----|----------|----------------|
| `mode` | string | Режим: `absolute` или `continuous` | **Да** |
| `pan` | float | Целевой угол по горизонтали | Для `absolute` |
| `tilt` | float | Целевой угол по вертикали | Для `absolute` |
| `zoom` | integer | Уровень зума (1-10) | Опционально |
| `direction` | string | Направление: `left`, `right`, `up`, `down`, `stop` | Для `continuous` |
| `speed` | integer | Скорость движения (0-100) | Опционально, по умолчанию 50 |

**Примеры:**

1. Поворот камеры на абсолютный угол:
```json
{"pan":90.0,"tilt":0.0,"zoom":3,"speed":50,"mode":"absolute"}
```

2. Непрерывное движение вправо:
```json
{"direction":"right","speed":30,"mode":"continuous"}
```

3. Остановка движения:
```json
{"direction":"stop","mode":"continuous"}
```

---

### `control/scenario/load`

Загрузка сценария МППСС.

**Направление:** Web UI / Test Script → Sensor Bridge  
**QoS:** 1  
**Retain:** false

**Формат сообщения:**
```json
{
  "scenario_name": "crossing_starboard",
  "reset": true
}
```

**Поля:**
| Поле | Тип | Описание |
|------|-----|----------|
| `scenario_name` | string | Имя сценария без `.json`: `crossing_starboard`, `head_on`, `overtaking` |
| `reset` | boolean | Если `true`, сбросить текущее состояние перед запуском |

**Ответ:** Статус публикации в `control/scenario/status`

---

### `control/scenario/start`

Запуск загруженного сценария.

**Направление:** Web UI → Sensor Bridge  
**QoS:** 1  
**Retain:** false

**Формат сообщения:**
```json
{
  "action": "start"
}
```

**Варианты действия:** `start`, `pause`, `resume`, `stop`

---

### `control/system/reset`

Сброс системы в начальное состояние.

**Направление:** Web UI → Sensor Bridge  
**QoS:** 1  
**Retain:** false

**Формат сообщения:**
```json
{
  "reset_all": true
}
```

---

## Топики статуса (Sensor Bridge → System)

### `control/scenario/status`

Статус выполнения сценария.

**Направление:** Sensor Bridge → Web UI  
**Частота:** По изменению состояния  
**QoS:** 0  
**Retain:** true

**Формат сообщения:**
```json
{
  "scenario_name": "crossing_starboard",
  "state": "running",
  "progress": 0.45,
  "time_elapsed": 120.5,
  "time_remaining": 147.3,
  "own_ship": {
    "lat": 59.9933,
    "lon": 29.7658,
    "course": 90.0,
    "speed": 10.5,
    "heading": 92.0
  },
  "target_ship": {
    "lat": 60.0050,
    "lon": 29.8000,
    "course": 180.0,
    "speed": 12.0,
    "heading": 178.0,
    "distance_nm": 2.5,
    "bearing": 45.0,
    "dcpa_nm": 0.8,
    "tcpa_min": 12.5
  }
}
```

**Поля `state`:** `idle`, `loading`, `running`, `paused`, `completed`, `error`

**Поля `target_ship`:**
| Поле | Тип | Описание |
|------|-----|----------|
| `distance_nm` | float | Дистанция до цели (морские мили) |
| `bearing` | float | Пеленг на цель (градусы) |
| `dcpa_nm` | float | Дистанция кратчайшего сближения (мили) |
| `tcpa_min` | float | Время до кратчайшего сближения (минуты) |

---

### `system/health`

Статус здоровья системы.

**Направление:** Sensor Bridge → Monitoring  
**Частота:** 0.1 Гц (каждые 10 секунд)  
**QoS:** 0  
**Retain:** true

**Формат сообщения:**
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "components": {
    "gps_emulator": "ok",
    "radar_emulator": "ok",
    "camera_emulator": "ok",
    "mqtt_client": "ok",
    "scenario_engine": "ok"
  },
  "timestamp": 1709750000
}
```

**Статусы компонентов:** `ok`, `warning`, `error`, `unknown`

---

## Диаграмма потоков данных

```
┌─────────────┐     sensors/nmea/raw      ┌──────────────┐
│   GPS       │ ─────────────────────────▶│ FusionCore   │
│  Emulator   │                           │   (CV)       │
└─────────────┘                           └──────────────┘
       │                                         │
       │ sensors/radar/targets                   │ control/ptz/command
       │ ────────────────────────────────────────│
       ▼                                         ▼
┌─────────────┐                           ┌──────────────┐
│   Radar     │                           │   PTZ        │
│  Emulator   │                           │  Emulator    │
└─────────────┘                           └──────────────┘
       │                                         │
       │ control/scenario/*                      │ sensors/camera/status
       │ ◀───────────────────────────────────────│
       ▼                                         ▼
┌─────────────┐                           ┌──────────────┐
│  Scenario   │◀──── Web UI ─────────────▶│   Logger     │
│   Engine    │    control/system/*       │              │
└─────────────┘                           └──────────────┘
```

---

## Обработка ошибок

### Формат сообщений об ошибках

Топик: `system/errors`

```json
{
  "component": "scenario_engine",
  "error_code": "SCENARIO_NOT_FOUND",
  "message": "Scenario 'invalid_name' not found in scenarios/",
  "timestamp": 1709750000,
  "recoverable": true
}
```

**Коды ошибок:**

| Код | Компонент | Описание |
|-----|-----------|----------|
| `SCENARIO_NOT_FOUND` | scenario_engine | Сценарий не найден |
| `INVALID_COMMAND` | camera_emulator | Неверная команда PTZ |
| `MQTT_DISCONNECTED` | mqtt_client | Потеря соединения с брокером |
| `VALIDATION_ERROR` | scenario_engine | Ошибка валидации сценария |
| `SENSOR_TIMEOUT` | gps/radar_emulator | Таймаут получения данных сенсора |

---

## Best Practices для разработчиков

### Подписка на топики

```python
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.connect("localhost", 1883, 60)

# Подписка на все сенсоры
client.subscribe("sensors/#")

# Подписка на конкретный топік с QoS 1
client.subscribe("sensors/radar/targets", qos=1)

# Подписка с wildcard
client.subscribe("control/+/command")
```

### Публикация с обработкой ошибок

```python
try:
    result = client.publish("control/ptz/command", 
                           json.dumps(command), 
                           qos=1)
    result.wait_for_publish(timeout=5)
except Exception as e:
    logger.error(f"Failed to publish command: {e}")
```

### Отписка при завершении

```python
client.unsubscribe("control/ptz/command")
client.disconnect()
```

---

## Версионирование

Текущая версия протокола: **1.0**

При изменении формата сообщений:
- Добавить поле `protocol_version` в начало сообщения
- Сохранить обратную совместимость минимум на 1 мажорную версию
- Обновить документацию в `docs/MQTT_API.md`

Пример:
```json
{
  "protocol_version": "1.0",
  "type": "GPRMC",
  ...
}
```

---

## Контакты

По вопросам интеграции обращаться:
- Документация: `docs/` директория репозитория
- Примеры кода: `integrations/fusioncore_stub.py`
