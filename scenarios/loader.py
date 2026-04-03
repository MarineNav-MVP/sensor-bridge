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