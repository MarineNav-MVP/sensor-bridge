# FusionCore Integration Guide

Инструкция по интеграции Sensor Bridge с модулем FusionCore (Computer Vision).

## Обзор

Sensor Bridge предоставляет эмулированные данные сенсоров для модуля FusionCore, который отвечает за:
- Обработку видео с камеры PTZ
- Детекцию объектов в кадре
- Классификацию целей (судно, буй, препятствие)
- Определение пеленга и дистанции до объектов

**Направление интеграции:**
```
Sensor Bridge ──MQTT──▶ FusionCore
   (данные)              (обработка)
   
FusionCore ──MQTT──▶ Sensor Bridge
  (команды камере)      (эмуляция)
```

---

## Архитектура взаимодействия

### Компоненты Sensor Bridge

| Компонент | Описание | MQTT топики |
|-----------|----------|-------------|
| GPS Emulator | Эмуляция NMEA данных | `sensors/nmea/raw` |
| Radar Emulator | Эмуляция радиолокационных целей | `sensors/radar/targets` |
| Camera Emulator | Эмуляция PTZ камеры | `sensors/camera/status`, `control/ptz/command` |
| Scenario Engine | Управление сценариями МППСС | `control/scenario/*` |

### Компоненты FusionCore (ожидаемые)

```python
# Ожидаемая структура модуля FusionCore
fusioncore/
├── camera_controller.py    # Управление PTZ через MQTT
├── object_detector.py      # Детекция объектов на видео
├── target_tracker.py       # Трекинг целей между кадрами
└── mqtt_interface.py       # MQTT клиент для обмена данными
```

---

## Настройка подключения

### 1. Конфигурация MQTT

Создайте файл `.env` в директории FusionCore:

```bash
# .env
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_CLIENT_ID=fusioncore_001
MQTT_USERNAME=  # опционально
MQTT_PASSWORD=  # опционально
```

### 2. Подписка на топики

FusionCore должен подписаться на следующие топики:

```python
import paho.mqtt.client as mqtt
import json

class FusionCoreMQTT:
    def __init__(self):
        self.client = mqtt.Client(client_id="fusioncore_001")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def connect(self, host="localhost", port=1883):
        self.client.connect(host, port, 60)
        
    def subscribe_to_sensors(self):
        """Подписка на все сенсорные топики"""
        topics = [
            ("sensors/nmea/raw", 0),           # QoS 0
            ("sensors/camera/status", 0),      # QoS 0
            ("control/scenario/status", 0),    # QoS 0
        ]
        self.client.subscribe(topics)
        
    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        self.subscribe_to_sensors()
        
    def on_message(self, client, userdata, msg):
        data = json.loads(msg.payload.decode())
        
        if msg.topic == "sensors/nmea/raw":
            self.handle_gps_data(data)
        elif msg.topic == "sensors/camera/status":
            self.handle_camera_status(data)
        elif msg.topic == "control/scenario/status":
            self.handle_scenario_status(data)
    
    def handle_gps_data(self, data):
        """Обработка GPS данных"""
        lat = data.get("lat")
        lon = data.get("lon")
        course = data.get("course")
        speed = data.get("speed")
        # Интегрировать с системой навигации
        
    def handle_camera_status(self, data):
        """Обработка статуса камеры"""
        pan = data.get("pan")
        tilt = data.get("tilt")
        zoom = data.get("zoom")
        # Обновить внутреннее состояние камеры
        
    def handle_scenario_status(self, data):
        """Обработка статуса сценария"""
        state = data.get("state")
        own_ship = data.get("own_ship")
        target_ship = data.get("target_ship")
        # Использовать для контекстной обработки
```

---

## Управление камерой PTZ

### Отправка команд

FusionCore может управлять камерой через топік `control/ptz/command`.

#### Режим абсолютных координат

```python
def move_camera_absolute(self, pan, tilt, zoom=1, speed=50):
    """
    Повернуть камеру на указанные углы
    
    Args:
        pan: Горизонтальный угол (-180..+180 градусов)
        tilt: Вертикальный угол (-90..+90 градусов)
        zoom: Уровень зума (1-10)
        speed: Скорость движения (0-100)
    """
    command = {
        "pan": pan,
        "tilt": tilt,
        "zoom": zoom,
        "speed": speed,
        "mode": "absolute"
    }
    self.client.publish("control/ptz/command", json.dumps(command), qos=1)

# Пример: посмотреть направо
move_camera_absolute(90.0, 0.0, zoom=3)
```

