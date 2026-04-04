# tools/simulator.py - Интерактивный десктопный эмулятор судна

import pygame
import math
import json
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.ship_state import ShipState, Position
from core.ship_dynamics import ShipDynamics, ShipParameters
from sensors.traffic_emulator import TrafficShip

# === ИНИЦИАЛИЗАЦИЯ PYGAME ===
pygame.init()

# === НАСТРОЙКИ ОКНА ===
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🚢 MarineNav Simulator v1.0")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 24)
font_large = pygame.font.Font(None, 36)

# === ЦВЕТА ===
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 100, 200)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
ORANGE = (255, 165, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
YELLOW = (255, 255, 0)

# === КАРТА (координаты) ===
# Масштаб: 1 пиксель = 0.0001 градуса (~10 метров)
SCALE = 0.0001
OFFSET_X = WIDTH // 2
OFFSET_Y = HEIGHT // 2

def world_to_screen(lat, lon):
    """Конвертирует географические координаты в экранные"""
    x = OFFSET_X + (lon - 29.70) / SCALE
    y = OFFSET_Y - (lat - 59.70) / SCALE  # Y инвертирован
    return int(x), int(y)

def screen_to_world(x, y):
    """Конвертирует экранные координаты в географические"""
    lon = 29.70 + (x - OFFSET_X) * SCALE
    lat = 59.70 + (OFFSET_Y - y) * SCALE
    return lat, lon

# === КЛАССЫ ===

class Port:
    def __init__(self, lat, lon, name=""):
        self.lat = lat
        self.lon = lon
        self.name = name or f"Port {len(ports)+1}"
        self.radius = 15
    
    def draw(self, surface):
        x, y = world_to_screen(self.lat, self.lon)
        # Порт
        pygame.draw.circle(surface, ORANGE, (x, y), self.radius)
        pygame.draw.circle(surface, BLACK, (x, y), self.radius, 2)
        # Название
        text = font.render(self.name, True, BLACK)
        surface.blit(text, (x + 20, y - 10))
    
    def contains_point(self, mx, my):
        x, y = world_to_screen(self.lat, self.lon)
        dist = math.sqrt((mx - x)**2 + (my - y)**2)
        return dist <= self.radius

class Ship:
    def __init__(self, lat, lon, name="Ship", is_own=False):
        self.is_own = is_own
        self.name = name
        
        # Физика
        params = ShipParameters.for_type("cargo")
        self.dynamics = ShipDynamics(params)
        
        # Состояние
        self.state = ShipState(
            position=Position(lat=lat, lon=lon),
            course=0.0,
            speed=0.0,
            timestamp=0,
            ship_id=name,
            ship_type="cargo"
        )
        
        # Маршрут
        self.waypoints = []
        self.current_wp = 0
        self.target_speed = 10.0
        
        # Визуализация
        self.trajectory = []
        self.max_trajectory = 200
    
    def add_waypoint(self, port):
        self.waypoints.append(port)
    
    def clear_waypoints(self):
        self.waypoints = []
        self.current_wp = 0
    
    def update(self, dt, time_scale):
        if not self.waypoints:
            return
        
        # Получаем текущую цель
        target = self.waypoints[self.current_wp]
        
        # Курс к цели
        dx = target.lon - self.state.position.lon
        dy = target.lat - self.state.position.lat
        target_course = math.degrees(math.atan2(dx, dy))
        if target_course < 0:
            target_course += 360
        
        # Расстояние до цели
        dist = self.state.position.distance_to(Position(target.lat, target.lon)) * 1852  # метры
        
        # Управление
        course_error = (target_course - self.state.course + 180) % 360 - 180
        rudder = max(-35.0, min(35.0, course_error * 2.0))
        
        if dist < 500:  # Достигли точки (500м)
            self.current_wp += 1
            if self.current_wp >= len(self.waypoints):
                self.current_wp = 0  # Циклический маршрут
            return
        
        # Газ
        throttle = 1.0 if self.state.speed < self.target_speed else 0.5
        
        controls = type('Controls', (), {'throttle': throttle, 'rudder_angle': rudder})()
        
        # Обновляем физику
        self.state = self.dynamics.update(
            self.state, 
            controls, 
            dt * time_scale, 
            type('Environment', (), {'current_speed': 0, 'current_direction': 0})()
        )
        
        # Сохраняем траекторию
        self.trajectory.append((self.state.position.lat, self.state.position.lon))
        if len(self.trajectory) > self.max_trajectory:
            self.trajectory.pop(0)
    
    def draw(self, surface):
        x, y = world_to_screen(self.state.position.lat, self.state.position.lon)
        
        # Траектория
        if len(self.trajectory) > 1:
            points = [world_to_screen(lat, lon) for lat, lon in self.trajectory]
            color = BLUE if self.is_own else DARK_GRAY
            pygame.draw.lines(surface, color, False, points, 2)
        
        # Маршрут (линии к waypoints)
        for i, wp in enumerate(self.waypoints):
            wx, wy = world_to_screen(wp.lat, wp.lon)
            color = GREEN if i == self.current_wp else GRAY
            pygame.draw.line(surface, color, (x, y), (wx, wy), 2)
            # Номер точки
            text = font.render(str(i+1), True, WHITE)
            pygame.draw.circle(surface, color, (wx, wy), 8)
            surface.blit(text, (wx-5, wy-5))
        
        # Корабль
        if self.is_own:
            pygame.draw.circle(surface, BLUE, (x, y), 12)
            pygame.draw.circle(surface, WHITE, (x, y), 12, 2)
            # Радар
            radar_radius = int(12 * 1852 * SCALE * 10000)  # 12 миль в пикселях
            pygame.draw.circle(surface, GREEN, (x, y), radar_radius, 1)
        else:
            pygame.draw.circle(surface, RED, (x, y), 10)
        
        # Название
        text = font.render(self.name, True, BLACK)
        surface.blit(text, (x + 15, y - 10))
        
        # Скорость и курс
        info = font.render(f"{self.state.speed:.1f}уз {self.state.course:.0f}°", True, DARK_GRAY)
        surface.blit(info, (x + 15, y + 5))

# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
ports = []
ships = []
own_ship = None
selected_object = None
time_scale = 1.0
paused = False
show_grid = True

# === ИНТЕРФЕЙС ===
class Button:
    def __init__(self, x, y, w, h, text, callback):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback
        self.color = BLUE
    
    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, BLACK, self.rect, 2)
        text = font.render(self.text, True, WHITE)
        surface.blit(text, (self.rect.x + 10, self.rect.y + 10))
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.callback()

