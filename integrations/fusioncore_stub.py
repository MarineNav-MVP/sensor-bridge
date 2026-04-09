"""
FusionCore Integration Stub

Пример заглушки для разработчика FusionCore (Леонид).

Этот файл демонстрирует:
1. Как подключиться к MQTT брокеру Sensor Bridge
2. Как подписаться на топики сенсоров
3. Как управлять камерой PTZ
4. Как загружать и запускать сценарии МППСС

TODO для Леонида:
- [ ] Заменить этот класс на реальную реализацию FusionCore
- [ ] Интегрировать с модулем компьютерного зрения
- [ ] Добавить обработку видео с камеры
- [ ] Реализовать детекцию объектов в кадре
- [ ] Настроить корреляцию радар-видео данные

Использование:
    python integrations/fusioncore_stub.py
"""

import paho.mqtt.client as mqtt
import json
import time
import logging
from typing import Optional, Dict, Any, List

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FusionCoreStub:
    """
    Заглушка-пример для интеграции FusionCore с Sensor Bridge.
    
    Этот класс показывает минимально необходимую функциональность
    для подключения к системе Sensor Bridge.
    
    Attributes:
        mqtt_host: Хост MQTT брокера
        mqtt_port: Порт MQTT брокера
        client_id: Уникальный идентификатор клиента
        gps_data: Последние полученные GPS данные
        camera_status: Текущий статус PTZ камеры
        scenario_status: Статус выполнения сценария
    """
    
    def __init__(self, mqtt_host: str = "localhost", mqtt_port: int = 1883):
        """
        Инициализация интеграционного модуля.
        
        Args:
            mqtt_host: Хост MQTT брокера (по умолчанию localhost)
            mqtt_port: Порт MQTT брокера (по умолчанию 1883)
        """
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.client_id = "fusioncore_stub_001"
        
        # Создание MQTT клиента
        self.client = mqtt.Client(client_id=self.client_id)
        
        # Настройка колбэков
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Текущее состояние (кэш последних данных)
        self.gps_data: Optional[Dict[str, Any]] = None
        self.camera_status: Optional[Dict[str, Any]] = None
        self.scenario_status: Optional[Dict[str, Any]] = None
        self.radar_targets: List[Dict[str, Any]] = []
        
        logger.info(f"FusionCoreStub initialized for {mqtt_host}:{mqtt_port}")
    
    def connect(self, timeout: int = 10) -> bool:
        """
        Подключение к MQTT брокеру.
        
        Args:
            timeout: Таймаут подключения в секундах
            
        Returns:
            True если подключение успешно, иначе False
        """
        try:
            logger.info(f"Connecting to MQTT broker {self.mqtt_host}:{self.mqtt_port}...")
            self.client.connect(self.mqtt_host, self.mqtt_port, timeout)
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Колбэк подключения к брокеру."""
        if rc == 0:
            logger.info("Successfully connected to MQTT broker")
            self._subscribe_to_topics()
        else:
            logger.error(f"Connection failed with result code {rc}")
    
    def _subscribe_to_topics(self):
        """Подписка на необходимые топики."""
        topics = [
            ("sensors/nmea/raw", 0),           # GPS данные, QoS 0
            ("sensors/camera/status", 0),      # Статус камеры, QoS 0
            ("sensors/radar/targets", 0),      # Цели радара, QoS 0
            ("control/scenario/status", 0),    # Статус сценария, QoS 0
            ("system/health", 0),              # Здоровье системы, QoS 0
        ]
        
        self.client.subscribe(topics)
        logger.info(f"Subscribed to {len(topics)} topics: {[t[0] for t in topics]}")
    
    def _on_message(self, client, userdata, msg):
        """Обработка входящих сообщений."""
        try:
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
            
            # Маршрутизация по топикам
            if msg.topic == "sensors/nmea/raw":
                self.gps_data = data
                self._handle_gps_update(data)
                
            elif msg.topic == "sensors/camera/status":
                self.camera_status = data
                self._handle_camera_status(data)
                
            elif msg.topic == "sensors/radar/targets":
                self.radar_targets = data.get("targets", [])
                self._handle_radar_targets(data)
                
            elif msg.topic == "control/scenario/status":
                self.scenario_status = data
                self._handle_scenario_status(data)
                
            elif msg.topic == "system/health":
                self._handle_system_health(data)
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {msg.topic}: {e}")
        except Exception as e:
            logger.error(f"Error processing message from {msg.topic}: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Колбэк отключения от брокера."""
        logger.warning(f"Disconnected from MQTT (code {rc})")
        
        # TODO: Реализовать автоматическое переподключение
        # Пример:
        # time.sleep(5)
        # self.connect()
    
    # === Обработчики событий (переопределить в наследнике) ===
    
    def _handle_gps_update(self, data: Dict[str, Any]):
        """
        Обработка обновления GPS данных.
        
        Args:
            data: Словарь с GPS данными:
                  {lat, lon, course, speed, timestamp, status}
        """
        lat = data.get("lat", 0.0)
        lon = data.get("lon", 0.0)
        course = data.get("course", 0.0)
        speed = data.get("speed", 0.0)
        
        logger.debug(f"GPS Update: lat={lat:.6f}, lon={lon:.6f}, course={course:.1f}°, speed={speed:.1f}kn")
        
        # TODO: Интегрировать с навигационной системой FusionCore
    
    def _handle_camera_status(self, data: Dict[str, Any]):
        """
        Обработка статуса PTZ камеры.
        
        Args:
            data: Словарь со статусом камеры:
                  {pan, tilt, zoom, mode, moving, timestamp}
        """
        pan = data.get("pan", 0.0)
        tilt = data.get("tilt", 0.0)
        zoom = data.get("zoom", 1)
        moving = data.get("moving", False)
        
        logger.debug(f"Camera Status: pan={pan:.1f}°, tilt={tilt:.1f}°, zoom={zoom}, moving={moving}")
        
        # TODO: Обновить внутреннее представление ориентации камеры
    
    def _handle_radar_targets(self, data: Dict[str, Any]):
        """
        Обработка данных радара о целях.
        
        Args:
            data: Словарь с данными радара:
                  {scan_id, timestamp, targets: [{id, bearing, range_nm, rcs_dbsm, ...}]}
        """
        targets = data.get("targets", [])
        scan_id = data.get("scan_id", 0)
        
        logger.debug(f"Radar Scan #{scan_id}: {len(targets)} targets detected")
        
        for target in targets[:3]:  # Логировать первые 3 цели
            target_id = target.get("id", "?")
            bearing = target.get("bearing", 0.0)
            range_nm = target.get("range_nm", 0.0)
            logger.debug(f"  Target {target_id}: bearing={bearing:.1f}°, range={range_nm:.2f}nm")
        
        # TODO: Коррелировать радарные цели с визуальными объектами
    
    def _handle_scenario_status(self, data: Dict[str, Any]):
        """
        Обработка статуса сценария МППСС.
        
        Args:
            data: Словарь со статусом сценария:
                  {scenario_name, state, progress, own_ship, target_ship, ...}
        """
        scenario = data.get("scenario_name", "?")
        state = data.get("state", "unknown")
        progress = data.get("progress", 0.0)
        
        logger.info(f"Scenario '{scenario}': state={state}, progress={progress:.1%}")
        
        # TODO: Адаптировать поведение CV на основе стадии сценария
    
    def _handle_system_health(self, data: Dict[str, Any]):
        """
        Обработка статуса здоровья системы.
        
        Args:
            data: Словарь со здоровьем компонентов:
                  {status, uptime_seconds, components: {...}}
        """
        status = data.get("status", "unknown")
        components = data.get("components", {})
        
        # Проверка критических компонентов
        critical = ["gps_emulator", "radar_emulator", "camera_emulator"]
        for comp in critical:
            comp_status = components.get(comp, "unknown")
            if comp_status != "ok":
                logger.warning(f"Component {comp} status: {comp_status}")
    
    # === Команды управления ===
    
    def move_camera_absolute(self, pan: float, tilt: float, zoom: int = 1, speed: int = 50):
        """
        Поворот камеры в абсолютную позицию.
        
        Args:
            pan: Горизонтальный угол (-180..+180 градусов)
            tilt: Вертикальный угол (-90..+90 градусов)
            zoom: Уровень зума (1-10), по умолчанию 1
            speed: Скорость движения (0-100), по умолчанию 50
        """
        command = {
            "pan": max(-180, min(180, pan)),      # Ограничение диапазона
            "tilt": max(-90, min(90, tilt)),       # Ограничение диапазона
            "zoom": max(1, min(10, zoom)),         # Ограничение диапазона
            "speed": max(0, min(100, speed)),      # Ограничение диапазона
            "mode": "absolute"
        }
        
        payload = json.dumps(command)
        self.client.publish("control/ptz/command", payload, qos=1)
        logger.info(f"Camera command: pan={pan:.1f}°, tilt={tilt:.1f}°, zoom={zoom}")
    
    def move_camera_continuous(self, direction: str, speed: int = 50):
        """
        Непрерывное движение камеры.
        
        Args:
            direction: Направление: 'left', 'right', 'up', 'down', 'stop'
            speed: Скорость движения (0-100)
        """
        valid_directions = ["left", "right", "up", "down", "stop"]
        if direction not in valid_directions:
            logger.error(f"Invalid direction: {direction}. Must be one of {valid_directions}")
            return
        
        command = {
            "direction": direction,
            "speed": max(0, min(100, speed)),
            "mode": "continuous"
        }
        
        payload = json.dumps(command)
        self.client.publish("control/ptz/command", payload, qos=1)
        logger.info(f"Camera continuous: direction={direction}, speed={speed}")
    
    def load_scenario(self, scenario_name: str, reset: bool = True):
        """
        Загрузка сценария МППСС.
        
        Доступные сценарии:
        - crossing_starboard: Пересечение курсов (судно справа)
        - head_on: Встречный курс
        - overtaking: Обгон
        
        Args:
            scenario_name: Имя сценария (без расширения .json)
            reset: Если True, сбросить текущее состояние перед загрузкой
        """
        command = {
            "scenario_name": scenario_name,
            "reset": reset
        }
        
        payload = json.dumps(command)
        self.client.publish("control/scenario/load", payload, qos=1)
        logger.info(f"Loading scenario: {scenario_name} (reset={reset})")
    
    def start_scenario(self):
        """Запуск загруженного сценария."""
        command = {"action": "start"}
        payload = json.dumps(command)
        self.client.publish("control/scenario/start", payload, qos=1)
        logger.info("Starting scenario")
    
    def pause_scenario(self):
        """Пауза выполнения сценария."""
        command = {"action": "pause"}
        payload = json.dumps(command)
        self.client.publish("control/scenario/start", payload, qos=1)
        logger.info("Pausing scenario")
    
    def stop_scenario(self):
        """Остановка сценария."""
        command = {"action": "stop"}
        payload = json.dumps(command)
        self.client.publish("control/scenario/start", payload, qos=1)
        logger.info("Stopping scenario")
    
    def reset_system(self):
        """Сброс системы в начальное состояние."""
        command = {"reset_all": True}
        payload = json.dumps(command)
        self.client.publish("control/system/reset", payload, qos=1)
        logger.info("System reset commanded")
    
    # === Основной цикл ===
    
    def start_listening(self, blocking: bool = True):
        """
        Запуск цикла обработки MQTT сообщений.
        
        Args:
            blocking: Если True, блокирующий режим (loop_forever),
                     иначе фоновый режим (loop_start)
        """
        if blocking:
            logger.info("Starting MQTT loop (blocking mode)")
            self.client.loop_forever()
        else:
            logger.info("Starting MQTT loop (background mode)")
            self.client.loop_start()
    
    def stop(self):
        """Остановка и отключение от брокера."""
        logger.info("Stopping FusionCoreStub...")
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker")


