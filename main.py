# main.py - Sensor Bridge for MarineNav maritime emulator
# Module emulates ship sensors and publishes data to MQTT

import logging
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Import our modules
from core.config import settings, get_mqtt_topics
from core.ship_state import ShipState, Position, RadarTarget
from core.ship_dynamics import ShipDynamics, ShipParameters, Environment
from sensors.gps_emulator import GPSEmulator
from sensors.radar_emulator import RadarEmulator
from scenarios.loader import load_scenario, create_moving_targets, MovingTarget

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get MQTT topics
TOPICS = get_mqtt_topics()

# Global state
connected: bool = False
client: Optional[mqtt.Client] = None
simulation_running: bool = False
time_scale: float = settings.default_timescale
own_ship: Optional[ShipState] = None
moving_targets: List[MovingTarget] = []
camera_state: Dict[str, Any] = {
    "pan": 0.0,
    "tilt": 0.0,
    "zoom": 1,
    "moving": False,
    "target_pan": 0.0,
    "target_tilt": 0.0
}
last_radar_update: float = 0
last_world_update: float = 0
WORLD_STATE_HZ: float = settings.world_state_hz


def on_connect(client: mqtt.Client, userdata: Any, flags: Dict, rc: int) -> None:
    """Callback when connected to MQTT broker.
    
    Args:
        client: MQTT client instance
        userdata: User data (unused)
        flags: Connection flags
        rc: Return code (0 = success)
    """
    global connected
    if rc == 0:
        logger.info("Connected to MQTT broker %s:%d", settings.mqtt_host, settings.mqtt_port)
        connected = True
        # Subscribe to command topics
        client.subscribe(TOPICS["PTZ_COMMAND"])
        client.subscribe(TOPICS["SIMULATION_COMMAND"])
        logger.info("Subscribed to %s and %s", TOPICS["PTZ_COMMAND"], TOPICS["SIMULATION_COMMAND"])
    else:
        logger.error("Connection failed. Return code: %d", rc)
        connected = False


def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    """Callback when message received on subscribed topic.
    
    Args:
        client: MQTT client instance
        userdata: User data (unused)
        msg: MQTT message object
    """
    global simulation_running, time_scale, camera_state
    
    try:
        payload = msg.payload.decode('utf-8')
        data = __import__('json').loads(payload)
        
        if msg.topic == TOPICS["SIMULATION_COMMAND"]:
            handle_simulation_command(data)
        elif msg.topic == TOPICS["PTZ_COMMAND"]:
            handle_ptz_command(data)
    except Exception as e:
        logger.error("Error processing message: %s", e)


def handle_simulation_command(cmd: Dict[str, Any]) -> None:
    """Handle simulation control commands.
    
    Args:
        cmd: Command dictionary with action and parameters
    """
    global simulation_running, time_scale, own_ship, moving_targets
    
    action = cmd.get("action", "")
    
    if action == "start":
        scenario_name = cmd.get("scenario", "crossing_starboard")
        time_scale = cmd.get("timescale", settings.default_timescale)
        start_simulation(scenario_name)
    elif action == "stop":
        simulation_running = False
        logger.info("Simulation stopped")
    elif action == "timescale":
        time_scale = float(cmd.get("value", settings.default_timescale))
        logger.info("Time scale: %dx", time_scale)
    elif action == "restart":
        scenario_name = cmd.get("scenario", "crossing_starboard")
        time_scale = cmd.get("timescale", settings.default_timescale)
        start_simulation(scenario_name)


def handle_ptz_command(cmd: Dict[str, Any]) -> None:
    """Handle PTZ camera control commands.
    
    Args:
        cmd: Command dictionary with pan, tilt, zoom parameters
    """
    global camera_state
    
    mode = cmd.get("mode", "absolute")
    
    if mode == "stop":
        camera_state["moving"] = False
    else:
        camera_state["target_pan"] = float(cmd.get("pan", camera_state["pan"]))
        camera_state["target_tilt"] = float(cmd.get("tilt", camera_state["tilt"]))
        camera_state["zoom"] = int(cmd.get("zoom", camera_state["zoom"]))
        camera_state["moving"] = True
        logger.info("Camera: pan=%.1f°, tilt=%.1f°, zoom=%dx", 
                   camera_state['target_pan'], camera_state['target_tilt'], camera_state['zoom'])


