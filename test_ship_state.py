# test_ship_state.py - Тесты для моделей данных

from core.ship_state import Position, ShipState, RadarTarget, Controls
import math

def test_position_distance():
    """Проверка расчёта расстояния между позициями"""
    pos1 = Position(lat=55.751244, lon=37.618423)  # Москва
    
    # 1 минута широты = 1 морская миля = 1/60 градуса ≈ 0.016667°
    pos2 = Position(lat=55.751244 + 0.016667, lon=37.618423)  # 1 минута севернее
    
    distance = pos1.distance_to(pos2)
    print(f"Расстояние между позициями: {distance:.2f} NM")
    
    # 1 минута широты = 1 морская миля
    assert abs(distance - 1.0) < 0.01, f"Ожидалось ~1.0 NM, получилось {distance}"
    print("✅ Расчёт расстояния корректен")
    
def test_position_bearing():
    """Проверка расчёта пеленга"""
    pos1 = Position(lat=55.75, lon=37.62)
    pos2 = Position(lat=55.75, lon=37.63)  # Восточнее
    
    bearing = pos1.bearing_to(pos2)
    print(f"Пеленг на восточную точку: {bearing:.1f}°")
    
    assert 85 <= bearing <= 95, f"Ожидался восток (~90°), получилось {bearing}"
    print("✅ Расчёт пеленга корректен")

def test_ship_state_validation():
    """Проверка валидации ShipState"""
    # Валидное состояние
    ship = ShipState(
        position=Position(lat=55.75, lon=37.62),
        course=180.0,
        speed=10.5,
        timestamp=1709750000
    )
    print(f"Создано судно: {ship.ship_id}, курс={ship.course}°, скорость={ship.speed} уз")
    assert ship.ship_id == "OWN"
    print("✅ Валидация ShipState корректна")

def test_ship_state_to_dict():
    """Проверка конвертации в словарь"""
    ship = ShipState(
        position=Position(lat=55.75, lon=37.62),
        course=180.0,
        speed=10.5,
        timestamp=1709750000,
        ship_id="R01",
        ship_type="cargo"
    )
    
    data = ship.to_dict()
    print(f"\nСловарь: {data}")
    
    assert data["id"] == "R01"
    assert data["position"]["lat"] == 55.75
    assert data["ship_type"] == "cargo"
    print("✅ Конвертация в словарь корректна")

def test_radar_target():
    """Проверка RadarTarget"""
    target = RadarTarget(
        target_id="R01",
        bearing=45.0,
        distance=2.5,
        course=180.0,
        speed=12.0,
        timestamp=1709750000,
        cpa=0.3,
        tcpa=5.0
    )
    
    data = target.to_dict()
    print(f"\nЦель радара: {data}")
    
    assert data["id"] == "R01"
    assert data["bearing"] == 45.0
    assert data["cpa"] == 0.3
    print("✅ RadarTarget корректен")

def test_controls_validation():
    """Проверка валидации Controls"""
    # Валидные контролы
    controls = Controls(throttle=0.8, rudder_angle=15.0)
    assert controls.throttle == 0.8
    print("✅ Controls валидны")
    
    # Невалидные (должны вызвать ошибку)
    try:
        bad_controls = Controls(throttle=1.5, rudder_angle=0)
        print("❌ Должна была быть ошибка для throttle > 1")
    except ValueError:
        print("✅ Валидация throttle работает")

if __name__ == "__main__":
    print("🧪 Запуск тестов ShipState...\n")
    print("=" * 50)
    
    test_position_distance()
    test_position_bearing()
    test_ship_state_validation()
    test_ship_state_to_dict()
    test_radar_target()
    test_controls_validation()
    
    print("=" * 50)
    print("🎉 Все тесты пройдены!")