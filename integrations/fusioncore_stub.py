#!/usr/bin/env python3
"""
🧪 FusionCore Integration Stub
================================
Шаблон для разработчика FusionCore.

Этот файл:
• Подключается к MQTT брокеру Sensor Bridge
• Получает данные радара и GPS
• Отправляет команды управления камерой

Задача:
1. Реализовать select_target() — критерии выбора цели
2. Реализовать calculate_camera_angles() — расчёт углов камеры
3. Протестировать на сценариях МППСС

Запуск:
  python integrations/fusioncore_stub.py

Зависимости:
  pip install paho-mqtt
"""

import json
import time
import logging
import math
import paho.mqtt.client as mqtt

from core.camera_utils import AngleTracker, normalize_angle, shortest_angle_diff

# Настройки (можно вынести в .env)
MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "fusioncore-stub"

# Топики
TOPICS = {
    "RADAR": "sensors/radar/targets",
    "GPS": "sensors/nmea/raw",
    "PTZ_COMMAND": "control/ptz/command",
}

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class FusionCoreStub:
    def __init__(self):
        self.client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.targets = []
        self.own_ship = None
        self.selected_target_id = None
        
        # AngleTracker для непрерывного отслеживания пеленгов цели
        # Разворачивает нормализованные углы (-180…+180) в непрерывные
        self.pan_tracker = AngleTracker()
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("✅ Connected to MQTT broker")
            client.subscribe(TOPICS["RADAR"])
            client.subscribe(TOPICS["GPS"])
            logger.info(f"📡 Subscribed: {TOPICS['RADAR']}, {TOPICS['GPS']}")
        else:
            logger.error(f"❌ Connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            
            if msg.topic == TOPICS["GPS"]:
                self.own_ship = data
                logger.debug(f"📍 GPS: {data['lat']:.4f}, {data['lon']:.4f}")
                
            elif msg.topic == TOPICS["RADAR"]:
                self.targets = data
                logger.debug(f"🎯 Targets: {len(data)}")
                
                # 🎯 ТВОЯ ЛОГИКА ЗДЕСЬ:
                target = self.select_target(data)
                if target and target['id'] != self.selected_target_id:
                    self.selected_target_id = target['id']
                    logger.info(f"🎯 Selected target: {target['id']}")
                    
                    # Рассчитать углы камеры
                    pan, tilt = self.calculate_camera_angles(target)
                    self.send_ptz_command(pan, tilt, zoom=2)
                    
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error: {e}")
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}", exc_info=True)
    
    def select_target(self, targets):
        """
        🎯 ТВОЯ ЗАДАЧА: Реализовать логику выбора цели
        
        Критерии (пример):
        • Ближайшая цель с DCPA < 0.5 миль
        • Цель в секторе 0°…180° (справа по борту)
        • Цель с относительным курсом, создающим риск столкновения
        
        Args:
            targets: List[dict] из sensors/radar/targets
            
        Returns:
            dict или None — выбранная цель
        """
        # ===== ВСТАВЬ СВОЙ КОД НИЖЕ =====
        
        # Пример: просто первая цель
        if targets:
            return targets[0]
        
        # ===== КОНЕЦ ПРИМЕРА =====
        return None
    
    def calculate_camera_angles(self, target):
        """
        📷 Рассчитывает углы камеры для цели с использованием AngleTracker.
        
        Использует pan_tracker для разворачивания нормализованных пеленгов
        в непрерывные углы, что обеспечивает плавный трекинг при переходе
        через 0° bearing (175° → -175° = поворот на +20°, а не скачок на -340°).
        
        Args:
            target: dict с полями bearing, distance, absolute_position
            
        Returns:
            tuple: (pan: float, tilt: float) — оба нормализованы к -180…+180
        """
        # ===== ИСПОЛЬЗУЕМ ANGLETRACKER ДЛЯ НЕПРЕРЫВНОГО ТРЕКИНГА =====
        
        bearing = target.get('bearing', 0)  # Пеленг 0-360 от радара
        distance = target.get('distance', 1.0)
        
        # Конвертируем абсолютный пеленг (0-360) в относительный (-180…+180)
        # 0° = прямо по носу, +90° = справа, -90° = слева, ±180° = прямо по корме
        relative_bearing = normalize_angle(bearing)
        
        # Используем AngleTracker для разворачивания углов
        # Это предотвращает скачки при переходе через 0°
        continuous_pan = self.pan_tracker.update(relative_bearing)
        
        # Для команды камере используем нормализованный угол
        # CameraEmulator internally выберет кратчайший путь
        pan = normalize_angle(continuous_pan)
        
        # Tilt: чем дальше цель, тем меньше наклон вниз
        # Высота камеры ~10м, 1 морская миля = 1852м
        distance_m = distance * 1852
        tilt_rad = math.atan(10 / distance_m) if distance_m > 0 else 0
        tilt = -math.degrees(tilt_rad)  # отрицательный = наклон вниз
        
        # Ограничения камеры
        pan = max(-180, min(180, pan))
        tilt = max(-30, min(30, tilt))
        
        logger.debug(f"📷 Target bearing={bearing:.1f}° → pan={pan:.1f}° (continuous={continuous_pan:.1f}°)")
        
        return pan, tilt
    
    def send_ptz_command(self, pan, tilt, zoom, speed=50, mode="absolute"):
        """Отправить команду управления камерой"""
        command = {
            "pan": round(pan, 1),
            "tilt": round(tilt, 1),
            "zoom": int(zoom),
            "speed": int(speed),
            "mode": mode
        }
        
        payload = json.dumps(command)
        self.client.publish(TOPICS["PTZ_COMMAND"], payload)
        logger.info(f"📤 PTZ command: pan={pan:.1f}°, tilt={tilt:.1f}°, zoom={zoom}")
    
    def run(self):
        """Запустить цикл обработки"""
        logger.info("🚀 FusionCore Stub started")
        logger.info(f"🔌 Connecting to {MQTT_HOST}:{MQTT_PORT}")
        
        try:
            self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            self.client.loop_forever()
        except KeyboardInterrupt:
            logger.info("👋 Stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
        finally:
            self.client.disconnect()


def main():
    stub = FusionCoreStub()
    stub.run()


if __name__ == "__main__":
    main()