#### Режим непрерывного движения

```python
def move_camera_continuous(self, direction, speed=50):
    """
    Непрерывное движение камеры
    
    Args:
        direction: 'left', 'right', 'up', 'down', 'stop'
        speed: Скорость движения (0-100)
    """
    command = {
        "direction": direction,
        "speed": speed,
        "mode": "continuous"
    }
    self.client.publish("control/ptz/command", json.dumps(command), qos=1)

# Пример: сканирование по горизонтали
move_camera_continuous("right", speed=30)

# Остановка
move_camera_continuous("stop")
```

### Автосопровождение цели

Пример реализации автосопровождения detected объекта:

```python
class CameraTracker:
    def __init__(self, mqtt_client):
        self.mqtt = mqtt_client
        self.current_pan = 0.0
        self.current_tilt = 0.0
        
    def track_object(self, object_x, object_y, frame_width, frame_height):
        """
        Поворот камеры к объекту в кадре
        
        Args:
            object_x, object_y: Координаты центра объекта (пиксели)
            frame_width, frame_height: Размеры кадра (пиксели)
        """
        # Вычисление смещения от центра кадра
        center_x = frame_width / 2
        center_y = frame_height / 2
        
        offset_x = object_x - center_x
        offset_y = object_y - center_y
        
        # Преобразование в углы (зависит от FOV камеры)
        fov_horizontal = 60.0  # градусов
        fov_vertical = 40.0    # градусов
        
        delta_pan = (offset_x / frame_width) * fov_horizontal
        delta_tilt = -(offset_y / frame_height) * fov_vertical  # инвертировано
        
        # Новая целевая позиция
        target_pan = self.current_pan + delta_pan
        target_tilt = self.current_tilt + delta_tilt
        
        # Ограничение диапазонов
        target_pan = max(-180, min(180, target_pan))
        target_tilt = max(-90, min(90, target_tilt))
        
        # Отправка команды
        self.mqtt.move_camera_absolute(target_pan, target_tilt)
        
        # Обновление текущего состояния
        self.current_pan = target_pan
        self.current_tilt = target_tilt
```

---

## Получение данных о целях

### Обработка радарных данных

```python
def handle_radar_targets(self, data):
    """
    Обработка данных радара для корреляции с визуальными объектами
    
    Args:
        data: Сообщение из топика sensors/radar/targets
    """
    targets = data.get("targets", [])
    
    for target in targets:
        bearing = target.get("bearing")      # пеленг (градусы)
        range_nm = target.get("range_nm")    # дистанция (мили)
        rcs = target.get("rcs_dbsm")         # ЭПР (дБ·м²)
        
        # Преобразование в декартовы координаты относительно судна
        range_m = range_nm * 1852.0          # мили → метры
        
        target_x = range_m * math.sin(math.radians(bearing))
        target_y = range_m * math.cos(math.radians(bearing))
        
        # Использование для верификации детектированных объектов
        self.correlate_with_visual_targets(target_x, target_y, rcs)
```

### Корреляция радар-видео

```python
def correlate_with_visual_targets(self, radar_x, radar_y, rcs):
    """
    Сопоставление радарной цели с объектом на видео
    
    Логика:
    1. Получить список детектированных объектов из CV
    2. Для каждого объекта оценить пеленг (на основе pan камеры)
    3. Найти ближайшего кандидата
    4. Присвоить радарные данные (дистанция, ЭПР)
    """
    visual_objects = self.detector.get_current_objects()
    
    best_match = None
    min_distance = float('inf')
    
    for obj in visual_objects:
        # Вычисление ожидаемого положения на основе панорамирования
        expected_bearing = self.camera_pan + obj.relative_bearing
        bearing_diff = abs(expected_bearing - radar_bearing)
        
        if bearing_diff < 5.0 and bearing_diff < min_distance:  # 5° окно
            min_distance = bearing_diff
            best_match = obj
    
    if best_match:
        # Присвоение радарных данных объекту
        best_match.set_radar_data(range_nm, rcs)
        self.tracker.update_target(best_match)
```

---

## Интеграция со сценариями МППСС

### Мониторинг статуса сценария

