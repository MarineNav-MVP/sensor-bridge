# core/ship_dynamics.py - Физика движения судна

import math
from dataclasses import dataclass
from typing import Optional
from core.ship_state import ShipState, Position, Controls


@dataclass
class ShipParameters:
    """Физические параметры судна"""
    length_m: float          # Длина корпуса (метры)
    beam_m: float            # Ширина (метры)
    displacement_t: float    # Водоизмещение (тонны)
    max_speed_knots: float   # Максимальная скорость
    max_rudder_angle: float = 35.0  # Макс. угол руля
    drag_coefficient: float = 0.02  # Коэффициент сопротивления воды
    
    @classmethod
    def for_type(cls, ship_type: str) -> 'ShipParameters':
        """Предустановки для типов судов"""
        presets = {
            "yacht": cls(length_m=12, beam_m=4, displacement_t=10, max_speed_knots=12),
            "fishing": cls(length_m=30, beam_m=8, displacement_t=150, max_speed_knots=12),
            "cargo": cls(length_m=200, beam_m=30, displacement_t=50000, max_speed_knots=18),
            "tanker": cls(length_m=300, beam_m=50, displacement_t=150000, max_speed_knots=15),
            "passenger": cls(length_m=150, beam_m=25, displacement_t=20000, max_speed_knots=22),
        }
        return presets.get(ship_type, presets["cargo"])


@dataclass
class Environment:
    """Внешние условия"""
    current_speed: float = 0.0      # Скорость течения (узлы)
    current_direction: float = 0.0  # Направление течения (градусы)
    wind_speed: float = 0.0         # Скорость ветра (узлы)
    wind_direction: float = 0.0     # Направление ветра
    wave_height: float = 0.0        # Высота волны (метры)
    
    @classmethod
    def calm(cls) -> 'Environment':
        """Штиль — условия по умолчанию"""
        return cls()


class ShipDynamics:
    """
    Моделирует физику движения судна.
    
    Особенности:
    • Инерция: разгон/торможение занимают время
    • Поворотливость: курс меняется плавно (rate of turn)
    • Влияние среды: течение сносит судно
    • Ограничения: макс. скорость, угол руля
    """
    
    def __init__(self, ship_params: ShipParameters):
        self.params = ship_params
        
        # Производные параметры
        self.mass_kg = ship_params.displacement_t * 1000
        # Постоянная времени разгона (секунды) — чем больше судно, тем медленнее
        self.accel_time_constant = ship_params.length_m * 2.0
        # Постоянная времени поворота (секунды на градус)
        self.turn_time_constant = ship_params.length_m / 5.0
        # Макс. угловая скорость поворота (градусов в секунду)
        self.max_turn_rate = 3.0  # типично для крупных судов
        
    def calculate_acceleration(self, current_speed: float, throttle: float) -> float:
        """
        Рассчитывает ускорение судна.
        
        Формула: a = (T - D*v²) / m
        где T — тяга, D — сопротивление, v — скорость, m — масса
        """
        # Тяга пропорциональна throttle (0..1)
        max_accel = 0.05  # м/с² — типичное ускорение крупного судна
        thrust = throttle * max_accel
        
        # Сопротивление воды ~ v²
        drag = self.params.drag_coefficient * current_speed**2
        
        return thrust - drag
    
    def calculate_turn_rate(self, current_speed: float, rudder_angle: float) -> float:
        """
        Рассчитывает угловую скорость поворота (градусов/сек).
        
        Поворотливость зависит от:
        - Скорости (на малой скорости руль менее эффективен)
        - Угла руля
        - Размеров судна
        """
        # Эффективность руля растёт со скоростью
        speed_factor = min(1.0, current_speed / 5.0)  # нормализация
        
        # Базовая скорость поворота
        base_turn_rate = (rudder_angle / self.params.max_rudder_angle) * self.max_turn_rate
        
        return base_turn_rate * speed_factor
    
    def apply_current(self, position: Position, environment: Environment, 
                     delta_seconds: float) -> Position:
        """
        Рассчитывает снос судна течением.
        
        Returns:
            Новая позиция с учётом дрейфа
        """
        if environment.current_speed < 0.01:
            return position  # Нет течения
        
        # Сколько миль снесло за это время
        drift_nm = environment.current_speed * (delta_seconds / 3600)
        
        # Смещение в градусах
        current_rad = math.radians(environment.current_direction)
        delta_lat = (drift_nm * math.cos(current_rad)) / 60
        delta_lon = (drift_nm * math.sin(current_rad)) / (60 * math.cos(math.radians(position.lat)))
        
        return Position(
            lat=position.lat + delta_lat,
            lon=position.lon + delta_lon
        )
    
    def update(self, state: ShipState, controls: Controls, 
               delta_seconds: float, environment: Environment) -> ShipState:
        """
        Обновляет состояние судна на основе физики.
        
        Args:
            state: Текущее состояние
            controls: Управление (throttle, rudder)
            delta_seconds: Прошло времени с последнего обновления
            environment: Внешние условия
            
        Returns:
            Новое состояние судна
        """
        # === 1. Обновление скорости (инерция) ===
        acceleration = self.calculate_acceleration(state.speed, controls.throttle)
        new_speed = state.speed + acceleration * delta_seconds
        
        # Ограничения скорости
        new_speed = max(0.0, min(new_speed, self.params.max_speed_knots))
        
        # === 2. Обновление курса (поворот) ===
        turn_rate = self.calculate_turn_rate(state.speed, controls.rudder_angle)
        new_course = state.course + turn_rate * delta_seconds
        new_course = new_course % 360  # нормализация 0-360
        
        # === 3. Обновление позиции ===
        distance_nm = new_speed * (delta_seconds / 3600)  # узлы * часы = морские мили
        course_rad = math.radians(new_course)
        
        delta_lat = (distance_nm * math.cos(course_rad)) / 60
        delta_lon = (distance_nm * math.sin(course_rad)) / (60 * math.cos(math.radians(state.position.lat)))
        
        new_position = Position(
            lat=state.position.lat + delta_lat,
            lon=state.position.lon + delta_lon
        )
        
        # === 4. Влияние течения ===
        if environment.current_speed > 0:
            new_position = self.apply_current(new_position, environment, delta_seconds)
        
        # === 5. Возвращаем новое состояние ===
        return ShipState(
            position=new_position,
            course=new_course,
            speed=new_speed,
            timestamp=state.timestamp + delta_seconds,
            ship_id=state.ship_id,
            ship_type=state.ship_type,
            heading=new_course,  # для простоты: нос смотрит туда, куда движется
            rate_of_turn=turn_rate
        )
    
    def estimate_stop_distance(self, current_speed: float) -> float:
        """
        Оценивает тормозной путь судна (в морских милях).
        
        Полезно для планирования манёвров.
        """
        # Упрощённая формула: тормозной путь ~ v² / (2*a)
        deceleration = 0.03  # типичное замедление
        time_to_stop = current_speed / deceleration  # секунды
        avg_speed = current_speed / 2  # средняя скорость при торможении
        distance_nm = avg_speed * (time_to_stop / 3600)  # мили
        
        return distance_nm