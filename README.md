# Sensor Bridge

Эмулятор морских сенсоров для тестирования FusionCore (CV) и NavLogic (МППСС).

## Быстрый старт

```bash
# 1. Запуск MQTT брокера
docker run -d -p 1883:1883 eclipse-mosquitto

# 2. Установка зависимостей
pip install -r requirements.txt

# 3. Запуск эмулятора
python main.py

# 4. Запуск веб-панели (в отдельном терминале)
cd web && python -m http.server 8000
# Веб-интерфейс: http://localhost:8000
```

## Интеграция с FusionCore

Sensor Bridge предоставляет MQTT-интерфейс для подключения модуля компьютерного зрения.

### Инструкция для разработчика

1. Клонировать репозиторий:
```bash
git clone https://github.com/MarineNav-MVP/sensor-bridge.git
cd sensor-bridge
```

2. Запустить Sensor Bridge:
```bash
# MQTT брокер
docker run -d -p 1883:1883 -p 8081:8081 eclipse-mosquitto

# Sensor Bridge
pip install -r requirements.txt
python main.py
```

3. Запустить шаблон FusionCore:
```bash
# В другом терминале
pip install paho-mqtt
python integrations/fusioncore_stub.py
```

4. Реализовать логику в `integrations/fusioncore_stub.py`:
- Функция `select_target()` — выбор приоритетной цели
- Функция `calculate_camera_angles()` — расчёт углов поворота камеры

5. Протестировать:
- Запустить сценарий в веб-панели: http://localhost:8000
- Проверить реакцию камеры на выбранные цели

### Файлы интеграции

| Файл | Назначение |
|------|-----------|
| `docs/MQTT_API.md` | Спецификация топиков и форматов сообщений |
| `integrations/fusioncore_stub.py` | Шаблон для реализации логики FusionCore |
| `web/` | Веб-панель для визуальной отладки |

### Логика выбора цели (МППСС)

Приоритеты при выборе цели для сопровождения:
1. Цель с минимальным DCPA (< 0.5 мили) — риск столкновения
2. Цель в секторе 0°…180° (справа по борту) — правило 15 (пересечение курсов)
3. Встречная цель — правило 14 (оба суда поворачивают вправо)
4. Обгоняемая цель — правило 13 (обгоняющее судно уступает)

### Отладка

```bash
# Просмотр всех MQTT-сообщений
mosquitto_sub -h localhost -t "#" -v

# Тест отправки команды на поворот камеры
mosquitto_pub -h localhost -t "control/ptz/command" \
  -m '{"pan":45,"tilt":-5,"zoom":2,"speed":50,"mode":"absolute"}'
```

### Структура проекта

```
sensor-bridge/
├── main.py                 # Точка входа, эмуляция сенсоров
├── requirements.txt        # Зависимости Python
├── integrations/
│   └── fusioncore_stub.py  # Шаблон для интеграции FusionCore
├── web/                    # Веб-панель (статика)
├── docs/
│   └── MQTT_API.md         # Документация по MQTT-интерфейсу
└── README.md               # Этот файл
```

### Форматы сообщений (кратко)

**Входящие (от FusionCore):**
- Топик: `control/ptz/command`
- Payload: `{"pan": float, "tilt": float, "zoom": int, "speed": int, "mode": "absolute"|"relative"}`

**Исходящие (от Sensor Bridge):**
- Топик: `sensors/ais/targets` — список целей AIS
- Топик: `sensors/radar/contacts` — контакты радара
- Топик: `sensors/own_ship/state` — состояние собственного судна

Подробная спецификация: `docs/MQTT_API.md`