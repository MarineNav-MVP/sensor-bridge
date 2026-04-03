# core/ship_state.py - Модель состояния судна

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import math


@dataclass
class Position:
    """Географическая позиция"""
    lat: float  # Широта (-90 до +90)
    lon: float  # Долгота (-180 до +180)
    
    def distance_to(self, other: 'Position') -> float:
        """
        Рассчитывает расстояние до другой позиции в морских милях.
        Использует упрощённую формулу (достаточно для малых дистанций).
        """
        # 1 градус широты ≈ 60 морских миль
        delta_lat = (other.lat - self.lat) * 60
        
        # 1 градус долготы ≈ 60 * cos(широта) морских миль
        avg_lat = math.radians((self.lat + other.lat) / 2)
        delta_lon = (other.lon - self.lon) * 60 * math.cos(avg_lat)
        
        return math.sqrt(delta_lat**2 + delta_lon**2)
    
    def bearing_to(self, other: 'Position') -> float:
        """
        Рассчитывает пеленг (азимут) до другой позиции в градусах (0-360).
        0° = North, 90° = East, 180° = South, 270° = West
        """
        delta_lon = math.radians(other.lon - self.lon)
        lat1 = math.radians(self.lat)
        lat2 = math.radians(other.lat)
        
        x = math.sin(delta_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
        
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360


@dataclass
class ShipState:
    """
    Состояние судна в конкретный момент времени.
    
    Используется для:
    - Нашего судна (own ship)
    - Целевых судов (targets)
    """
    position: Position
    course: float           # Курс в градусах (0-360)
    speed: float            # Скорость в узлах
    timestamp: float        # UNIX timestamp
    ship_id: str = "OWN"    # Уникальный ID (OWN для нашего, R01, R02 для целей)
    ship_type: str = "power"  # Тип судна: power, sailing, fishing, etc.
    heading: Optional[float] = None  # Направление носа (может отличаться от курса из-за сноса)
    rate_of_turn: float = 0.0  # Угловая скорость поворота (градусов/минуту)
    
    def __post_init__(self):
        """Валидация после инициализации"""
        if not -90 <= self.position.lat <= 90:
            raise ValueError(f"Широта должна быть от -90 до 90, получено {self.position.lat}")
        if not -180 <= self.position.lon <= 180:
            raise ValueError(f"Долгота должна быть от -180 до 180, получено {self.position.lon}")
        if not 0 <= self.course < 360:
            raise ValueError(f"Курс должен быть от 0 до 360, получено {self.course}")
        if self.speed < 0:
            raise ValueError(f"Скорость не может быть отрицательной, получено {self.speed}")
        
        # Если heading не задан, используем курс
        if self.heading is None:
            self.heading = self.course
    
    def to_dict(self) -> dict:
        """Конвертация в словарь (для JSON/MQTT)"""
        return {
            "id": self.ship_id,
            "position": {
                "lat": self.position.lat,
                "lon": self.position.lon
            },
            "course": self.course,
            "speed": self.speed,
            "heading": self.heading,
            "ship_type": self.ship_type,
            "timestamp": int(self.timestamp)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ShipState':
        """Создание объекта из словаря"""
        return cls(
            position=Position(lat=data["position"]["lat"], lon=data["position"]["lon"]),
            course=data["course"],
            speed=data["speed"],
            timestamp=data["timestamp"],
            ship_id=data.get("id", "UNKNOWN"),
            ship_type=data.get("ship_type", "power"),
            heading=data.get("heading"),
            rate_of_turn=data.get("rate_of_turn", 0.0)
        )


@dataclass
class RadarTarget:
    """
    Цель радара (ARPA track).
    
    Содержит относительные данные (пеленг и дистанция от нашего судна).
    """
    target_id: str
    bearing: float        # Пеленг в градусах (0-360, относительно носа)
    distance: float       # Дистанция в морских милях
    course: float         # Курс цели (абсолютный)
    speed: float          # Скорость цели в узлах
    timestamp: float      # UNIX timestamp
    cpa: Optional[float] = None  # CPA (морские мили)
    tcpa: Optional[float] = None  # TCPA (минуты)
    
    def __post_init__(self):
        """Валидация"""
        if not 0 <= self.bearing < 360:
            raise ValueError(f"Пеленг должен быть от 0 до 360, получено {self.bearing}")
        if self.distance < 0:
            raise ValueError(f"Дистанция не может быть отрицательной, получено {self.distance}")
    
    def to_dict(self) -> dict:
        """Конвертация в словарь (для JSON/MQTT)"""
        return {
            "id": self.target_id,
            "bearing": round(self.bearing, 2),
            "distance": round(self.distance, 2),
            "course": round(self.course, 2),
            "speed": round(self.speed, 1),
            "timestamp": int(self.timestamp),
            "cpa": round(self.cpa, 2) if self.cpa is not None else None,
            "tcpa": round(self.tcpa, 1) if self.tcpa is not None else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RadarTarget':
        """Создание объекта из словаря"""
        return cls(
            target_id=data["id"],
            bearing=data["bearing"],
            distance=data["distance"],
            course=data["course"],
            speed=data["speed"],
            timestamp=data["timestamp"],
            cpa=data.get("cpa"),
            tcpa=data.get("tcpa")
        )


@dataclass
class Controls:
    """
    Органы управления судном.
    
    Используется для симуляции движения (автопилот или ручное управление).
    """
    throttle: float = 0.0   # Тяга двигателя (0.0 - 1.0)
    rudder_angle: float = 0.0  # Угол руля (-35 до +35 градусов)
    target_course: Optional[float] = None  # Целевой курс для автопилота
    target_speed: Optional[float] = None   # Целевая скорость для автопилота
    
    def __post_init__(self):
        """Валидация"""
        if not 0 <= self.throttle <= 1.0:
            raise ValueError(f"Throttle должен быть от 0 до 1, получено {self.throttle}")
        if not -35 <= self.rudder_angle <= 35:
            raise ValueError(f"Угол руля должен быть от -35 до 35, получено {self.rudder_angle}")