#!/usr/bin/env python3
"""
📷 Camera Utilities for PTZ with Continuous Rotation
=====================================================

Утилиты для работы с углами PTZ камеры с непрерывным вращением 360°+.

Функции:
- normalize_angle(angle) — нормализация к -180…+180
- shortest_angle_diff(current, target) — расчёт кратчайшего пути поворота
- AngleTracker — класс для непрерывного отслеживания углов при трекинге
"""

import math
from typing import Optional


def normalize_angle(angle: float) -> float:
    """
    Нормализует угол к диапазону -180°…+180°.
    
    Args:
        angle: Угол в градусах (может быть любым, например 450°, -360°, 720°)
        
    Returns:
        Нормализованный угол в диапазоне [-180, 180)
        Примечание: -180° нормализуется к -180, +180° нормализуется к -180
        
    Examples:
        >>> normalize_angle(180)
        -180.0
        >>> normalize_angle(270)
        -90.0
        >>> normalize_angle(450)
        90.0
        >>> normalize_angle(-270)
        90.0
        >>> normalize_angle(-180)
        -180.0
    """
    # Используем math.fmod для корректной обработки отрицательных углов
    # Приводим к диапазону (-360, 360)
    angle = angle % 360
    
    # Конвертируем в диапазон [-180, 180)
    if angle >= 180:
        angle -= 360
    elif angle < -180:
        angle += 360
    
    return angle


def shortest_angle_diff(current: float, target: float) -> float:
    """
    Вычисляет минимальный угол поворота от current к target.
    
    Учитывает переход через 0°/360° и выбирает кратчайший путь.
    
    Args:
        current: Текущий угол (нормализованный -180…+180)
        target: Целевой угол (нормализованный -180…+180)
        
    Returns:
        Угол поворота в градусах:
        - Положительное значение = поворот по часовой стрелке
        - Отрицательное значение = поворот против часовой стрелки
        - Диапазон результата: (-180, 180]
        
    Examples:
        >>> shortest_angle_diff(170, -170)
        20  # Поворот на +20° через 180°, а не на -340°
        >>> shortest_angle_diff(-170, 170)
        -20  # Поворот на -20° через -180°, а не на +340°
        >>> shortest_angle_diff(10, 20)
        10
        >>> shortest_angle_diff(20, 10)
        -10
        >>> shortest_angle_diff(90, -90)
        -180  # Поворот на -180° (против часовой)
    """
    diff = target - current
    
    # Нормализуем разность к диапазону (-180, 180]
    diff = normalize_angle(diff)
    
    return diff


class AngleTracker:
    """
    Трекер для непрерывного отслеживания углов.
    
    Используется для разворачивания нормализованных углов (-180…+180)
    в непрерывные значения при трекинге целей.
    
    Проблема:
    При переходе цели через 0° bearing (например, 175° → -175°),
    нормализованные углы показывают скачок на 350°, но фактически
    цель переместилась всего на 10°.
    
    Решение:
    AngleTracker накапливает полные обороты и возвращает непрерывный угол.
    
    Example usage:
        >>> tracker = AngleTracker()
        >>> tracker.update(175)  # Начальный пеленг
        175.0
        >>> tracker.update(-175)  # Цель перешла через 0°
        185.0  # Не -175, а 185 (поворот на +10°)
        >>> tracker.update(-170)
        190.0  # Продолжение вращения
    """
    
    def __init__(self, initial_value: Optional[float] = None):
        """
        Инициализация трекера.
        
        Args:
            initial_value: Начальное значение угла (будет использовано как первая точка)
        """
        self._continuous_angle: Optional[float] = None
        self._last_normalized: Optional[float] = None
        self._total_rotation: float = 0.0  # Накопленный полный поворот
        
        if initial_value is not None:
            self._last_normalized = normalize_angle(initial_value)
            self._continuous_angle = self._last_normalized
    
    def update(self, normalized_angle: float) -> float:
        """
        Обновляет трекер новым нормализованным углом.
        
        Args:
            normalized_angle: Новый угол в диапазоне -180…+180
            
        Returns:
            Непрерывный угол (может быть > 180 или < -180)
        """
        normalized = normalize_angle(normalized_angle)
        
        if self._continuous_angle is None or self._last_normalized is None:
            # Первая инициализация
            self._last_normalized = normalized
            self._continuous_angle = normalized
            return self._continuous_angle
        
        # Вычисляем разницу между текущим и предыдущим нормализованным углом
        diff = shortest_angle_diff(self._last_normalized, normalized)
        
        # Добавляем разницу к непрерывному углу
        self._continuous_angle += diff
        self._last_normalized = normalized
        
        return self._continuous_angle
    
    def reset(self, initial_value: Optional[float] = None):
        """
        Сбрасывает трекер.
        
        Args:
            initial_value: Новое начальное значение (опционально)
        """
        self._continuous_angle = None
        self._last_normalized = None
        self._total_rotation = 0.0
        
        if initial_value is not None:
            self.update(initial_value)
    
    @property
    def continuous_angle(self) -> Optional[float]:
        """Возвращает текущий непрерывный угол."""
        return self._continuous_angle
    
    @property
    def normalized_angle(self) -> Optional[float]:
        """Возвращает текущий нормализованный угол."""
        if self._continuous_angle is not None:
            return normalize_angle(self._continuous_angle)
        return None


def interpolate_angle(start: float, end: float, t: float) -> float:
    """
    Интерполирует угол между start и end по параметру t.
    
    Учитывает кратчайший путь поворота.
    
    Args:
        start: Начальный угол (нормализованный)
        end: Конечный угол (нормализованный)
        t: Параметр интерполяции (0.0 = start, 1.0 = end)
        
    Returns:
        Интерполированный угол (нормализованный)
    """
    diff = shortest_angle_diff(start, end)
    return normalize_angle(start + diff * t)


# Алиасы для совместимости
unwrap_angle = normalize_angle
calculate_shortest_path = shortest_angle_diff
