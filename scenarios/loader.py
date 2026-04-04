# scenarios/loader.py - Загрузка сценариев из JSON
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import os
from typing import Dict, Any, List
from core.ship_state import ShipState, Position


def load_scenario(filepath: str) -> Dict[str, Any]:
    """
    Загружает сценарий из JSON-файла.
    
    Args:
        filepath: Путь к файлу сценария
        
    Returns:
        Словарь с данными сценария
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_own_ship_from_scenario(scenario: Dict[str, Any]) -> ShipState:
    """Создаёт ShipState из данных сценария"""
    import time
    data = scenario['own_ship']
    return ShipState(
        position=Position(lat=data['lat'], lon=data['lon']),
        course=data['course'],
        speed=data['speed'],
        ship_id="OWN",
        ship_type=data.get('type', 'cargo'),
        timestamp=time.time()
    )


def create_targets_from_scenario(scenario: Dict[str, Any]) -> List[Dict]:
    """Создаёт список целей из данных сценария"""
    return scenario.get('targets', [])


def get_available_scenarios() -> List[str]:
    """Возвращает список доступных сценариев"""
    scenarios_dir = os.path.dirname(__file__)
    files = []
    for f in os.listdir(scenarios_dir):
        if f.endswith('.json'):
            files.append(f[:-5])  # убираем .json
    return files

class MovingTarget:
    """Движущаяся цель с обновляемой позицией"""
    
    def __init__(self, target_id: str, position: Position, 
                 course: float, speed: float, ship_type: str = "cargo"):
        self.id = target_id
        self.position = position
        self.course = course
        self.speed = speed
        self.ship_type = ship_type
        self.timestamp = time.time()
    
    def update(self, delta_seconds: float):
        """Обновляет позицию цели"""
        distance_nm = self.speed * (delta_seconds / 3600)
        course_rad = math.radians(self.course)
        
        delta_lat = (distance_nm * math.cos(course_rad)) / 60
        delta_lon = (distance_nm * math.sin(course_rad)) / (60 * math.cos(math.radians(self.position.lat)))
        
        self.position.lat += delta_lat
        self.position.lon += delta_lon
        self.timestamp = time.time()
    
    def to_radar_target(self, own_ship: ShipState) -> dict:
        """Конвертирует в формат для радара (пеленг/дистанция)"""
        bearing = self.position.bearing_to(own_ship.position)
        # Пеленг относительно курса нашего судна
        relative_bearing = (bearing - own_ship.course + 360) % 360
        
        distance = self.position.distance_to(own_ship.position)
        
        return {
            "id": self.id,
            "bearing": round(relative_bearing, 2),
            "distance": round(distance, 2),
            "course": self.course,
            "speed": self.speed,
            "type": self.ship_type,
            "timestamp": int(self.timestamp),
            "absolute_position": {
                "lat": self.position.lat,
                "lon": self.position.lon
            }
        }


def create_moving_targets(scenario: Dict[str, Any]) -> List[MovingTarget]:
    """Создаёт список движущихся целей из сценария"""
    targets = []
    for t in scenario.get('targets', []):
        pos = Position(lat=t['initial_position']['lat'], 
                      lon=t['initial_position']['lon'])
        targets.append(MovingTarget(
            target_id=t['id'],
            position=pos,
            course=t['course'],
            speed=t['speed'],
            ship_type=t.get('type', 'cargo')
        ))
    return targets

# Тест
if __name__ == "__main__":
    print("📋 Доступные сценарии:")
    for name in get_available_scenarios():
        print(f"  • {name}")
    
    print("\n🧪 Загрузка crossing_starboard.json...")
    scenario = load_scenario("scenarios/crossing_starboard.json")
    print(f"  Название: {scenario['name']}")
    print(f"  Правило: {scenario['rule']}")
    print(f"  Описание: {scenario['description']}")
    print(f"  Целей: {len(scenario['targets'])}")
    print(f"  Ожидаемое действие: {scenario['expected_outcome']['action']}")