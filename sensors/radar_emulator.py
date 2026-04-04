# sensors/radar_emulator.py - Эмулятор радара с ARPA-трекингом

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import math
import time
import random
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from core.ship_state import ShipState, Position, RadarTarget


class RadarEmulator:
    """
    Эмулятор морского радара с функцией ARPA (Automatic Radar Plotting Aid).
    
    Характеристики:
    - Дальность: 0.05 - 12 морских миль (настраиваемая)
    - Точность: ±1% дистанция, ±2° пеленг
    - Частота обновления: 1 оборот за 2-4 секунды
    - Максимум целей: 50 (ARPA tracks)
    - Слепые зоны: настраиваемые сектора
    """
    
    def __init__(self, 
                 range_nm: float = 12.0,
                 min_range_nm: float = 0.05,
                 max_targets: int = 50,
                 update_interval: float = 3.0,
                 noise_bearing: float = 2.0,
                 noise_distance: float = 0.01):
        """
        Args:
            range_nm: Максимальная дальность обнаружения (мили)
            min_range_nm: Минимальная дальность (мертвая зона)
            max_targets: Максимальное количество сопровождаемых целей
            update_interval: Интервал обновления (секунды)
            noise_bearing: Шум пеленга (градусы)
            noise_distance: Шум дистанции (мили)
        """
        self.range = range_nm
        self.min_range = min_range_nm
        self.max_targets = max_targets
        self.update_interval = update_interval
        self.noise_bearing = noise_bearing
        self.noise_distance = noise_distance
        
        # Хранилище целей (ID -> RadarTarget)
        self._targets: Dict[str, RadarTarget] = {}
        self._target_counter = 0
        self._last_update = 0.0
        
        # Слепые зоны (секторы где радар не видит)
        self.blind_sectors: List[tuple] = []  # [(start_bearing, end_bearing), ...]
    
    def add_noise(self, value: float, noise_std: float) -> float:
        """Добавляет гауссов шум к значению"""
        return value + random.gauss(0, noise_std)
    
    def is_in_blind_sector(self, bearing: float) -> bool:
        """Проверяет, находится ли пеленг в слепой зоне"""
        bearing = bearing % 360
        for start, end in self.blind_sectors:
            if start <= bearing <= end:
                return True
        return False
    
    def calculate_cpa_tcpa(self, own_ship: ShipState, target: ShipState) -> tuple:
        """
        Рассчитывает CPA (Closest Point of Approach) и TCPA (Time to CPA).
        
        Returns:
            (cpa_nm, tcpa_minutes) - дистанция и время до сближения
        """
        # Относительная скорость
        v_rel_x = target.speed * math.sin(math.radians(target.course)) - \
                  own_ship.speed * math.sin(math.radians(own_ship.course))
        v_rel_y = target.speed * math.cos(math.radians(target.course)) - \
                  own_ship.speed * math.cos(math.radians(own_ship.course))
        
        v_rel = math.sqrt(v_rel_x**2 + v_rel_y**2)
        
        # Относительная позиция (в градусах)
        dx = target.position.lon - own_ship.position.lon
        dy = target.position.lat - own_ship.position.lat
        
        # Расстояние в морских милях
        range_nm = own_ship.position.distance_to(target.position)
        
        if range_nm < 0.01 or v_rel < 0.01:
            return range_nm, float('inf')
        
        # Пеленг на цель
        bearing_to_target = own_ship.position.bearing_to(target.position)
        
        # Угол между относительной скоростью и линией визирования
        relative_course = math.degrees(math.atan2(v_rel_x, v_rel_y))
        angle = bearing_to_target - relative_course
        angle_rad = math.radians(angle)
        
        # CPA
        cpa = range_nm * math.sin(angle_rad)
        
        # TCPA (в минутах)
        tcpa = (range_nm * math.cos(angle_rad)) / v_rel * 60
        
        return abs(cpa), tcpa
    
    def generate_targets(self, 
                        own_ship: ShipState, 
                        num_targets: int = None) -> List[RadarTarget]:
        """
        Генерирует цели радара вокруг судна.
        
        Args:
            own_ship: Состояние нашего судна
            num_targets: Количество целей (None = случайное 1-5)
            
        Returns:
            Список целей радара
        """
        if num_targets is None:
            num_targets = random.randint(1, 5)
        
        targets = []
        
        for _ in range(num_targets):
            if len(self._targets) >= self.max_targets:
                break
            
            # Генерируем случайную цель
            self._target_counter += 1
            target_id = f"R{self._target_counter:02d}"
            
            # Случайные параметры
            bearing = random.uniform(0, 360)
            
            # Пропускаем слепые зоны
            if self.is_in_blind_sector(bearing):
                continue
            
            distance = random.uniform(self.min_range, self.range)
            course = random.uniform(0, 360)
            speed = random.uniform(5, 20)
            
            # Создаём объект цели (абсолютные координаты будут рассчитаны)
            target = RadarTarget(
                target_id=target_id,
                bearing=round(self.add_noise(bearing, self.noise_bearing) % 360, 2),
                distance=round(self.add_noise(distance, self.noise_distance), 2),
                course=round(self.add_noise(course, self.noise_bearing), 2),
                speed=round(self.add_noise(speed, 0.5), 1),
                timestamp=time.time()
            )
            
            targets.append(target)
            self._targets[target_id] = target
        
        return targets
    
    def generate_nmea_ttm(self, target: RadarTarget) -> str:
        """
        Генерирует NMEA-строку $TTM (Tracked Target Message).
        
        Формат: $TTM,xx,distance,bearing,relative_bearing,course,speed,status,id*checksum
        
        Args:
            target: Цель радара
            
        Returns:
            NMEA-строка $TTM
        """
        from nmea.generator import NMEAGenerator
        
        # Формат: $TTM,target_num,distance,bearing,relative,course,speed,status,name*checksum
        body = f"TTM,{target.target_id[1:]},{target.distance:.1f},{target.bearing:.1f},R,{target.course:.1f},{target.speed:.1f},A,{target.target_id}"
        
        checksum = NMEAGenerator.calculate_checksum(body)
        return f"${body}*{checksum}"
    
    def generate_json(self, targets: List[RadarTarget]) -> List[dict]:
        """
        Генерирует JSON для MQTT (список целей).
        
        Args:
            targets: Список целей
            
        Returns:
            Список словарей
        """
        return [t.to_dict() for t in targets]
    
    def update(self, own_ship: ShipState, 
           num_targets: int = None, 
           scenario_targets: List[dict] = None,
           moving_targets: List[Any] = None) -> List[RadarTarget]:
        """
        Обновляет цели радара и рассчитывает CPA/TCPA.
        
        Args:
            own_ship: Состояние нашего судна
            num_targets: Количество целей для генерации (если нет сценария)
            scenario_targets: Цели из сценария (если есть)
        """
            # Если есть движущиеся цели — обновляем их позиции
        if moving_targets:
            for mt in moving_targets:
                mt.update(self.update_interval)

        targets = []
        
        # Если есть сценарий — используем его цели
        if scenario_targets:
            for t in scenario_targets:
                targets.append(RadarTarget(
                    target_id=t['id'],
                    bearing=t['bearing'],
                    distance=t['distance'],
                    course=t['course'],
                    speed=t['speed'],
                    timestamp=time.time(),
                    cpa=t.get('cpa'),
                    tcpa=t.get('tcpa')
                ))
        else:
            # Генерируем рандомные цели
            targets = self.generate_targets(own_ship, num_targets)
        
        # Рассчитываем CPA/TCPA для каждой цели
        for target in targets:
            # Эмуляция абсолютной позиции цели (для расчёта CPA)
            target_lat = own_ship.position.lat + (target.distance * math.cos(math.radians(target.bearing))) / 60
            target_lon = own_ship.position.lon + (target.distance * math.sin(math.radians(target.bearing))) / (60 * math.cos(math.radians(own_ship.position.lat)))

            target_ship = ShipState(
                position=Position(lat=target_lat, lon=target_lon),
                course=target.course % 360,  # ✅ Нормализация 0-360
                speed=target.speed,
                timestamp=target.timestamp
)
            
            cpa, tcpa = self.calculate_cpa_tcpa(own_ship, target_ship)
            target.cpa = round(cpa, 2)
            target.tcpa = round(tcpa, 1)
        
        self._last_update = time.time()
        return targets


