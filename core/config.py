# core/config.py - Configuration management for Sensor Bridge

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables.
    
    Attributes:
        mqtt_host: MQTT broker hostname
        mqtt_port: MQTT broker port
        mqtt_client_id: Client ID for MQTT connection
        radar_range_nm: Radar detection range in nautical miles
        default_timescale: Default simulation time scale multiplier
        world_state_hz: Frequency of world state updates (Hz)
        update_interval: Main loop update interval (seconds)
    """
    
    def __init__(self):
        # MQTT Settings
        self.mqtt_host: str = os.getenv("MQTT_HOST", "localhost")
        self.mqtt_port: int = int(os.getenv("MQTT_PORT", 1883))
        self.mqtt_client_id: str = os.getenv("MQTT_CLIENT_ID", "sensor-bridge")
        
        # Simulation Settings
        self.radar_range_nm: float = float(os.getenv("RADAR_RANGE_NM", "12.0"))
        self.default_timescale: float = float(os.getenv("DEFAULT_TIMESCALE", "1.0"))
        self.world_state_hz: float = float(os.getenv("WORLD_STATE_HZ", "5.0"))
        self.update_interval: float = float(os.getenv("UPDATE_INTERVAL", "0.01"))
        
        # GPS Emulator Settings
        self.gps_update_rate: float = float(os.getenv("GPS_UPDATE_RATE", "1.0"))
        self.gps_noise_std: float = float(os.getenv("GPS_NOISE_STD", "0.00001"))
        
        # Radar Emulator Settings
        self.radar_min_range_nm: float = float(os.getenv("RADAR_MIN_RANGE", "0.05"))
        self.radar_max_targets: int = int(os.getenv("RADAR_MAX_TARGETS", "50"))
        self.radar_update_interval: float = float(os.getenv("RADAR_UPDATE_INTERVAL", "3.0"))


# Global settings instance
settings = Settings()


def get_mqtt_topics() -> dict:
    """Returns dictionary of MQTT topics used by Sensor Bridge.
    
    Returns:
        Dictionary mapping topic names to topic strings
    """
    return {
        "NMEA_RAW": "sensors/nmea/raw",
        "RADAR_TARGETS": "sensors/radar/targets",
        "WORLD_STATE": "sensors/world_state",
        "CAMERA_STATUS": "camera/status",
        "PTZ_COMMAND": "control/ptz/command",
        "SIMULATION_COMMAND": "control/simulation/command"
    }
