# core/ship_route.py - Маршруты судов между портами
import sys
import os
# Добавляем родительскую директорию в путь поиска модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dataclasses import dataclass
from typing import List, Optional
from core.ship_state import Position
import math
import time


@dataclass
class Waypoint:
    """Точка маршрута"""
    lat: float
    lon: float
    name: str = ""
    radius_m: float = 500  # Зона "достигнуто" (500 метров)


@dataclass  
class ShipRoute:
    """
    Маршрут судна от порта к порту.
    
    Судно движется от waypoint к waypoint.
    Когда достигает текущего — переходит к следующему.
    """
    waypoints: List[Waypoint]
    current_wp_index: int = 0
    completed: bool = False
    start_time: float = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = time.time()
    
    def get_current_target(self) -> Optional[Waypoint]:
        """Текущая целевая точка"""
        if self.current_wp_index >= len(self.waypoints):
            return None
        return self.waypoints[self.current_wp_index]
    
    def get_next_target(self) -> Optional[Waypoint]:
        """Следующая точка (после текущей)"""
        next_index = self.current_wp_index + 1
        if next_index >= len(self.waypoints):
            return None
        return self.waypoints[next_index]
    
    def update(self, position: Position) -> bool:
        """
        Проверяет, достигли ли текущей точки.
        
        Returns:
            True если перешли к следующей точке
        """
        target = self.get_current_target()
        if not target:
            self.completed = True
            return False
        
        # Расстояние до точки (в метрах)
        distance = position.distance_to(Position(target.lat, target.lon)) * 1852  # NM → метры
        
        if distance <= target.radius_m:
            # Достигли точки!
            old_index = self.current_wp_index
            self.current_wp_index += 1
            
            if self.current_wp_index >= len(self.waypoints):
                self.completed = True
                print(f"  🏁 Маршрут завершён!")
            else:
                next_target = self.get_current_target()
                print(f"  📍 Достиг {target.name}, следующая цель: {next_target.name}")
            
            return True
        
        return False
    
    def get_course_to_target(self, position: Position) -> float:
        """Курс к текущей цели"""
        target = self.get_current_target()
        if not target:
            return 0.0
        
        return position.bearing_to(Position(target.lat, target.lon))
    
    def get_distance_to_target(self, position: Position) -> float:
        """Расстояние до текущей цели (в морских милях)"""
        target = self.get_current_target()
        if not target:
            return 0.0
        
        return position.distance_to(Position(target.lat, target.lon))
    
    def get_eta_minutes(self, position: Position, speed_knots: float) -> Optional[float]:
        """Расчёт времени до цели (минуты)"""
        target = self.get_current_target()
        if not target or speed_knots <= 0:
            return None
        
        distance_nm = self.get_distance_to_target(position)
        eta_hours = distance_nm / speed_knots
        return eta_hours * 60
    
    @classmethod
    def from_ports(cls, start: dict, end: dict) -> 'ShipRoute':
        """Создаёт маршрут между двумя портами"""
        return cls(
            waypoints=[
                Waypoint(lat=start['lat'], lon=start['lon'], name=start.get('name', 'Start')),
                Waypoint(lat=end['lat'], lon=end['lon'], name=end.get('name', 'End'))
            ]
        )
    
    @classmethod
    def from_config(cls, lane: dict, ports: List[dict]) -> Optional['ShipRoute']:
        """Создаёт маршрут из конфигурации shipping_lane"""
        from_port = None
        to_port = None
        
        for port in ports:
            if port['id'] == lane['from']:
                from_port = port
            if port['id'] == lane['to']:
                to_port = port
        
        if not from_port or not to_port:
            return None
        
        return cls.from_ports(from_port, to_port)


# Тест
if __name__ == "__main__":
    import json
    
    print("🧪 Тест ShipRoute...\n")
    
    # Загружаем конфиг
    with open('config/ports.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Создаём маршрут
    route = ShipRoute.from_config(config['shipping_lanes'][0], config['ports'])
    
    print(f"Маршрут: {route.waypoints[0].name} → {route.waypoints[1].name}")
    print(f"Начальная позиция: {route.waypoints[0].lat}, {route.waypoints[0].lon}")
    print(f"Цель: {route.waypoints[1].lat}, {route.waypoints[1].lon}")
    
    # Тестовая позиция (начало)
    start_pos = Position(lat=route.waypoints[0].lat, lon=route.waypoints[0].lon)
    
    # Курс к цели
    course = route.get_course_to_target(start_pos)
    print(f"Курс к цели: {course:.1f}°")
    
    # Расстояние
    distance = route.get_distance_to_target(start_pos)
    print(f"Расстояние: {distance:.2f} NM ({distance * 1852:.0f} м)")
    
    # ETA
    eta = route.get_eta_minutes(start_pos, speed_knots=10.0)
    print(f"Время до цели: {eta:.0f} мин (при 10 уз)")
    
    print("\n✅ ShipRoute работает!")