# Тестовая функция
def test_radar_emulator():
    """Быстрый тест эмулятора радара"""
    from core.ship_state import ShipState, Position
    
    # Создаём наше судно
    own_ship = ShipState(
        position=Position(lat=55.751244, lon=37.618423),
        course=180.0,
        speed=10.5,
        timestamp=time.time(),
        ship_id="OWN"
    )
    
    # Создаём эмулятор радара
    radar = RadarEmulator(
        range_nm=12.0,
        update_interval=3.0,
        noise_bearing=2.0,
        noise_distance=0.01
    )
    
    # Обновляем цели
    targets = radar.update(own_ship, num_targets=3)
    
    print("📡 Цели радара:")
    print("=" * 70)
    
    for target in targets:
        print(f"ID: {target.target_id}")
        print(f"  Пеленг: {target.bearing}°")
        print(f"  Дистанция: {target.distance} NM")
        print(f"  Курс: {target.course}°")
        print(f"  Скорость: {target.speed} уз")
        print(f"  CPA: {target.cpa} NM")
        print(f"  TCPA: {target.tcpa} мин")
        print()
    
    print("=" * 70)
    
    # Генерируем NMEA $TTM
    print("\n📄 NMEA $TTM строки:")
    for target in targets:
        ttm = radar.generate_nmea_ttm(target)
        print(ttm)
    
    # Генерируем JSON
    print("\n📦 JSON для MQTT:")
    json_data = radar.generate_json(targets)
    import json
    print(json.dumps(json_data, indent=2))
    
    return targets


if __name__ == "__main__":
    print("🧪 Тест Radar Emulator...\n")
    test_radar_emulator()
    print("\n✅ Тест завершён!")