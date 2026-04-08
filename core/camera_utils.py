"""
Утилиты для расчёта углов камеры PTZ.

Функции для расчёта bearing (пеленга) и углов pan/tilt
для интеграции с системой трекинга целей.
"""

import math


def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Рассчитывает пеленг (bearing) от точки 1 к точке 2.
    
    Args:
        lat1, lon1: Координаты наблюдателя (градусы)
        lat2, lon2: Координаты цели (градусы)
    
    Returns:
        bearing: Пеленг в градусах (0-360°, где 0° = север)
    """
    # Конвертируем в радианы
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    
    # Формула для расчёта bearing
    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
    
    bearing = math.degrees(math.atan2(x, y))
    
    # Нормализуем к диапазону 0-360
    return (bearing + 360) % 360


def calculate_distance_nm(lat1, lon1, lat2, lon2):
    """
    Рассчитывает расстояние между двумя точками в морских милях.
    
    Args:
        lat1, lon1: Координаты точки 1 (градусы)
        lat2, lon2: Координаты точки 2 (градусы)
    
    Returns:
        distance: Расстояние в морских милях
    """
    # Приближённая формула (достаточно для малых расстояний)
    # 1 градус широты ≈ 60 морских миль
    # 1 градус долготы ≈ 60 * cos(lat) морских миль
    
    delta_lat = (lat2 - lat1) * 60
    delta_lon = (lon2 - lon1) * 60 * math.cos(math.radians((lat1 + lat2) / 2))
    
    return math.sqrt(delta_lat**2 + delta_lon**2)


def calculate_relative_bearing(own_course, target_bearing):
    """
    Рассчитывает относительный пеленг (relative bearing) цели.
    
    Относительный пеленг — угол между курсом судна и направлением на цель.
    0° = цель прямо по носу, 90° = справа, 180° = позади, 270° = слева.
    
    Args:
        own_course: Курс собственного судна (градусы, 0-360)
        target_bearing: Абсолютный пеленг на цель (градусы, 0-360)
    
    Returns:
        relative_bearing: Относительный пеленг (-180 до +180)
    """
    rel = target_bearing - own_course
    
    # Нормализуем к диапазону -180 до +180
    while rel > 180:
        rel -= 360
    while rel < -180:
        rel += 360
    
    return rel


def bearing_to_pan(relative_bearing, camera_mount_angle=0):
    """
    Конвертирует относительный пеленг в угол pan камеры.
    
    Args:
        relative_bearing: Относительный пеленг цели (-180 до +180)
        camera_mount_angle: Угол установки камеры относительно носа судна (градусы)
    
    Returns:
        pan: Угол pan камеры (градусы)
    """
    # Pan = 0° когда камера смотрит прямо по носу
    # Положительный pan = поворот вправо
    pan = relative_bearing + camera_mount_angle
    
    # Ограничиваем диапазон камеры (обычно -180 до +180 или 0 до 360)
    # Для PTZ камер обычно доступен полный круг
    return pan % 360


def elevation_to_tilt(distance_nm, target_height_m, camera_height_m):
    """
    Рассчитывает угол tilt для цели на заданной дистанции.
    
    Args:
        distance_nm: Дистанция до цели (морские мили)
        target_height_m: Высота цели над уровнем моря (метры)
        camera_height_m: Высота камеры над уровнем моря (метры)
    
    Returns:
        tilt: Угол tilt камеры (градусы, отрицательный = вниз)
    """
    # Конвертируем морские мили в метры (1 NM = 1852 м)
    distance_m = distance_nm * 1852
    
    # Разница высот
    height_diff = target_height_m - camera_height_m
    
    # Рассчитываем угол возвышения (elevation)
    if distance_m == 0:
        return 0
    
    tilt_rad = math.atan(height_diff / distance_m)
    tilt_deg = math.degrees(tilt_rad)
    
    # Tilt: положительный = вверх, отрицательный = вниз
    return tilt_deg


def interpolate_angle(current, target, max_speed_deg_per_sec, dt_seconds):
    """
    Плавно интерполирует угол с ограничением скорости.
    
    Args:
        current: Текущий угол (градусы)
        target: Целевой угол (градусы)
        max_speed_deg_per_sec: Максимальная скорость поворота (градусы/сек)
        dt_seconds: Время с последнего обновления (секунды)
    
    Returns:
        new_angle: Новый угол после интерполяции
    """
    # Вычисляем минимальную разницу углов (учитывая переход через 360)
    diff = target - current
    while diff > 180:
        diff -= 360
    while diff < -180:
        diff += 360
    
    # Ограничиваем скорость
    max_change = max_speed_deg_per_sec * dt_seconds
    if abs(diff) <= max_change:
        return target
    else:
        return current + (max_change if diff > 0 else -max_change)
