# 🚢 Sensor Bridge

**MarineNav Sensor Emulator** — эмулятор морских сенсоров для тестирования FusionCore (CV) и NavLogic (МППСС).

## Статус

✅ MVP готов | 🚧 В разработке

Эмулирует:
- **GPS/NMEA** — GPRMC, GPVTG, HDT сообщения с шумом и задержкой
- **Радар** — ARPA-трекинг целей, CPA/TCPA расчёт, NMEA $TTM
- **Камера PTZ** — Pan/Tilt/Zoom управление, статус
- **Сценарии МППСС** — Crossing, Head-on, Overtaking ситуации

## Быстрый старт

### 1. Запуск MQTT брокера

```bash
docker run -d -p 1883:1883 eclipse-mosquitto
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка окружения

```bash
cp .env.example .env
# Отредактируйте .env при необходимости
```

### 4. Запуск Sensor Bridge

```bash
python main.py
```

### 5. Веб-панель для отладки

```bash
cd web && python -m http.server 8000
# Открыть: http://localhost:8000
```

## Архитектура

```
┌─────────────────┐     MQTT      ┌──────────────────┐
│   Sensor Bridge │ ◄──────────►  │   FusionCore     │
│   (эмулятор)    │               │   (Computer CV)  │
└────────┬────────┘               └──────────────────┘
         │
         │ MQTT Topics:
         ├─ sensors/nmea/raw
         ├─ sensors/radar/targets
         ├─ sensors/world_state
         ├─ camera/status
         └─ control/ptz/command
         
┌────────┴────────┐
│   NavLogic      │
│   (МППСС)       │
└─────────────────┘
```

## Структура проекта

```
sensor-bridge/
├── core/              # Бизнес-логика (config, constants, ship_state)
├── sensors/           # Эмуляторы (GPS, radar, camera)
├── scenarios/         # Сценарии МППСС (JSON)
├── integrations/      # Интеграции (MQTT, FusionCore stub)
├── web/               # Веб-панель для отладки
├── docs/              # Документация
├── tests/             # Юнит-тесты
└── main.py            # Точка входа
```

## Доступные сценарии

| Сценарий | Описание | Правило МППСС |
|----------|----------|---------------|
| `crossing_starboard` | Цель пересекает курс справа | Rule 15 |
| `head_on` | Встречное судно | Rule 14 |
| `overtaking` | Догоняющее судно | Rule 13 |

## MQTT API

Полная спецификация топиков и форматов: [`docs/MQTT_API.md`](docs/MQTT_API.md)

### Основные топики

| Топик | Направление | Частота | Описание |
|-------|-------------|---------|----------|
| `sensors/nmea/raw` | → | 1 Гц | GPS данные (GPRMC) |
| `sensors/radar/targets` | → | 0.3 Гц | Цели радара |
| `sensors/world_state` | → | 5 Гц | Полное состояние мира |
| `camera/status` | → | 1 Гц | Статус PTZ камеры |
| `control/ptz/command` | ← | on demand | Команды камере |
| `control/simulation/command` | ← | on demand | Управление симуляцией |

## Интеграция

Для разработчиков FusionCore и NavLogic:
- [`docs/FUSIONCORE_INTEGRATION.md`](docs/FUSIONCORE_INTEGRATION.md) — инструкция по интеграции
- [`integrations/fusioncore_stub.py`](integrations/fusioncore_stub.py) — пример заглушки

## Разработка

Добавить новый сценарий:
1. Создать JSON файл в `scenarios/`
2. Использовать шаблон из существующих сценариев
3. Перезапустить симуляцию с новым сценарием

Запуск тестов:
```bash
pytest tests/
```

## Лицензия

MIT