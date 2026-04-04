# test_ship_dynamics.py - Тесты физики движения

from core.ship_state import ShipState, Position, Controls
from core.ship_dynamics import ShipDynamics, ShipParameters, Environment
import time

def test_acceleration():
    """Проверка разгона судна"""
    params = ShipParameters.for_type("cargo")
    dynamics = ShipDynamics(params)
    
    # Начальное состояние: стоит на месте
    ship = ShipState(
        position=Position(lat=55.75, lon=37.62),
        course=180.0,
        speed=0.0,
        timestamp=time.time()
    )
    
    # Полный газ
    controls = Controls(throttle=1.0, rudder_angle=0)
    
    # Моделируем 60 секунд разгона
    for _ in range(20):  # 20 шагов по 3 секунды
        ship = dynamics.update(ship, controls, delta_seconds=3.0, environment=Environment.calm())
    
    print(f"🚀 Скорость после 60 сек разгона: {ship.speed:.2f} уз")
    assert ship.speed > 0, "Судно должно разогнаться"
    assert ship.speed < params.max_speed_knots, "Скорость не должна превысить максимум"
    print("✅ Разгон работает корректно")

def test_deceleration():
    """Проверка торможения"""
    params = ShipParameters.for_type("cargo")
    dynamics = ShipDynamics(params)
    
    # Начальное состояние: полная скорость
    ship = ShipState(
        position=Position(lat=55.75, lon=37.62),
        course=180.0,
        speed=params.max_speed_knots,
        timestamp=time.time()
    )
    
    # Газ в ноль
    controls = Controls(throttle=0.0, rudder_angle=0)
    
    # Тормозим 120 секунд
    for _ in range(40):  # 40 шагов по 3 секунды
        ship = dynamics.update(ship, controls, delta_seconds=3.0, environment=Environment.calm())
    
    print(f"🛑 Скорость после 120 сек торможения: {ship.speed:.2f} уз")
    assert ship.speed < params.max_speed_knots * 0.5, "Судно должно замедлиться"
    print("✅ Торможение работает корректно")

def test_turning():
    """Проверка поворота"""
    params = ShipParameters.for_type("cargo")
    dynamics = ShipDynamics(params)
    
    ship = ShipState(
        position=Position(lat=55.75, lon=37.62),
        course=180.0,
        speed=10.0,  # нужна скорость для эффективного руля
        timestamp=time.time()
    )
    
    # Руль вправо на максимум
    controls = Controls(throttle=0.5, rudder_angle=35.0)
    
    # Поворачиваем 30 секунд
    initial_course = ship.course
    for _ in range(10):  # 10 шагов по 3 секунды
        ship = dynamics.update(ship, controls, delta_seconds=3.0, environment=Environment.calm())
    
    course_change = (ship.course - initial_course) % 360
    print(f"🔄 Изменение курса за 30 сек: {course_change:.1f}°")
    
    # Курс должен измениться, но не мгновенно
    assert course_change > 0, "Курс должен измениться"
    assert course_change < 90, "Поворот не должен быть слишком резким"
    print("✅ Поворот работает корректно")

def test_current_drift():
    """Проверка сноса течением"""
    params = ShipParameters.for_type("cargo")
    dynamics = ShipDynamics(params)
    
    ship = ShipState(
        position=Position(lat=55.75, lon=37.62),
        course=180.0,
        speed=0.0,  # стоит на месте
        timestamp=time.time()
    )
    
    # Течение на восток (90°), 2 узла
    environment = Environment(current_speed=2.0, current_direction=90.0)
    controls = Controls(throttle=0, rudder_angle=0)
    
    # Ждём 60 секунд
    ship = dynamics.update(ship, controls, delta_seconds=60.0, environment=environment)
    
    print(f"🌊 Снос течением: долгота изменилась на {(ship.position.lon - 37.62)*60*60:.2f} морских миль")
    
    # Долгота должна увеличиться (снесло на восток)
    assert ship.position.lon > 37.62, "Течение должно снести судно на восток"
    print("✅ Снос течением работает корректно")

def test_stop_distance():
    """Проверка расчёта тормозного пути"""
    params = ShipParameters.for_type("cargo")
    dynamics = ShipDynamics(params)
    
    # Тормозной путь с 15 узлов
    distance = dynamics.estimate_stop_distance(15.0)
    print(f"📏 Тормозной путь с 15 уз: {distance:.2f} NM")
    
    # Должен быть разумным (не 0, не 100)
    assert 0.1 < distance < 10.0, f"Тормозной путь {distance} NM выглядит нереалистично"
    print("✅ Расчёт тормозного пути корректен")

if __name__ == "__main__":
    print("🧪 Тесты ShipDynamics...\n")
    print("=" * 60)
    
    test_acceleration()
    test_deceleration()
    test_turning()
    test_current_drift()
    test_stop_distance()
    
    print("=" * 60)
    print("🎉 Все тесты физики пройдены!")