```python
def handle_scenario_status(self, data):
    """
    Обработка статуса сценария для адаптивного поведения
    
    Доступная информация:
    - state: текущее состояние (idle/running/paused/completed)
    - own_ship: параметры собственного судна
    - target_ship: параметры целевого судна + DCPA/TCPA
    """
    state = data.get("state")
    
    if state == "running":
        target = data.get("target_ship", {})
        dcpa = target.get("dcpa_nm", 0)
        tcpa = target.get("tcpa_min", 0)
        
        # Адаптация частоты детекции на основе опасности
        if dcpa < 0.5 and tcpa < 10:  # Высокий риск столкновения
            self.detector.set_scan_frequency(high=True)
            self.camera_tracker.enable_high_priority_tracking()
        else:
            self.detector.set_scan_frequency(high=False)
```

### Загрузка тестовых сценариев

```python
def load_test_scenario(self, scenario_name):
    """
    Загрузка сценария для тестирования
    
    Args:
        scenario_name: 'crossing_starboard', 'head_on', 'overtaking'
    """
    command = {
        "scenario_name": scenario_name,
        "reset": True
    }
    self.client.publish("control/scenario/load", json.dumps(command), qos=1)
    
    # Старт сценария
    start_command = {"action": "start"}
    self.client.publish("control/scenario/start", json.dumps(start_command), qos=1)
```

---

## Обработка ошибок

### Восстановление соединения MQTT

```python
def on_disconnect(self, client, userdata, rc):
    """Обработка разрыва соединения"""
    print(f"Disconnected with result code {rc}")
    
    # Попытка переподключения
    reconnect_delay = 5  # секунд
    time.sleep(reconnect_delay)
    self.client.reconnect()
```

### Таймауты и валидация

```python
def process_sensor_data(self, data, timeout_ms=1000):
    """
    Обработка данных с проверкой актуальности
    
    Args:
        data: Сообщение сенсора
        timeout_ms: Максимальная задержка данных (мс)
    """
    timestamp = data.get("timestamp", 0)
    current_time = time.time()
    
    age_ms = (current_time - timestamp) * 1000
    
    if age_ms > timeout_ms:
        logger.warning(f"Stale data: {age_ms:.0f}ms old")
        return False  # Данные устарели
    
    return True  # Данные актуальны
```

---

## Пример полного класса интеграции

```python
# fusioncore/mqtt_interface.py

import paho.mqtt.client as mqtt
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class FusionCoreIntegration:
    """
    Интеграционный модуль FusionCore ↔ Sensor Bridge
    
    Usage:
        integration = FusionCoreIntegration()
        integration.connect()
        integration.start_listening()
        
        # Управление камерой
        integration.move_camera(pan=45.0, tilt=-10.0)
        
        # Загрузка сценария
        integration.load_scenario("head_on")
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.mqtt_host = self.config.get("mqtt_host", "localhost")
        self.mqtt_port = self.config.get("mqtt_port", 1883)
        self.client_id = self.config.get("client_id", "fusioncore_001")
        
        self.client = mqtt.Client(client_id=self.client_id)
        self._setup_callbacks()
        
        # Текущее состояние
        self.gps_data: Optional[Dict] = None
        self.camera_status: Optional[Dict] = None
        self.scenario_status: Optional[Dict] = None
        
    def _setup_callbacks(self):
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
    def connect(self):
        """Подключение к MQTT брокеру"""
        logger.info(f"Connecting to MQTT {self.mqtt_host}:{self.mqtt_port}")
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        
    def _on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected with result code {rc}")
        self._subscribe_to_topics()
        
    def _subscribe_to_topics(self):
        topics = [
            ("sensors/nmea/raw", 0),
            ("sensors/camera/status", 0),
            ("control/scenario/status", 0),
            ("system/health", 0),
        ]
        self.client.subscribe(topics)
        logger.info(f"Subscribed to {len(topics)} topics")
        
    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            
            if msg.topic == "sensors/nmea/raw":
                self.gps_data = data
                self._on_gps_update(data)
                
            elif msg.topic == "sensors/camera/status":
                self.camera_status = data
                self._on_camera_status_update(data)
                
            elif msg.topic == "control/scenario/status":
                self.scenario_status = data
                self._on_scenario_status_update(data)
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in topic {msg.topic}: {e}")
            
    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT (code {rc})")
        
    # === Callbacks для переопределения ===
    
    def _on_gps_update(self, data: Dict):
        """Вызывается при обновлении GPS данных"""
        pass  # Переопределить в подклассе
        
    def _on_camera_status_update(self, data: Dict):
        """Вызывается при обновлении статуса камеры"""
        pass  # Переопределить в подклассе
        
    def _on_scenario_status_update(self, data: Dict):
        """Вызывается при обновлении статуса сценария"""
        pass  # Переопределить в подклассе
        
    # === Команды управления ===
    
    def move_camera(self, pan: float, tilt: float, zoom: int = 1, speed: int = 50):
        """Переместить камеру в абсолютную позицию"""
        command = {
            "pan": pan,
            "tilt": tilt,
            "zoom": zoom,
            "speed": speed,
            "mode": "absolute"
        }
        self.client.publish("control/ptz/command", json.dumps(command), qos=1)
        
    def stop_camera(self):
        """Остановить движение камеры"""
        command = {"direction": "stop", "mode": "continuous"}
        self.client.publish("control/ptz/command", json.dumps(command), qos=1)
        
    def load_scenario(self, name: str, reset: bool = True):
        """Загрузить сценарий МППСС"""
        command = {"scenario_name": name, "reset": reset}
        self.client.publish("control/scenario/load", json.dumps(command), qos=1)
        
    def start_scenario(self):
        """Запустить загруженный сценарий"""
        command = {"action": "start"}
        self.client.publish("control/scenario/start", json.dumps(command), qos=1)
        
    def reset_system(self):
        """Сбросить систему в начальное состояние"""
        command = {"reset_all": True}
        self.client.publish("control/system/reset", json.dumps(command), qos=1)
        
    # === Основной цикл ===
    
    def start_listening(self, blocking: bool = True):
        """Запуск цикла обработки сообщений"""
        if blocking:
            self.client.loop_forever()
        else:
            self.client.loop_start()
            
    def stop(self):
        """Остановка и отключение"""
        self.client.loop_stop()
        self.client.disconnect()


# === Пример использования ===

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    class MyFusionCore(FusionCoreIntegration):
        def _on_gps_update(self, data):
            print(f"GPS: lat={data['lat']}, lon={data['lon']}")
            
        def _on_camera_status_update(self, data):
            print(f"Camera: pan={data['pan']}, tilt={data['tilt']}")
            
        def _on_scenario_status_update(self, data):
            print(f"Scenario: {data['state']}, progress={data.get('progress', 0):.1%}")
    
    # Запуск
    integration = MyFusionCore()
    integration.connect()
    integration.start_listening()
```

