# core/constants.py - Global constants for Sensor Bridge

from typing import Final

# =============================================================================
# NAVIGATION CONSTANTS
# =============================================================================

# Earth parameters
EARTH_RADIUS_NM: Final[float] = 3440.065  # Earth radius in nautical miles
DEGREES_PER_CIRCLE: Final[float] = 360.0
MINUTES_PER_DEGREE: Final[float] = 60.0

# Course ranges
COURSE_MIN: Final[float] = 0.0
COURSE_MAX: Final[float] = 359.999999

# Speed limits (typical vessel speeds)
SPEED_MIN: Final[float] = 0.0
SPEED_MAX_CARGO: Final[float] = 25.0  # knots
SPEED_MAX_TANKER: Final[float] = 20.0
SPEED_MAX_PASSENGER: Final[float] = 30.0
SPEED_MAX_YACHT: Final[float] = 15.0

# Position ranges
LAT_MIN: Final[float] = -90.0
LAT_MAX: Final[float] = 90.0
LON_MIN: Final[float] = -180.0
LON_MAX: Final[float] = 180.0

# =============================================================================
# RADAR CONSTANTS
# =============================================================================

# Radar range settings (nautical miles)
RADAR_MIN_RANGE_NM: Final[float] = 0.05
RADAR_MAX_RANGE_NM: Final[float] = 12.0
RADAR_DEFAULT_RANGE_NM: Final[float] = 12.0

# Radar accuracy
RADAR_BEARING_ACCURACY_DEG: Final[float] = 2.0  # ±2 degrees
RADAR_DISTANCE_ACCURACY_NM: Final[float] = 0.01  # ±0.01 NM

# ARPA tracking limits
RADAR_MAX_TARGETS: Final[int] = 50
RADAR_UPDATE_INTERVAL_SEC: Final[float] = 3.0  # 2-4 seconds typical

# =============================================================================
# CAMERA PTZ CONSTANTS
# =============================================================================

# Pan-Tilt-Zoom limits
CAMERA_PAN_MIN: Final[float] = -180.0
CAMERA_PAN_MAX: Final[float] = 180.0
CAMERA_TILT_MIN: Final[float] = -30.0
CAMERA_TILT_MAX: Final[float] = 30.0
CAMERA_ZOOM_MIN: Final[int] = 1
CAMERA_ZOOM_MAX: Final[int] = 10
CAMERA_PAN_SPEED_DEG_SEC: Final[float] = 50.0  # degrees per second

# =============================================================================
# SIMULATION CONSTANTS
# =============================================================================

# Time scale limits
TIMESCALE_MIN: Final[float] = 1.0
TIMESCALE_MAX: Final[float] = 100.0
TIMESCALE_DEFAULT: Final[float] = 1.0

# Update frequencies (Hz)
GPS_UPDATE_HZ: Final[float] = 1.0
RADAR_UPDATE_HZ: Final[float] = 0.3  # ~3 seconds per update
WORLD_STATE_UPDATE_HZ: Final[float] = 5.0  # For web panel
MAIN_LOOP_HZ: Final[float] = 100.0  # 10ms update interval

# =============================================================================
# SHIP TYPE DEFINITIONS
# =============================================================================

SHIP_TYPES: Final[dict] = {
    "cargo": {"length_m": 200, "beam_m": 30, "displacement_t": 50000, "max_speed_knots": 18},
    "tanker": {"length_m": 300, "beam_m": 50, "displacement_t": 150000, "max_speed_knots": 15},
    "passenger": {"length_m": 150, "beam_m": 25, "displacement_t": 20000, "max_speed_knots": 22},
    "fishing": {"length_m": 30, "beam_m": 8, "displacement_t": 150, "max_speed_knots": 12},
    "yacht": {"length_m": 12, "beam_m": 4, "displacement_t": 10, "max_speed_knots": 12},
    "sailing": {"length_m": 15, "beam_m": 5, "displacement_t": 15, "max_speed_knots": 10},
}

# COLREGS ship type codes (for AIS/NMEA)
COLREGS_SHIP_CODES: Final[dict] = {
    "cargo": 70,
    "tanker": 80,
    "passenger": 60,
    "fishing": 30,
    "yacht": 37,
    "sailing": 36,
}

# =============================================================================
# MQTT CONSTANTS
# =============================================================================

MQTT_KEEPALIVE_SEC: Final[int] = 60
MQTT_CONNECT_TIMEOUT_SEC: Final[int] = 10
MQTT_RECONNECT_DELAY_SEC: Final[int] = 5