def start_simulation(scenario_name: str) -> None:
    """Start a simulation scenario.
    
    Args:
        scenario_name: Name of the scenario file (without .json extension)
    """
    global simulation_running, own_ship, moving_targets
    
    try:
        scenario_path = f"scenarios/{scenario_name}.json"
        scenario = load_scenario(scenario_path)
        
        # Create own ship from scenario data
        own_data = scenario.get("own_ship", {})
        start_pos = own_data.get("start", {})
        own_ship = ShipState(
            position=Position(
                lat=float(start_pos.get("lat", 55.751244)),
                lon=float(start_pos.get("lon", 37.618423))
            ),
            course=float(own_data.get("course", 0)),
            speed=float(own_data.get("speed", 10)),
            ship_id=own_data.get("id", "OWN"),
            ship_type=own_data.get("ship_type", "cargo"),
            timestamp=time.time()
        )
        
        # Create moving targets
        moving_targets = create_moving_targets(scenario)
        
        simulation_running = True
        logger.info("Started scenario: %s (%d targets)", scenario_name, len(moving_targets))
        
    except Exception as e:
        logger.error("Error starting scenario: %s", e)
        simulation_running = False


def update_ship_positions(dt: float) -> None:
    """Update positions of all ships.
    
    Args:
        dt: Delta time in seconds
    """
    global own_ship, moving_targets
    
    if own_ship:
        # Move own ship in straight line
        distance_nm = own_ship.speed * (dt / 3600)  # nautical miles
        course_rad = math.radians(own_ship.course)
        
        delta_lat = (distance_nm * math.cos(course_rad)) / 60
        delta_lon = (distance_nm * math.sin(course_rad)) / (60 * math.cos(math.radians(own_ship.position.lat)))
        
        own_ship.position.lat += delta_lat
        own_ship.position.lon += delta_lon
        own_ship.timestamp = time.time()
    
    # Update targets
    for target in moving_targets:
        target.update(dt)


def get_radar_targets() -> List[Dict[str, Any]]:
    """Get radar targets within range.
    
    Returns:
        List of radar target dictionaries
    """
    global own_ship, moving_targets
    
    targets = []
    
    for mt in moving_targets:
        distance = own_ship.position.distance_to(mt.position)
        
        # Filter: only targets within RADAR_RANGE_NM
        if distance <= settings.radar_range_nm:
            bearing = own_ship.position.bearing_to(mt.position)
            relative_bearing = (bearing - own_ship.course + 360) % 360
            
            targets.append({
                "id": mt.id,
                "bearing": round(relative_bearing, 2),
                "distance": round(distance, 2),
                "course": mt.course,
                "speed": mt.speed,
                "timestamp": int(time.time()),
                "absolute_position": {
                    "lat": mt.position.lat,
                    "lon": mt.position.lon
                }
            })
    
    return targets


def publish_nmea_raw():
    """Публикация данных GPS (NMEA raw)"""
    global own_ship, client
    
    if not own_ship or not client:
        return
    
    data = {
        "type": "GPRMC",
        "lat": round(own_ship.position.lat, 6),
        "lon": round(own_ship.position.lon, 6),
        "course": round(own_ship.course, 1),
        "speed": round(own_ship.speed, 1),
        "timestamp": int(own_ship.timestamp)
    }
    
    client.publish(TOPIC_NMEA_RAW, json.dumps(data))


def publish_radar_targets(targets):
    """Публикация целей радара"""
    global client
    
    if not client:
        return
    
    client.publish(TOPIC_RADAR_TARGETS, json.dumps(targets))


def publish_world_state(radar_targets):
    """Публикация полного состояния мира (для веб-панели)"""
    global own_ship, moving_targets, client
    
    if not client or not own_ship:
        return
    
    all_targets = []
    for mt in moving_targets:
        all_targets.append({
            "id": mt.id,
            "course": mt.course,
            "speed": mt.speed,
            "absolute_position": {  # ← Добавили вложенный объект!
                "lat": round(mt.position.lat, 6),
                "lon": round(mt.position.lon, 6)
            }
        })
    
    data = {
        "own_ship": {
            "lat": round(own_ship.position.lat, 6),
            "lon": round(own_ship.position.lon, 6),
            "course": round(own_ship.course, 1),
            "speed": round(own_ship.speed, 1)
        },
        "all_targets": all_targets,
        "timestamp": int(time.time())
    }
    
    client.publish(TOPIC_WORLD_STATE, json.dumps(data))


