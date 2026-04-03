# sensors/gps_emulator.py - GPS эмулятор с генерацией NMEA
import sys
import os

# Добавляем родительскую директорию в путь поиска модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timezone
from typing import Optional, List
from core.ship_state import ShipState, Position
from nmea.generator import NMEAGenerator


class GPSEmulator:
    """
    Эмулятор GPS-приёмника.
    
    Принимает состояние судна (ShipState) и генерирует NMEA-строки:
    - $GPRMC: Основные навигационные данные
    - $GPVTG: Скорость и курс
    - $HDT: Истинный курс (для компаса)
    
    Характеристики:
    - Частота обновления: 1-10 Hz (настраиваемая)
    - Шум: ±0.00001° (~1м для DGPS)
    - Задержка: 0-100ms
    """
    
    def __init__(self, update_rate: float = 1.0, noise_std: float = 0.00001):
        """
        Args:
            update_rate: Частота обновления в Hz (1 = 1 раз в секунду)
            noise_std: Стандартное отклонение шума координат
        """
        self.update_rate = update_rate
        self.noise_std = noise_std
        self.nmea = NMEAGenerator()
        self._last_update = 0.0
    
    def add_noise(self, value: float) -> float:
        """Добавляет гауссов шум к значению"""
        import random
        import math
        # Box-Muller transform для гауссова шума
        u1 = random.random()
        u2 = random.random()
        z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return value + z0 * self.noise_std
    
    def generate_nmea_sentences(self, ship: ShipState) -> List[str]:
        """
        Генерирует набор NMEA-строк для текущего состояния судна.
        
        Args:
            ship: Состояние судна
            
        Returns:
            Список NMEA-строк (GPRMC, GPVTG, HDT)
        """
        import time
        
        # Добавляем шум к координатам (эмуляция погрешности GPS)
        noisy_lat = self.add_noise(ship.position.lat)
        noisy_lon = self.add_noise(ship.position.lon)
        
        # Используем текущее время или из ship
        if ship.timestamp:
            timestamp = datetime.fromtimestamp(ship.timestamp, tz=timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        sentences = []
        
        # 1. GPRMC - основное сообщение
        gprmc = self.nmea.generate_gprmc(
            lat=noisy_lat,
            lon=noisy_lon,
            course=ship.course,
            speed=ship.speed,
            timestamp=timestamp
        )
        sentences.append(gprmc)
        
        # 2. GPVTG - скорость и курс
        gpvtg = self.nmea.generate_gpvtg(
            course=ship.course,
            speed=ship.speed
        )
        sentences.append(gpvtg)
        
        # 3. HDT - истинный курс (от компаса)
        hdt = self.nmea.generate_hdt(
            heading=ship.heading if ship.heading else ship.course
        )
        sentences.append(hdt)
        
        self._last_update = time.time()
        
        return sentences
    
    def generate_json(self, ship: ShipState) -> dict:
        """
        Генерирует JSON для MQTT (удобный формат для FusionCore).
        
        Args:
            ship: Состояние судна
            
        Returns:
            Словарь с данными GPS
        """
        import time
        
        return {
            "type": "GPRMC",
            "lat": round(self.add_noise(ship.position.lat), 6),
            "lon": round(self.add_noise(ship.position.lon), 6),
            "course": round(ship.course, 2),
            "speed": round(ship.speed, 1),
            "heading": round(ship.heading, 2) if ship.heading else None,
            "timestamp": int(ship.timestamp if ship.timestamp else time.time())
        }


# Тестовая функция
def test_gps_emulator():
    """Быстрый тест эмулятора"""
    from core.ship_state import ShipState, Position
    
    # Создаём тестовое судно
    ship = ShipState(
        position=Position(lat=55.751244, lon=37.618423),
        course=180.0,
        speed=10.5,
        timestamp=1709750000,
        ship_id="OWN"
    )
    
    # Создаём эмулятор
    gps = GPSEmulator(update_rate=1.0, noise_std=0.00001)
    
    # Генерируем NMEA
    nmea_sentences = gps.generate_nmea_sentences(ship)
    
    print("📡 NMEA строки от GPS эмулятора:")
    print("=" * 60)
    for sentence in nmea_sentences:
        print(sentence)
    print("=" * 60)
    
    # Генерируем JSON
    json_data = gps.generate_json(ship)
    
    print("\n📦 JSON для MQTT:")
    print(json_data)
    
    return nmea_sentences, json_data


if __name__ == "__main__":
    print("🧪 Тест GPS эмулятора...\n")
    test_gps_emulator()
    print("\n✅ Тест завершён!")