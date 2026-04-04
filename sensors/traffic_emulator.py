# sensors/traffic_emulator.py - Эмулятор морского трафика

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import List, Optional
from core.ship_state import ShipState, Position, Controls
from core.ship_route import ShipRoute
from core.ship_dynamics import ShipDynamics, ShipParameters, Environment
import random
import time
import json


class TrafficShip:
    """Одно судно в трафике (со своим маршрутом)"""
    
    def __init__(self, ship_id: str, ship_type: str, route: ShipRoute, 
                 speed_knots: float = 10.0):
        self.id = ship_id
        self.ship_type = ship_type
        self.route = route
        self.speed = speed_knots
        
        # Начальная позиция (чуть дальше от старта, чтобы не "в порту")
        start = route.waypoints[0]
        self.state = ShipState(
            position=Position(lat=start.lat, lon=start.lon),
            course=route.get_course_to_target(Position(start.lat, start.lon)),
            speed=speed_knots,
            ship_id=ship_id,
            ship_type=ship_type,
            timestamp=time.time()
        )
        
        # Физика для этого судна
        params = ShipParameters.for_type(ship_type)
        self.dynamics = ShipDynamics(params)
    
    def update(self, delta_seconds: float, environment: Environment) -> bool:
        """
        Обновляет позицию судна.
        
        Returns:
            True если судно ещё в пути, False если прибыло
        """
        if self.route.completed:
            return False
        
        # Курс к цели
        target_course = self.route.get_course_to_target(self.state.position)
        
        # Простое управление: руль к цели
        course_error = (target_course - self.state.course + 180) % 360 - 180
        rudder = max(-35.0, min(35.0, course_error * 2.0))
        
        # Поддержание скорости
        speed_error = self.speed - self.state.speed
        throttle = max(0.0, min(1.0, 0.5 + speed_error * 0.1))
        
        controls = Controls(throttle=throttle, rudder_angle=rudder)
        
        # Обновляем физику
        self.state = self.dynamics.update(self.state, controls, delta_seconds, environment)
        
        # Проверяем waypoint
        self.route.update(self.state.position)
        
        return not self.route.completed