---

## Тестирование интеграции

### 1. Проверка подключения

```bash
# Запуск Sensor Bridge
python main.py

# В отдельном терминале - проверка MQTT
mosquitto_sub -h localhost -t "sensors/#" -v
```

### 2. Тест управления камерой

```python
from fusioncore.mqtt_interface import FusionCoreIntegration

integration = FusionCoreIntegration()
integration.connect()
integration.start_listening(blocking=False)

# Тест движения
integration.move_camera(pan=45.0, tilt=0.0)
time.sleep(2)
integration.move_camera(pan=-45.0, tilt=-10.0)
time.sleep(2)
integration.stop_camera()

integration.stop()
```

### 3. Тест сценария

```python
integration.load_scenario("crossing_starboard")
time.sleep(1)
integration.start_scenario()

# Мониторинг статуса
for i in range(60):
    if integration.scenario_status:
        print(f"State: {integration.scenario_status['state']}")
    time.sleep(1)
```

---

## Отладка

### Логирование MQTT

Включите подробное логирование paho-mqtt:

```python
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.enable_logger(logger)  # Python logging
client.logging_set_level(mqtt.MQTT_LOG_DEBUG)
```

### MQTT CLI инструменты

```bash
# Подписка на все топики
mosquitto_sub -h localhost -t "#" -v

# Публикация тестовой команды
mosquitto_pub -h localhost -t "control/ptz/command" \
  -m '{"pan":90,"tilt":0,"mode":"absolute"}'

# Просмотр дерева топиков
mosquitto_sub -h localhost -t "#" -v | grep -E "(sensors|control)"
```

---

## Частые проблемы

| Проблема | Решение |
|----------|---------|
| Нет данных от сенсоров | Проверить подключение Sensor Bridge к MQTT |
| Камера не реагирует | Проверить формат команды (обязательно поле `mode`) |
| Устаревшие данные | Проверить timestamp в сообщениях, увеличить частоту обновления |
| Разрывы соединения | Реализовать механизм реконнекта в `on_disconnect` |

---

## Контакты и поддержка

- Документация MQTT: `docs/MQTT_API.md`
- Пример заглушки: `integrations/fusioncore_stub.py`
- Спецификация топиков: раздел "MQTT API Specification"

Для вопросов по интеграции обращайтесь к команде Sensor Bridge.