def main():
    """
    Демонстрационный скрипт использования FusionCoreStub.
    
    Запуск:
        python integrations/fusioncore_stub.py
    """
    print("=" * 60)
    print("FusionCore Stub - пример интеграции с Sensor Bridge")
    print("=" * 60)
    
    # Создание и подключение
    stub = FusionCoreStub(mqtt_host="localhost", mqtt_port=1883)
    
    if not stub.connect(timeout=10):
        print("❌ Не удалось подключиться к MQTT брокеру")
        print("   Убедитесь, что Sensor Bridge запущен:")
        print("   python main.py")
        return
    
    # Запуск в фоновом режиме
    stub.start_listening(blocking=False)
    
    # Демонстрация команд
    print("\n✅ Подключено! Демонстрация возможностей:\n")
    
    try:
        # 1. Ожидание первых данных
        print("⏳ Ожидание данных от сенсоров...")
        time.sleep(2)
        
        if stub.gps_data:
            gps = stub.gps_data
            print(f"📍 GPS: широта={gps['lat']:.6f}, долгота={gps['lon']:.6f}")
            print(f"      курс={gps['course']:.1f}°, скорость={gps['speed']:.1f} узлов")
        
        # 2. Тест управления камерой
        print("\n📷 Тест управления камерой:")
        stub.move_camera_absolute(pan=45.0, tilt=-5.0, zoom=2)
        time.sleep(1)
        
        stub.move_camera_absolute(pan=-45.0, tilt=0.0, zoom=1)
        time.sleep(1)
        
        stub.move_camera_continuous("right", speed=30)
        time.sleep(1)
        stub.move_camera_continuous("stop")
        
        # 3. Тест загрузки сценария
        print("\n🚢 Тест сценария МППСС:")
        stub.load_scenario("crossing_starboard")
        time.sleep(1)
        stub.start_scenario()
        
        # 4. Мониторинг статуса
        print("\n⏱ Мониторинг статуса сценария (10 секунд):")
        for i in range(10):
            if stub.scenario_status:
                state = stub.scenario_status.get("state", "?")
                progress = stub.scenario_status.get("progress", 0)
                print(f"   [{i+1}s] Состояние: {state}, прогресс: {progress:.1%}")
            time.sleep(1)
        
        # 5. Остановка сценария
        stub.stop_scenario()
        
    except KeyboardInterrupt:
        print("\n\n⚠ Прервано пользователем")
    
    finally:
        # Очистка
        stub.stop()
        print("\n✅ Завершено")


if __name__ == "__main__":
    main()
