# scenarios/loader.py - Загрузка сценариев из JSON
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import os
import time
import math
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
    data = scenario.get('own_ship', {})
    # Поддержка обоих форматов: "start" и прямой lat/lon
    pos_data = data.get('start') or data
    return ShipState(
        position=Position(lat=pos_data.get('lat', 55.751244), lon=pos_data.get('lon', 37.618423)),
        course=data.get('course', 0),
        speed=data.get('speed', 10),
        ship_id=data.get('id', 'OWN'),
        ship_type=data.get('ship_type') or data.get('type', 'cargo'),
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
        # Поддержка обоих форматов: "start" и "initial_position"
        pos_data = t.get('start') or t.get('initial_position')
        if not pos_data:
            continue
        pos = Position(lat=pos_data['lat'], lon=pos_data['lon'])
        targets.append(MovingTarget(
            target_id=t['id'],
            position=pos,
            course=t['course'],
            speed=t['speed'],
            ship_type=t.get('ship_type') or t.get('type', 'cargo')
        ))
    return targets


def validate_scenario(scenario: Dict[str, Any]) -> bool:
    """
    Проверяет, что сценарий создаёт правильную ситуацию МППСС
    
    Returns:
        True если сценарий валиден, False иначе
    """
    own = scenario.get('own_ship', {})
    targets = scenario.get('targets', [])
    
    if not targets:
        print("❌ Ошибка: нет целей в сценарии")
        return False
    
    target = targets[0]
    scenario_name = scenario.get('name', '').lower()
    
    try:
        # Проверка для crossing
        if 'crossing' in scenario_name:
            assert abs(own.get('course', 0) - 0.0) < 1, "Наш курс должен быть 0° (север)"
            assert abs(target.get('course', 0) - 270.0) < 1, "Курс цели должен быть 270° (запад)"
            assert target.get('start', {}).get('lon', 0) > own.get('start', {}).get('lon', 0), \
                "Цель должна быть справа (восточнее)"
            print("✅ Crossing сценарий валиден")
        
        # Проверка для head_on
        elif 'head' in scenario_name:
            assert abs(own.get('course', 0) - 0.0) < 1, "Наш курс должен быть 0° (север)"
            assert abs(target.get('course', 0) - 180.0) < 1, "Курс цели должен быть 180° (юг)"
            # Суда должны быть на одной долготе (или близко)
            assert abs(target.get('start', {}).get('lon', 0) - own.get('start', {}).get('lon', 0)) < 0.01, \
                "Суда должны быть на одной линии"
            print("✅ Head-On сценарий валиден")
        
        # Проверка для overtaking
        elif 'overtaking' in scenario_name:
            assert abs(own.get('course', 0) - target.get('course', 0)) < 1, "Курсы должны совпадать"
            assert own.get('speed', 0) > target.get('speed', 0), "Мы должны быть быстрее"
            # Мы должны быть сзади (западнее, если идём на восток)
            if abs(own.get('course', 0) - 90.0) < 1:  # идём на восток
                assert own.get('start', {}).get('lon', 0) < target.get('start', {}).get('lon', 0), \
                    "Мы должны быть сзади (западнее)"
            print("✅ Overtaking сценарий валиден")
        
        else:
            print(f"ℹ️  Неизвестный тип сценария: {scenario_name}")
        
        return True
        
    except AssertionError as e:
        print(f"❌ Ошибка валидации сценария: {e}")
        return False


def calculate_cpa_tcpa(own_ship, target) -> tuple:
    """
    Рассчитывает CPA (Closest Point of Approach) и TCPA (Time to CPA)
    
    Args:
        own_ship: объект ShipState или dict с полями position, course, speed
        target: объект MovingTarget или dict с полями position, course, speed
    
    Returns:
        dcpa: дистанция до CPA (морские мили)
        tcpa: время до CPA (минуты)
    """
    # Получаем данные
    if hasattr(own_ship, 'position'):
        x1, y1 = own_ship.position.lon, own_ship.position.lat
        v1 = own_ship.speed
        c1 = math.radians(own_ship.course)
    else:
        x1, y1 = own_ship['position'].lon, own_ship['position'].lat
        v1 = own_ship['speed']
        c1 = math.radians(own_ship['course'])
    
    if hasattr(target, 'position'):
        x2, y2 = target.position.lon, target.position.lat
        v2 = target.speed
        c2 = math.radians(target.course)
    else:
        x2, y2 = target['position'].lon, target['position'].lat
        v2 = target['speed']
        c2 = math.radians(target['course'])
    
    # Конвертируем в декартовы координаты (мили)
    cos_lat = math.cos(math.radians(y1))
    x1_mi = x1 * 60 * cos_lat
    y1_mi = y1 * 60
    x2_mi = x2 * 60 * cos_lat
    y2_mi = y2 * 60
    
    # Векторы скоростей (узлы = мили/час)
    vx1 = v1 * math.sin(c1)
    vy1 = v1 * math.cos(c1)
    vx2 = v2 * math.sin(c2)
    vy2 = v2 * math.cos(c2)
    
    # Относительная скорость
    dvx = vx2 - vx1
    dvy = vy2 - vy1
    
    # Относительная позиция (мили)
    dx = x2_mi - x1_mi
    dy = y2_mi - y1_mi
    
    # Время до CPA (в часах)
    if dvx**2 + dvy**2 == 0:
        tcpa_hours = 0
    else:
        tcpa_hours = -(dx * dvx + dy * dvy) / (dvx**2 + dvy**2)
    
    # Позиция в момент CPA (мили)
    cpa_x = (x2_mi + vx2 * tcpa_hours) - (x1_mi + vx1 * tcpa_hours)
    cpa_y = (y2_mi + vy2 * tcpa_hours) - (y1_mi + vy1 * tcpa_hours)
    
    # Дистанция CPA (мили)
    dcpa_nm = math.sqrt(cpa_x**2 + cpa_y**2)
    
    # TCPA в минутах
    tcpa_min = tcpa_hours * 60
    
    return dcpa_nm, tcpa_min

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