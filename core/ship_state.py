# core/ship_state.py - Model for ship state and position

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import math


@dataclass
class Position:
    """Geographic position with utility methods.
    
    Attributes:
        lat: Latitude in decimal degrees (-90 to +90)
        lon: Longitude in decimal degrees (-180 to +180)
    """
    lat: float  # Latitude (-90 to +90)
    lon: float  # Longitude (-180 to +180)
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate distance to another position in nautical miles.
        
        Uses simplified formula suitable for short distances.
        
        Args:
            other: Another Position object
            
        Returns:
            Distance in nautical miles
        """
        # 1 degree latitude ≈ 60 nautical miles
        delta_lat = (other.lat - self.lat) * 60
        
        # 1 degree longitude ≈ 60 * cos(latitude) nautical miles
        avg_lat = math.radians((self.lat + other.lat) / 2)
        delta_lon = (other.lon - self.lon) * 60 * math.cos(avg_lat)
        
        return math.sqrt(delta_lat**2 + delta_lon**2)
    
    def bearing_to(self, other: 'Position') -> float:
        """Calculate bearing (azimuth) to another position in degrees (0-360).
        
        0° = North, 90° = East, 180° = South, 270° = West
        
        Args:
            other: Another Position object
            
        Returns:
            Bearing in degrees (0-360)
        """
        delta_lon = math.radians(other.lon - self.lon)
        lat1 = math.radians(self.lat)
        lat2 = math.radians(other.lat)
        
        x = math.sin(delta_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
        
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360
    
    def offset_by(self, distance_nm: float, bearing_deg: float) -> 'Position':
        """Calculate new position by offsetting from current position.
        
        Args:
            distance_nm: Distance to offset in nautical miles
            bearing_deg: Bearing in degrees (0-360)
            
        Returns:
            New Position object
        """
        bearing_rad = math.radians(bearing_deg)
        
        delta_lat = (distance_nm * math.cos(bearing_rad)) / 60
        delta_lon = (distance_nm * math.sin(bearing_rad)) / (60 * math.cos(math.radians(self.lat)))
        
        return Position(
            lat=self.lat + delta_lat,
            lon=self.lon + delta_lon
        )
    
    def to_dict(self) -> Dict[str, float]:
        """Convert position to dictionary.
        
        Returns:
            Dictionary with lat/lon keys
        """
        return {"lat": self.lat, "lon": self.lon}
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'Position':
        """Create Position from dictionary.
        
        Args:
            data: Dictionary with lat/lon keys
            
        Returns:
            Position object
        """
        return cls(lat=data["lat"], lon=data["lon"])


@dataclass
class ShipState:
    """Ship state at a specific moment in time.
    
    Used for:
    - Own ship tracking
    - Target vessel tracking
    
    Attributes:
        position: Geographic position
        course: Course over ground in degrees (0-360)
        speed: Speed in knots
        timestamp: UNIX timestamp
        ship_id: Unique identifier (OWN for own ship, R01/R02 for targets)
        ship_type: Type of vessel (power, sailing, fishing, cargo, etc.)
        heading: Vessel heading (may differ from course due to drift)
        rate_of_turn: Angular turn rate (degrees/minute)
    """
    position: Position
    course: float           # Course in degrees (0-360)
    speed: float            # Speed in knots
    timestamp: float        # UNIX timestamp
    ship_id: str = "OWN"    # Unique ID (OWN for own ship, R01, R02 for targets)
    ship_type: str = "power"  # Ship type: power, sailing, fishing, etc.
    heading: Optional[float] = None  # Heading (may differ from course due to drift)
    rate_of_turn: float = 0.0  # Turn rate (degrees/minute)
    
    def __post_init__(self):
        """Validate after initialization."""
        if not -90 <= self.position.lat <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {self.position.lat}")
        if not -180 <= self.position.lon <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {self.position.lon}")
        if not 0 <= self.course < 360:
            raise ValueError(f"Course must be between 0 and 360, got {self.course}")
        if self.speed < 0:
            raise ValueError(f"Speed cannot be negative, got {self.speed}")
        
        # If heading is not set, use course
        if self.heading is None:
            self.heading = self.course
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/MQTT.
        
        Returns:
            Dictionary representation of ship state
        """
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
    def from_dict(cls, data: Dict[str, Any]) -> 'ShipState':
        """Create ShipState from dictionary.
        
        Args:
            data: Dictionary with ship state data
            
        Returns:
            ShipState object
        """
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
    """Radar target with ARPA tracking data.
    
    Attributes:
        target_id: Target identifier
        bearing: Relative bearing in degrees (0-360)
        distance: Distance in nautical miles
        course: Target course in degrees
        speed: Target speed in knots
        timestamp: UNIX timestamp
        cpa: Closest Point of Approach (nautical miles)
        tcpa: Time to CPA (minutes)
        ship_type: Type of vessel
        absolute_position: Absolute lat/lon position
    """
    target_id: str
    bearing: float
    distance: float
    course: float
    speed: float
    timestamp: float
    cpa: Optional[float] = None
    tcpa: Optional[float] = None
    ship_type: str = "cargo"
    absolute_position: Optional[Dict[str, float]] = None
    
    def __post_init__(self):
        """Validate after initialization."""
        if not 0 <= self.bearing < 360:
            raise ValueError(f"Bearing must be between 0 and 360, got {self.bearing}")
        if self.distance < 0:
            raise ValueError(f"Distance cannot be negative, got {self.distance}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/MQTT.
        
        Returns:
            Dictionary representation of radar target
        """
        result = {
            "id": self.target_id,
            "bearing": round(self.bearing, 2),
            "distance": round(self.distance, 2),
            "course": round(self.course, 2),
            "speed": round(self.speed, 1),
            "timestamp": int(self.timestamp),
            "cpa": round(self.cpa, 2) if self.cpa is not None else None,
            "tcpa": round(self.tcpa, 1) if self.tcpa is not None else None,
            "type": self.ship_type
        }
        # Add absolute_position if available
        if self.absolute_position:
            result["absolute_position"] = self.absolute_position
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RadarTarget':
        """Create RadarTarget from dictionary.
        
        Args:
            data: Dictionary with radar target data
            
        Returns:
            RadarTarget object
        """
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
    """Ship control inputs.
    
    Used for simulation (autopilot or manual control).
    
    Attributes:
        throttle: Engine throttle (0.0 - 1.0)
        rudder_angle: Rudder angle (-35 to +35 degrees)
        target_course: Target course for autopilot
        target_speed: Target speed for autopilot
    """
    throttle: float = 0.0   # Engine throttle (0.0 - 1.0)
    rudder_angle: float = 0.0  # Rudder angle (-35 to +35 degrees)
    target_course: Optional[float] = None  # Target course for autopilot
    target_speed: Optional[float] = None   # Target speed for autopilot
    
    def __post_init__(self):
        """Validate after initialization."""
        if not 0 <= self.throttle <= 1.0:
            raise ValueError(f"Throttle must be between 0 and 1, got {self.throttle}")
        if not -35 <= self.rudder_angle <= 35:
            raise ValueError(f"Rudder angle must be between -35 and 35, got {self.rudder_angle}")