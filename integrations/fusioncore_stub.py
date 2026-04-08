"""
Заглушка для интеграции с FusionCore.

Леонид: реализуй логику выбора цели и расчёта углов камеры.
Этот модуль подписывается на данные радара и отправляет команды камере.
"""

import paho.mqtt.client as mqtt
import json
import time
from typing import List, Dict, Any, Optional


class FusionCoreStub:
    """
    Заглушка для FusionCore.
    
    TODO: Реализуй полноценную логику:
    1. Выбор цели для трекинга (ближайшая, самая опасная, ручная)
    2. Расчёт углов pan/tilt для выбранной цели
    3. Управление зумом в зависимости от дистанции
    """
    
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883):
        """
        Инициализация заглушки FusionCore.
        
        Args:
            broker_host: MQTT брокер
            broker_port: Порт MQTT брокера
        """
        self.client = mqtt.Client()
        self.client.connect(broker_host, broker_port)
        self.client.subscribe("sensors/radar/targets")
        
        # Текущая выбранная цель
        self.selected_target_id: Optional[str] = None
        
        # Параметры камеры
        self.current_pan = 0.0
        self.current_tilt = 0.0
        self.current_zoom = 1
        
        print("🔗 FusionCore Stub подключён к MQTT")
        print("📡 Подписка на sensors/radar/targets")
    
    def on_message(self, client, userdata, msg):
        """Обработка входящих сообщений."""
        if msg.topic == "sensors/radar/targets":
            try:
                targets = json.loads(msg.payload.decode('utf-8'))
                self.process_targets(targets)
            except json.JSONDecodeError:
                print(f"⚠️ Ошибка парсинга данных радара: {msg.payload}")
    
    def process_targets(self, targets: List[Dict[str, Any]]):
        """
        Обработка списка целей с радара.
        
        TODO: Реализуй логику выбора цели!
        
        Args:
            targets: Список целей с полями:
                - id: идентификатор цели
                - bearing: пеленг (градусы)
                - distance: дистанция (мили)
                - course: курс цели (градусы)
                - speed: скорость цели (узлы)
                - absolute_position: {lat, lon}
        """
        if not targets:
            return
        
        # === ТВОЯ ЛОГИКА ЗДЕСЬ ===
        # TODO: Реализуй критерии выбора цели:
        # - Ближайшая цель
        # - Цель с наименьшим CPA
        # - Ручной выбор пользователя
        # - Приоритет по типу судна
        
        # Временная логика: выбираем первую цель
        target = self.select_target(targets)
        
        if target:
            self.track_target(target)
    
    def select_target(self, targets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Выбери цель для трекинга.
        
        TODO: Реализуй критерии выбора!
        
        Примеры критериев:
        - Минимальная дистанция
        - Минимальный TCPA
        - Максимальная скорость сближения
        - Ручной выбор из веб-интерфейса
        
        Args:
            targets: Список доступных целей
        
        Returns:
            Выбранная цель или None
        """
        # ВРЕМЕННАЯ ЗАГЛУШКА
        # Просто выбираем первую цель
        if targets:
            selected = targets[0]
            print(f"🎯 Выбрана цель: {selected.get('id', 'UNKNOWN')}")
            return selected
        
        return None
    
    def calculate_camera_angles(self, target: Dict[str, Any]) -> tuple:
        """
        Рассчитай углы камеры для сопровождения цели.
        
        TODO: Реализуй расчёт углов!
        
        Подсказка:
        - Pan = bearing цели относительно курса судна
        - Tilt зависит от дистанции и высоты цели
        - Zoom зависит от дистанции
        
        Args:
            target: Данные цели (bearing, distance, ...)
        
        Returns:
            (pan, tilt, zoom) - углы и уровень зума
        """
        # ВРЕМЕННАЯ ЗАГЛУШКА
        # Используем bearing цели как pan
        
        bearing = target.get('bearing', 0)
        distance = target.get('distance', 1.0)
        
        # Простая логика:
        # - Pan = bearing (цель в центре кадра)
        # - Tilt = 0 (горизонт)
        # - Zoom = чем ближе, тем больше
        pan = bearing
        tilt = 0
        
        # Зум: 1x на 5+ миль, 10x на 0.1 мили
        if distance > 5:
            zoom = 1
        elif distance < 0.1:
            zoom = 10
        else:
            zoom = int(1 + (5 - distance) / 0.5)
        zoom = max(1, min(10, zoom))
        
        return pan, tilt, zoom
    
    def track_target(self, target: Dict[str, Any]):
        """
        Сопровождение цели - расчёт и отправка команды камере.
        
        Args:
            target: Данные цели для сопровождения
        """
        pan, tilt, zoom = self.calculate_camera_angles(target)
        
        # Округляем для плавности
        pan = round(pan, 1)
        tilt = round(tilt, 1)
        
        # Отправляем команду только если углы изменились
        if abs(pan - self.current_pan) > 0.5 or \
           abs(tilt - self.current_tilt) > 0.5 or \
           zoom != self.current_zoom:
            
            self.send_ptz_command(pan, tilt, zoom)
            self.current_pan = pan
            self.current_tilt = tilt
            self.current_zoom = zoom
    
    def send_ptz_command(self, pan: float, tilt: float, zoom: int):
        """
        Отправить команду камере PTZ.
        
        Args:
            pan: Угол поворота (градусы)
            tilt: Угол наклона (градусы)
            zoom: Уровень зума
        """
        command = {
            "pan": pan,
            "tilt": tilt,
            "zoom": zoom,
            "speed": 50,
            "mode": "absolute"
        }
        
        self.client.publish("control/ptz/command", json.dumps(command))
        print(f"📹 Команда камере: pan={pan}°, tilt={tilt}°, zoom={zoom}x")
    
    def run(self):
        """Запустить цикл обработки."""
        print("🚀 FusionCore Stub запущен")
        print("   Ожидание данных радара...")
        
        self.client.on_message = self.on_message
        self.client.loop_forever()


if __name__ == "__main__":
    stub = FusionCoreStub()
    
    try:
        stub.run()
    except KeyboardInterrupt:
        print("\n🛑 FusionCore Stub остановлен")
