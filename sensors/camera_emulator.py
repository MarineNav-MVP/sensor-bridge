#!/usr/bin/env python3
"""
📷 Camera Emulator for PTZ with Continuous Rotation
====================================================

Эмулятор морской PTZ камеры с непрерывным вращением 360°+.

Особенности:
- Непрерывное вращение по оси Pan (без механических упоров)
- Внутреннее состояние хранится как непрерывный float (pan_internal)
- Для MQTT/UI — угол нормализуется к -180°…+180°
- Плавный поворот с учётом кратчайшего пути
- Интеграция с MQTT для получения команд и отправки статуса

Архитектура:
- pan_internal: непрерывное внутреннее состояние (может быть 450°, -360°, 720°)
- pan_normalized: нормализованный угол для внешнего мира (-180…+180)
- При получении команды — выбирается кратчайший путь поворота
"""

import json
import time
import logging
import math
from typing import Optional, Dict, Any
import paho.mqtt.client as mqtt

from core.camera_utils import normalize_angle, shortest_angle_diff, AngleTracker

# Настройки
MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "camera-emulator"

# Топики
TOPICS = {
    "PTZ_COMMAND": "control/ptz/command",
    "CAMERA_STATUS": "camera/status",
}

# Параметры камеры
CAMERA_CONFIG = {
    "pan_speed": 60.0,      # градусов/секунду
    "tilt_speed": 30.0,     # градусов/секунду
    "pan_min": -3600,       # условный минимум (фактически без ограничений)
    "pan_max": 3600,        # условный максимум
    "tilt_min": -90,        # градусов (вниз)
    "tilt_max": 30,         # градусов (вверх)
}

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class CameraEmulator:
    """
    Эмулятор PTZ камеры с непрерывным вращением.
    
    Атрибуты:
        pan_internal: Непрерывный внутренний угол pan (может быть любым)
        tilt: Угол tilt (ограничен диапазоном -90…+30)
        zoom: Уровень зума (1-100)
        target_pan_internal: Целевой внутренний угол pan
        target_tilt: Целевой угол tilt
        is_moving: Флаг движения
    """
    
    def __init__(self, initial_pan: float = 0.0, initial_tilt: float = 0.0):
        """
        Инициализация камеры.
        
        Args:
            initial_pan: Начальный угол pan (будет нормализован internally)
            initial_tilt: Начальный угол tilt
        """
        # Внутреннее непрерывное состояние
        self._pan_internal: float = normalize_angle(initial_pan)
        self._tilt: float = max(CAMERA_CONFIG["tilt_min"], 
                                min(CAMERA_CONFIG["tilt_max"], initial_tilt))
        self._zoom: int = 1
        
        # Целевые значения
        self._target_pan_internal: Optional[float] = None
        self._target_tilt: Optional[float] = None
        
        # Трекер для разворачивания входящих команд
        self._pan_tracker = AngleTracker(initial_pan)
        
        # Состояние движения
        self._is_moving = False
        self._movement_start_time: Optional[float] = None
        self._start_pan_internal: float = self._pan_internal
        self._start_tilt: float = self._tilt
        
        # MQTT клиент
        self._mqtt_client: Optional[mqtt.Client] = None
        self._mqtt_connected = False
        
        logger.info(f"📷 Camera initialized: pan={self.pan_normalized:.1f}°, tilt={self.tilt:.1f}°")
    
    @property
    def pan_internal(self) -> float:
        """Внутренний непрерывный угол pan."""
        return self._pan_internal
    
    @property
    def pan_normalized(self) -> float:
        """Нормализованный угол pan для внешнего мира (-180…+180)."""
        return normalize_angle(self._pan_internal)
    
    @property
    def tilt(self) -> float:
        """Текущий угол tilt."""
        return self._tilt
    
    @property
    def zoom(self) -> int:
        """Текущий уровень зума."""
        return self._zoom
    
    @property
    def is_moving(self) -> bool:
        """Флаг движения камеры."""
        return self._is_moving
    
    @property
    def target_pan_normalized(self) -> Optional[float]:
        """Нормализованный целевой угол pan."""
        if self._target_pan_internal is not None:
            return normalize_angle(self._target_pan_internal)
        return None
    
    @property
    def target_tilt(self) -> Optional[float]:
        """Целевой угол tilt."""
        return self._target_tilt
    
    def set_pan_tilt(self, pan: float, tilt: float, zoom: Optional[int] = None, 
                     speed: float = 50.0, mode: str = "absolute"):
        """
        Устанавливает целевые углы pan и tilt.
        
        Принимает нормализованные углы (-180…+180), internally конвертирует
        в непрерывные значения с учётом кратчайшего пути.
        
        Args:
            pan: Целевой угол pan (нормализованный -180…+180)
            tilt: Целевой угол tilt (-90…+30)
            zoom: Уровень зума (1-100, опционально)
            speed: Скорость движения (0-100, влияет на время достижения цели)
            mode: Режим управления ("absolute" или "continuous")
        """
        # Нормализуем входной pan
        pan_normalized = normalize_angle(pan)
        
        # Разворачиваем pan в непрерывное значение относительно текущего положения
        # Это обеспечивает выбор кратчайшего пути
        self._pan_tracker.update(pan_normalized)
        self._target_pan_internal = self._pan_tracker.continuous_angle
        
        # Ограничиваем tilt
        self._target_tilt = max(CAMERA_CONFIG["tilt_min"], 
                                min(CAMERA_CONFIG["tilt_max"], tilt))
        
        # Устанавливаем zoom
        if zoom is not None:
            self._zoom = max(1, min(100, zoom))
        
        # Сохраняем текущее состояние для интерполяции
        self._start_pan_internal = self._pan_internal
        self._start_tilt = self._tilt
        self._movement_start_time = time.time()
        self._is_moving = True
        
        # Рассчитываем длительность движения на основе скорости
        pan_diff = abs(shortest_angle_diff(self.pan_normalized, pan_normalized))
        tilt_diff = abs(self._target_tilt - self._tilt)
        max_diff = max(pan_diff, tilt_diff)
        
        # Скорость 50 = 100% скорости, 0 = остановка
        effective_speed = (speed / 100.0) * CAMERA_CONFIG["pan_speed"]
        self._movement_duration = max_diff / effective_speed if effective_speed > 0 else 0
        
        logger.info(f"🎯 Target set: pan={pan_normalized:.1f}° (internal={self._target_pan_internal:.1f}°), "
                   f"tilt={self._target_tilt:.1f}°, duration={self._movement_duration:.2f}s")
        
        # Публикуем статус
        self._publish_status()
    
    def update(self, dt: Optional[float] = None):
        """
        Обновляет состояние камеры (плавное движение к цели).
        
        Args:
            dt: Время в секундах с последнего обновления (если None, вычисляется автоматически)
        """
        if not self._is_moving or self._target_pan_internal is None:
            return
        
        if dt is None:
            if self._movement_start_time is None:
                return
            dt = time.time() - self._movement_start_time
        
        # Вычисляем прогресс движения (0.0 … 1.0)
        if self._movement_duration > 0:
            progress = min(1.0, dt / self._movement_duration)
        else:
            progress = 1.0
        
        # Интерполируем pan с учётом кратчайшего пути
        pan_diff = shortest_angle_diff(
            normalize_angle(self._start_pan_internal),
            normalize_angle(self._target_pan_internal)
        )
        self._pan_internal = self._start_pan_internal + pan_diff * progress
        
        # Интерполируем tilt
        if self._target_tilt is not None:
            tilt_diff = self._target_tilt - self._start_tilt
            self._tilt = self._start_tilt + tilt_diff * progress
        
        # Проверяем завершение движения
        if progress >= 1.0:
            self._is_moving = False
            self._pan_internal = self._target_pan_internal
            if self._target_tilt is not None:
                self._tilt = self._target_tilt
            logger.debug(f"✅ Movement completed: pan={self.pan_normalized:.1f}°, tilt={self.tilt:.1f}°")
            self._publish_status()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Возвращает текущий статус камеры для MQTT/API.
        
        Returns:
            dict со статусом камеры (pan всегда нормализован)
        """
        return {
            "pan": round(self.pan_normalized, 2),
            "tilt": round(self.tilt, 2),
            "zoom": self.zoom,
            "is_moving": self.is_moving,
            "target_pan": round(self.target_pan_normalized, 2) if self.target_pan_normalized is not None else None,
            "target_tilt": round(self.target_tilt, 2) if self.target_tilt is not None else None,
            "pan_internal": round(self.pan_internal, 2),  # Для отладки
            "timestamp": int(time.time())
        }
    
    def _publish_status(self):
        """Публикует статус камеры в MQTT."""
        if not self._mqtt_connected or self._mqtt_client is None:
            return
        
        status = self.get_status()
        payload = json.dumps(status)
        
        try:
            self._mqtt_client.publish(TOPICS["CAMERA_STATUS"], payload)
            logger.debug(f"📤 Status published: pan={status['pan']:.1f}°")
        except Exception as e:
            logger.error(f"❌ Failed to publish status: {e}")
    
    def connect_mqtt(self, host: str = MQTT_HOST, port: int = MQTT_PORT):
        """
        Подключается к MQTT брокеру.
        
        Args:
            host: Адрес хоста MQTT
            port: Порт MQTT
        """
        self._mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self._mqtt_client.on_connect = self._on_mqtt_connect
        self._mqtt_client.on_message = self._on_mqtt_message
        
        try:
            self._mqtt_client.connect(host, port, keepalive=60)
            self._mqtt_client.loop_start()
            logger.info(f"🔌 Connecting to MQTT broker at {host}:{port}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MQTT: {e}")
    
    def disconnect_mqtt(self):
        """Отключается от MQTT брокера."""
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
            self._mqtt_connected = False
            logger.info("👋 Disconnected from MQTT")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Обработчик подключения к MQTT."""
        if rc == 0:
            self._mqtt_connected = True
            logger.info("✅ Connected to MQTT broker")
            
            # Подписываемся на топик команд
            client.subscribe(TOPICS["PTZ_COMMAND"])
            logger.info(f"📡 Subscribed to {TOPICS['PTZ_COMMAND']}")
        else:
            logger.error(f"❌ MQTT connection failed: {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Обработчик входящих MQTT сообщений."""
        if msg.topic == TOPICS["PTZ_COMMAND"]:
            try:
                command = json.loads(msg.payload.decode())
                logger.info(f"📥 PTZ command received: {command}")
                
                pan = command.get("pan", self.pan_normalized)
                tilt = command.get("tilt", self.tilt)
                zoom = command.get("zoom", self.zoom)
                speed = command.get("speed", 50)
                mode = command.get("mode", "absolute")
                
                self.set_pan_tilt(pan, tilt, zoom=zoom, speed=speed, mode=mode)
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON in command: {e}")
            except Exception as e:
                logger.error(f"❌ Error processing command: {e}", exc_info=True)
    
    def run_loop(self):
        """
        Запускает основной цикл эмулятора.
        
        Блокирующий цикл, который обновляет состояние камеры
        и обрабатывает MQTT сообщения.
        """
        logger.info("🚀 Camera emulator started")
        last_update = time.time()
        
        try:
            while True:
                current_time = time.time()
                dt = current_time - last_update
                last_update = current_time
                
                self.update(dt)
                time.sleep(0.016)  # ~60 FPS
                
        except KeyboardInterrupt:
            logger.info("👋 Stopped by user")
        finally:
            self.disconnect_mqtt()


def main():
    """Запуск эмулятора камеры."""
    camera = CameraEmulator(initial_pan=0.0, initial_tilt=0.0)
    camera.connect_mqtt()
    camera.run_loop()


if __name__ == "__main__":
    main()