# Кнопки
buttons = []

def add_own_ship():
    global own_ship
    if own_ship is None:
        own_ship = Ship(59.9933, 29.7658, "Our Ship", is_own=True)
        ships.append(own_ship)

def add_traffic_ship():
    ship = Ship(59.95, 29.8, f"Ship {len(ships)+1}")
    ships.append(ship)

def clear_all():
    global ports, ships, own_ship
    ports = []
    ships = []
    own_ship = None

def toggle_pause():
    global paused
    paused = not paused

buttons.append(Button(10, 10, 200, 40, "🚢 Наш корабль", add_own_ship))
buttons.append(Button(220, 10, 200, 40, "⛵ Добавить судно", add_traffic_ship))
buttons.append(Button(430, 10, 150, 40, "🗑 Очистить", clear_all))
buttons.append(Button(590, 10, 150, 40, "⏸ Пауза", toggle_pause))

# === ОСНОВНОЙ ЦИКЛ ===
running = True
while running:
    dt = clock.tick(60) / 1000.0  # Delta time в секундах
    
    # === СОБЫТИЯ ===
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # Кнопки
        for btn in buttons:
            btn.handle_event(event)
        
        # Клик мыши
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            # Проверка клика по порту
            clicked_port = None
            for port in ports:
                if port.contains_point(mx, my):
                    clicked_port = port
                    break
            
            # Если не порт — создаём или выбираем
            if not clicked_port:
                # Shift+клик — создать порт
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    lat, lon = screen_to_world(mx, my)
                    port = Port(lat, lon)
                    ports.append(port)
                # Ctrl+клик — добавить waypoint выбранному кораблю
                elif pygame.key.get_mods() & pygame.KMOD_CTRL:
                    if selected_object and isinstance(selected_object, Ship):
                        lat, lon = screen_to_world(mx, my)
                        # Ищем ближайший порт
                        nearest = None
                        min_dist = float('inf')
                        for p in ports:
                            d = math.sqrt((p.lat - lat)**2 + (p.lon - lon)**2)
                            if d < min_dist:
                                min_dist = d
                                nearest = p
                        if nearest:
                            selected_object.add_waypoint(nearest)
                # Обычный клик — выбрать объект
                else:
                    selected_object = None
                    # Проверка кораблей
                    for ship in ships:
                        sx, sy = world_to_screen(ship.state.position.lat, ship.state.position.lon)
                        if math.sqrt((mx-sx)**2 + (my-sy)**2) < 20:
                            selected_object = ship
                            break
    
        # Колёсико мыши — масштаб времени
        if event.type == pygame.MOUSEWHEEL:
            time_scale += event.y * 0.5
            time_scale = max(0.1, min(time_scale, 100.0))
    
    # Клавиши
    keys = pygame.key.get_pressed()
    if keys[pygame.K_SPACE]:
        paused = not paused
        pygame.time.wait(200)  # Debounce
    
    # === ОБНОВЛЕНИЕ ===
    if not paused:
        for ship in ships:
            ship.update(dt, time_scale)
    
    # === ОТРИСОВКА ===
    screen.fill(WHITE)
    
    # Сетка
    if show_grid:
        for x in range(0, WIDTH, 50):
            pygame.draw.line(screen, GRAY, (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, 50):
            pygame.draw.line(screen, GRAY, (0, y), (WIDTH, y), 1)
    
    # Порты
    for port in ports:
        port.draw(screen)
    
    # Корабли
    for ship in ships:
        ship.draw(screen)
    
    # Выбранный объект
    if selected_object:
        if isinstance(selected_object, Ship):
            x, y = world_to_screen(selected_object.state.position.lat, selected_object.state.position.lon)
            pygame.draw.circle(screen, YELLOW, (x, y), 15, 3)
    
    # Кнопки
    for btn in buttons:
        btn.draw(screen)
    
    # Панель информации
    info_y = 70
    pygame.draw.rect(screen, GRAY, (10, info_y, 400, 200))
    pygame.draw.rect(screen, BLACK, (10, info_y, 400, 200), 2)
    
    info_text = [
        f"🕐 Время: {time_scale:.1f}x (колесо мыши)",
        f"⏸ Пауза: {'ДА' if paused else 'НЕТ'} (Пробел)",
        f"📍 Портов: {len(ports)}",
        f"⛵ Кораблей: {len(ships)}",
        "",
        "📌 Управление:",
        "  Shift+клик — создать порт",
        "  Ctrl+клик — добавить waypoint",
        "  Клик по кораблю — выбрать",
    ]
    
    for i, text in enumerate(info_text):
        surf = font.render(text, True, BLACK)
        screen.blit(surf, (20, info_y + 10 + i * 25))
    
    # Информация о выбранном
    if selected_object and isinstance(selected_object, Ship):
        ship = selected_object
        info_y2 = 70
        pygame.draw.rect(screen, BLUE, (WIDTH - 310, info_y2, 300, 250))
        pygame.draw.rect(screen, BLACK, (WIDTH - 310, info_y2, 300, 250), 2)
        
        ship_info = [
            f"🚢 {ship.name}",
            f"Позиция: {ship.state.position.lat:.4f}, {ship.state.position.lon:.4f}",
            f"Курс: {ship.state.course:.1f}°",
            f"Скорость: {ship.state.speed:.1f} уз",
            f"Waypoints: {ship.current_wp+1}/{len(ship.waypoints)}",
            "",
            "Маршрут:",
        ]
        for i, wp in enumerate(ship.waypoints):
            marker = "→" if i == ship.current_wp else "•"
            ship_info.append(f"  {marker} {wp.name}")
        
        for i, text in enumerate(ship_info):
            surf = font.render(text, True, WHITE)
            screen.blit(surf, (WIDTH - 300, info_y2 + 10 + i * 25))
    
    pygame.display.flip()

pygame.quit()
sys.exit()