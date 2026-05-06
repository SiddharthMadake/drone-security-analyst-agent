"""Core data models for Drone Security Analyst Agent."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid


class AlertSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertType(Enum):
    LOITERING = "LOITERING"
    INTRUSION = "INTRUSION"
    REPEATED_VEHICLE = "REPEATED_VEHICLE"
    UNAUTHORIZED_ZONE = "UNAUTHORIZED_ZONE"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    CROWD_DETECTED = "CROWD_DETECTED"


@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: tuple
    track_id: Optional[int] = None
    color_estimate: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 3),
            "bbox": list(self.bbox),
            "track_id": self.track_id,
            "color_estimate": self.color_estimate,
        }


@dataclass
class Telemetry:
    timestamp: datetime
    latitude: float
    longitude: float
    altitude: float
    heading: float
    speed: float
    location_label: str
    battery_pct: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "heading": self.heading,
            "speed": self.speed,
            "location_label": self.location_label,
            "battery_pct": self.battery_pct,
        }


@dataclass
class FrameRecord:
    frame_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    telemetry: Optional[Telemetry] = None
    detections: List[Detection] = field(default_factory=list)
    caption: Optional[str] = None
    frame_description: Optional[str] = None
    object_summary: Optional[str] = None
    embedding: Optional[List[float]] = None

    def detected_classes(self) -> List[str]:
        return list(set(d.class_name for d in self.detections))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp.isoformat(),
            "telemetry": self.telemetry.to_dict() if self.telemetry else None,
            "detections": [d.to_dict() for d in self.detections],
            "detected_classes": self.detected_classes(),
            "caption": self.caption,
            "frame_description": self.frame_description,
            "object_summary": self.object_summary,
            "location": self.telemetry.location_label if self.telemetry else "Unknown",
        }


@dataclass
class Alert:
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    alert_type: AlertType = AlertType.SUSPICIOUS_ACTIVITY
    severity: AlertSeverity = AlertSeverity.MEDIUM
    location: str = "Unknown"
    description: str = ""
    frame_ids: List[str] = field(default_factory=list)
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp.isoformat(),
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "location": self.location,
            "description": self.description,
            "frame_ids": self.frame_ids,
            "resolved": self.resolved,
            "metadata": self.metadata,
        }


@dataclass
class QueryResult:
    frames: List[FrameRecord] = field(default_factory=list)
    alerts: List[Alert] = field(default_factory=list)
    total_count: int = 0
    query: str = ""
    execution_time_ms: float = 0.0