class TrafficEmulator:
    """
    Эмулятор морского трафика в акватории.
    
    Генерирует суда с маршрутами, обновляет их позиции.
    SensorBridge просто "видит" эти суда через радар.
    """
    
    def __init__(self, config_path: str = "config/ports.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.ships: List[TrafficShip] = []
        self.environment = Environment()
        
        print(f"🗺 Загрузка акватории: {self.config['name']}")
        
        # Генерируем начальный трафик
        self._spawn_initial_traffic()
    
    def _spawn_initial_traffic(self):
        """Создаёт начальные суда на маршрутах"""
        ship_counter = 0
        
        for lane in self.config.get('shipping_lanes', []):
            num_ships = random.randint(1, 2)
            
            for i in range(num_ships):
                ship_counter += 1
                
                # Находим порты
                from_port = self._get_port(lane['from'])
                to_port = self._get_port(lane['to'])
                
                if not from_port or not to_port:
                    continue
                
                # Создаём маршрут
                route = ShipRoute.from_ports(from_port, to_port)
                
                # Тип судна зависит от порта
                ship_type = from_port.get('type', 'cargo')
                
                # Случайная скорость
                speed = random.uniform(8, 15)
                
                # Создаём судно
                ship = TrafficShip(
                    ship_id=f"TR{ship_counter:02d}",
                    ship_type=ship_type,
                    route=route,
                    speed_knots=speed
                )
                
                # Смещаем время старта (чтобы не все одновременно)
                ship.state.timestamp -= random.uniform(0, 300)
                
                self.ships.append(ship)
        
        print(f"🚢 Создано {len(self.ships)} судов в трафике")
    
    def _get_port(self, port_id: str) -> Optional[dict]:
        """Находит порт по ID"""
        for port in self.config.get('ports', []):
            if port['id'] == port_id:
                return port
        return None
    
    def update(self, delta_seconds: float) -> List[ShipState]:
        """
        Обновляет все суда в трафике.
        
        Returns:
            Список состояний всех активных судов
        """
        active_ships = []
        
        for ship in self.ships:
            still_moving = ship.update(delta_seconds, self.environment)
            if still_moving:
                active_ships.append(ship.state)
            else:
                # Судно прибыло — назначаем обратный маршрут
                self._reverse_route(ship)
                active_ships.append(ship.state)  # Всё ещё активно
        
        return active_ships
    
    def _reverse_route(self, ship: TrafficShip):
        """Разворачивает судно (порт назначения → порт отправления)"""
        if len(ship.route.waypoints) < 2:
            return
        
        # Меняем waypoints местами
        old_waypoints = ship.route.waypoints
        ship.route.waypoints = [old_waypoints[-1], old_waypoints[0]]
        ship.route.current_wp_index = 0
        ship.route.completed = False
        
        # Новый курс
        ship.state.course = ship.route.get_course_to_target(ship.state.position)
        
        print(f"  🔄 {ship.id} разворачивается: {old_waypoints[-1].name} → {old_waypoints[0].name}")
    
    def get_radar_targets(self, own_ship: ShipState, range_nm: float = 12.0) -> List[dict]:
        """
        Возвращает цели для радара (относительно нашего судна).
        
        Args:
            own_ship: Наше судно
            range_nm: Дальность радара
            
        Returns:
            Список целей в формате для radar_emulator
        """
        targets = []
        
        for ship in self.ships:
            # Расстояние до цели
            distance = own_ship.position.distance_to(ship.state.position)
            
            if distance > range_nm:
                continue  # Вне диапазона радара
            
            # Пеленг (абсолютный)
            bearing = own_ship.position.bearing_to(ship.state.position)
            
            # Пеленг относительный (к курсу нашего судна)
            relative_bearing = (bearing - own_ship.course + 360) % 360
            
            # В конце метода, где создаётся targets:
            targets.append({
                "id": ship.id,
                "bearing": round(relative_bearing, 2),
                "distance": round(distance, 2),
                "course": ship.state.course,
                "speed": ship.state.speed,
                "type": ship.ship_type,
                "timestamp": int(time.time()),
                # ✅ Обязательно добавь:
                "absolute_position": {
                    "lat": ship.state.position.lat,
                    "lon": ship.state.position.lon
                }
            })
        
        return targets


# Тест
if __name__ == "__main__":
    print("🧪 Тест TrafficEmulator...\n")
    
    # Создаём эмулятор
    traffic = TrafficEmulator("config/ports.json")
    
    print(f"\n📋 Активные суда: {len(traffic.ships)}")
    for ship in traffic.ships:
        print(f"  • {ship.id}: {ship.ship_type}, {ship.speed:.1f} уз, "
              f"маршрут: {ship.route.waypoints[0].name} → {ship.route.waypoints[-1].name}")
    
    # Обновляем 5 раз (имитация 15 секунд)
    print("\n⏱ Симуляция 15 секунд...")
    for i in range(5):
        traffic.update(3.0)
        time.sleep(0.1)
    
    # Тест радара
    print("\n📡 Тест радара:")
    import time
    
    own_ship = ShipState(
        position=Position(lat=55.7512, lon=29.7683),  # Kronstadt
        course=58.0,
        speed=10.0,
        timestamp=time.time(),
        ship_id="OWN"
    )
    
    targets = traffic.get_radar_targets(own_ship, range_nm=12.0)
    print(f"  Видим целей: {len(targets)}")
    for t in targets[:3]:  # Показываем первые 3
        print(f"    - {t['id']}: пеленг={t['bearing']}°, дистанция={t['distance']}миль")
    
    print("\n✅ TrafficEmulator работает!")