def publish_camera_status():
    """Публикация статуса камеры"""
    global camera_state, client
    
    if not client:
        return
    
    data = {
        "pan": round(camera_state["pan"], 1),
        "tilt": round(camera_state["tilt"], 1),
        "zoom": camera_state["zoom"],
        "moving": camera_state["moving"],
        "timestamp": int(time.time())
    }
    
    client.publish(TOPIC_CAMERA_STATUS, json.dumps(data))


def update_camera(dt):
    """Обновление состояния камеры (плавный поворот)"""
    global camera_state
    
    if camera_state["moving"]:
        speed = 50  # градусов в секунду
        
        # Поворот pan
        pan_diff = camera_state["target_pan"] - camera_state["pan"]
        if abs(pan_diff) > 0.1:
            step = speed * dt
            if abs(pan_diff) < step:
                camera_state["pan"] = camera_state["target_pan"]
            else:
                camera_state["pan"] += step * (1 if pan_diff > 0 else -1)
        else:
            camera_state["pan"] = camera_state["target_pan"]
        
        # Поворот tilt
        tilt_diff = camera_state["target_tilt"] - camera_state["tilt"]
        if abs(tilt_diff) > 0.1:
            step = speed * dt
            if abs(tilt_diff) < step:
                camera_state["tilt"] = camera_state["target_tilt"]
            else:
                camera_state["tilt"] += step * (1 if tilt_diff > 0 else -1)
        else:
            camera_state["tilt"] = camera_state["target_tilt"]
        
        # Проверка остановки
        if abs(pan_diff) < 0.1 and abs(tilt_diff) < 0.1:
            camera_state["moving"] = False


def main():
    """Главный цикл симуляции"""
    global connected, client, simulation_running, own_ship, time_scale, last_radar_update, last_world_update, WORLD_STATE_HZ
    
    print("=" * 60)
    print("🚢 MarineNav Sensor Bridge")
    print("=" * 60)
    print(f"📡 MQTT: {MQTT_HOST}:{MQTT_PORT}")
    print(f"🎯 Time Scale: {time_scale}x")
    print(f"📡 Радар: {RADAR_RANGE_NM} миль")
    print("=" * 60)
    
    # Инициализация MQTT
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"\n🔄 Подключение к {MQTT_HOST}:{MQTT_PORT}...")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    time.sleep(1)
    
    if not connected:
        print("❌ Нет подключения к брокеру!")
        return
    
    print("\n🎉 Sensor Bridge готов! Ожидание команд...")
    print("Команды:")
    print('  {"action": "start", "scenario": "crossing_starboard", "timescale": 1.0}')
    print('  {"action": "stop"}')
    print('  {"action": "timescale", "value": 10.0}')
    print("=" * 60)
    
    last_update = time.time()
    
    try:
        while True:
            current_time = time.time()
            dt = current_time - last_update
            last_update = current_time
            
            if simulation_running:
                # Обновление позиций с учётом time scale
                update_ship_positions(dt * time_scale)
                
                # Публикация GPS (1 Гц)
                publish_nmea_raw()
                
                # Публикация радара (0.3 Гц)
                if current_time - last_radar_update >= (1.0 / 0.3):
                    radar_targets = get_radar_targets()
                    publish_radar_targets(radar_targets)
                    publish_world_state(radar_targets)
                    last_radar_update = current_time

                    # World State (5 Гц) - только для веб-панели!
                if current_time - last_world_update >= (1.0 / WORLD_STATE_HZ):
                    publish_world_state(get_radar_targets())
                    last_world_update = current_time

                # Обновление камеры
                update_camera(dt)
                publish_camera_status()
                
                # Вывод статистики
                print(f"\r📍 {own_ship.position.lat:.6f}, {own_ship.position.lon:.6f} | "
                      f"Курс={own_ship.course:5.1f}° | Скорость={own_ship.speed:5.1f} уз | "
                      f"Целей={len(moving_targets)} (видим={len(get_radar_targets())}) | "
                      f"Time={time_scale}x", end="", flush=True)
            
            #time.sleep(UPDATE_INTERVAL)
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n\n👋 Остановка по команде пользователя...")
    finally:
        client.loop_stop()
        client.disconnect()
        print("✅ Sensor Bridge остановлен")


if __name__ == "__main__":
    main()
