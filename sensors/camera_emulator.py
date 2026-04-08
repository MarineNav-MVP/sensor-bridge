"""
Эмулятор камеры PTZ для Sensor Bridge.

Эмулирует поворотную камеру с поддержкой:
- Управления через MQTT (control/ptz/command)
- Публикации статуса (camera/status) 2 Гц
- Плавного движения с ограничением скорости
- Автономного режима (без внешнего управления)
"""

import json
import time
import threading
from typing import Optional, Dict, Any

from core.camera_utils import interpolate_angle


class CameraEmulator:
    """
    Эмулятор PTZ камеры.
    
    Камера закреплена на судне и может поворачиваться
    по командам из внешней системы (FusionCore).
    """
    
    def __init__(self, mqtt_client, own_ship_ref=None):
        """
        Инициализация эмулятора камеры.
        
        Args:
            mqtt_client: MQTT клиент для публикации/подписки
            own_ship_ref: Ссылка на объект собственного судна (для расчётов)
        """
        self.mqtt_client = mqtt_client
        self.own_ship = own_ship_ref
        
        # Текущее состояние камеры
        self.pan = 0.0      # Угол поворота (градусы, 0 = прямо по носу)
        self.tilt = 0.0     # Угол наклона (градусы, + = вверх, - = вниз)
        self.zoom = 1       # Уровень зума (1x, 2x, ...)
        self.moving = False # Статус движения
        
        # Параметры движения
        self.pan_speed = 50.0   # Максимальная скорость pan (градусы/сек)
        self.tilt_speed = 30.0  # Максимальная скорость tilt (градусы/сек)
        
        # Целевые значения для плавного движения
        self.target_pan = 0.0
        self.target_tilt = 0.0
        self.target_zoom = 1
        
        # Время последнего обновления
        self.last_update = time.time()
        
        # Флаг остановки
        self._stop_flag = False
        
        # Поток публикации статуса
        self._status_thread = None
    
    def start(self):
        """Запуск эмулятора камеры."""
        self._stop_flag = False
        self.last_update = time.time()
        
        # Запускаем поток публикации статуса
        self._status_thread = threading.Thread(target=self._status_loop, daemon=True)
        self._status_thread.start()
        
        print("📹 Camera emulator started")
    
    def stop(self):
        """Остановка эмулятора камеры."""
        self._stop_flag = True
        if self._status_thread:
            self._status_thread.join(timeout=2)
        print("📹 Camera emulator stopped")
    
    def _status_loop(self):
        """Цикл публикации статуса камеры (2 Гц)."""
        while not self._stop_flag:
            self.publish_status()
            time.sleep(0.5)  # 2 Гц
    
    def publish_status(self):
        """Публикация текущего статуса камеры в MQTT."""
        status = {
            "pan": round(self.pan, 1),
            "tilt": round(self.tilt, 1),
            "zoom": self.zoom,
            "moving": self.moving,
            "timestamp": int(time.time())
        }
        
        self.mqtt_client.publish("camera/status", json.dumps(status))
    
    def handle_ptz_command(self, payload: bytes):
        """
        Обработка команды управления камерой.
        
        Вызывается при получении сообщения на control/ptz/command.
        
        Args:
            payload: JSON с командой (pan, tilt, zoom, speed, mode)
        """
        try:
            command = json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError:
            print(f"⚠️ Invalid PTZ command: {payload}")
            return
        
        mode = command.get("mode", "absolute")
        speed = command.get("speed", self.pan_speed)
        
        if mode == "absolute":
            # Абсолютные координаты
            self.target_pan = command.get("pan", self.pan)
            self.target_tilt = command.get("tilt", self.tilt)
            self.target_zoom = command.get("zoom", self.zoom)
            
        elif mode == "relative":
            # Относительное смещение
            self.target_pan = self.pan + command.get("pan", 0)
            self.target_tilt = self.tilt + command.get("tilt", 0)
            self.target_zoom = self.zoom + command.get("zoom", 0)
            
        elif mode == "continuous":
            # Непрерывное движение (пока не будет другой команды)
            # Для простоты реализуем как относительное с большим смещением
            direction_pan = command.get("pan", 0)  # -1, 0, +1
            direction_tilt = command.get("tilt", 0)  # -1, 0, +1
            
            self.target_pan = self.pan + direction_pan * 90
            self.target_tilt = self.tilt + direction_tilt * 45
            
        else:
            print(f"⚠️ Unknown PTZ mode: {mode}")
            return
        
        # Обновляем скорость если указана
        if "speed" in command:
            self.pan_speed = speed
            self.tilt_speed = speed / 2  # Tilt обычно медленнее
        
        self.moving = True
        print(f"🎯 PTZ command: pan={self.target_pan}°, tilt={self.target_tilt}°, zoom={self.target_zoom}")
    
    def update(self, dt: float):
        """
        Обновление состояния камеры (плавное движение к цели).
        
        Вызывается в главном цикле симуляции.
        
        Args:
            dt: Время с последнего обновления (секунды)
        """
        if not self.moving:
            return
        
        # Интерполяция pan
        old_pan = self.pan
        self.pan = interpolate_angle(self.pan, self.target_pan, self.pan_speed, dt)
        
        # Интерполяция tilt
        old_tilt = self.tilt
        self.tilt = interpolate_angle(self.tilt, self.target_tilt, self.tilt_speed, dt)
        
        # Мгновенное изменение zoom (без плавности)
        self.zoom = self.target_zoom
        
        # Проверка достижения цели
        pan_reached = abs(self.pan - self.target_pan) < 0.5
        tilt_reached = abs(self.tilt - self.target_tilt) < 0.5
        
        if pan_reached and tilt_reached:
            self.pan = self.target_pan
            self.tilt = self.target_tilt
            self.moving = False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение текущего статуса камеры.
        
        Returns:
            Словарь с текущим состоянием камеры
        """
        return {
            "pan": self.pan,
            "tilt": self.tilt,
            "zoom": self.zoom,
            "moving": self.moving
        }
    
    def set_manual_position(self, pan: float, tilt: float, zoom: int = 1):
        """
        Установка позиции камеры вручную (для тестов).
        
        Args:
            pan: Угол pan (градусы)
            tilt: Угол tilt (градусы)
            zoom: Уровень зума
        """
        self.pan = pan % 360
        self.tilt = max(-90, min(90, tilt))  # Ограничение tilt
        self.zoom = max(1, zoom)
        self.target_pan = self.pan
        self.target_tilt = self.tilt
        self.target_zoom = self.zoom
        self.moving = False
