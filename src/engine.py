"""Production alert engine."""
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import threading

from src.models import Alert, AlertSeverity, AlertType, FrameRecord

logger = logging.getLogger(__name__)


class AlertEngine:
    def __init__(self, config=None):
        self._lock = threading.Lock()
        self.loitering_threshold_s = 30
        self.off_hours_start = 22
        self.off_hours_end = 6
        self.repeated_vehicle_n = 2
        self.repeated_vehicle_window_m = 60
        self.restricted_zones = {"server_room", "vault", "restricted_area", "back_entrance"}
        self.alert_cooldown_s = 60
        self.crowd_threshold = 3

        if config:
            self.loitering_threshold_s = config.loitering_threshold_seconds
            self.off_hours_start = config.intrusion_off_hours_start
            self.off_hours_end = config.intrusion_off_hours_end
            self.repeated_vehicle_n = config.repeated_vehicle_threshold
            self.repeated_vehicle_window_m = config.repeated_vehicle_window_minutes
            self.restricted_zones = set(config.restricted_zones)
            self.alert_cooldown_s = config.alert_cooldown_seconds

        self._presence_log: Dict[Tuple, deque] = defaultdict(lambda: deque(maxlen=500))
        self._vehicle_log: Dict[Tuple, deque] = defaultdict(lambda: deque(maxlen=200))
        self._cooldown: Dict[str, datetime] = {}
        self._alerts: List[Alert] = []

    def process_frame(self, record: FrameRecord) -> List[Alert]:
        new_alerts: List[Alert] = []
        with self._lock:
            ts = record.timestamp
            location = record.telemetry.location_label if record.telemetry else "Unknown"
            for detection in record.detections:
                key = (location, detection.class_name)
                self._presence_log[key].append((ts, record.frame_id))
                if detection.class_name in ("car", "truck", "bus", "motorcycle"):
                    vkey = (location, detection.class_name)
                    self._vehicle_log[vkey].append(ts)

            new_alerts.extend(self._check_loitering(location, ts))
            new_alerts.extend(self._check_intrusion(record, location, ts))
            new_alerts.extend(self._check_repeated_vehicle(record, location, ts))
            new_alerts.extend(self._check_unauthorized_zone(record, location, ts))
            new_alerts.extend(self._check_crowd(record, location, ts))
            self._alerts.extend(new_alerts)

        for alert in new_alerts:
            logger.warning(f"[ALERT] {alert.severity.value} | {alert.alert_type.value} | {alert.description}")
        return new_alerts

    def _can_alert(self, key: str, ts: datetime) -> bool:
        if key in self._cooldown:
            elapsed = (ts - self._cooldown[key]).total_seconds()
            if elapsed < self.alert_cooldown_s:
                return False
        self._cooldown[key] = ts
        return True

    def _check_loitering(self, location: str, ts: datetime) -> List[Alert]:
        alerts = []
        key = (location, "person")
        log = self._presence_log[key]
        if len(log) < 2:
            return alerts
        first_seen = log[0][0]
        duration_s = (ts - first_seen).total_seconds()
        if duration_s >= self.loitering_threshold_s:
            alert_key = f"loitering:{location}"
            if self._can_alert(alert_key, ts):
                alerts.append(Alert(
                    timestamp=ts,
                    alert_type=AlertType.LOITERING,
                    severity=self._loitering_severity(duration_s, ts),
                    location=location,
                    description=f"Person loitering at {location} for {int(duration_s)}s.",
                    frame_ids=[fid for _, fid in list(log)[-5:]],
                    metadata={"duration_seconds": round(duration_s, 1)},
                ))
        return alerts

    def _loitering_severity(self, duration_s: float, ts: datetime) -> AlertSeverity:
        hour = ts.hour
        off_hours = (hour >= self.off_hours_start or hour < self.off_hours_end)
        if off_hours and duration_s > 120:
            return AlertSeverity.CRITICAL
        if off_hours or duration_s > 90:
            return AlertSeverity.HIGH
        return AlertSeverity.MEDIUM

    def _check_intrusion(self, record: FrameRecord, location: str, ts: datetime) -> List[Alert]:
        alerts = []
        hour = ts.hour
        is_off_hours = (hour >= self.off_hours_start or hour < self.off_hours_end)
        if not is_off_hours:
            return alerts
        has_person = any(d.class_name == "person" for d in record.detections)
        if not has_person:
            return alerts
        alert_key = f"intrusion:{location}"
        if self._can_alert(alert_key, ts):
            alerts.append(Alert(
                timestamp=ts,
                alert_type=AlertType.INTRUSION,
                severity=AlertSeverity.HIGH,
                location=location,
                description=f"Person detected during off-hours at {location} ({ts.strftime('%H:%M')}).",
                frame_ids=[record.frame_id],
                metadata={"hour": hour, "off_hours": True},
            ))
        return alerts

    def _check_repeated_vehicle(self, record: FrameRecord, location: str, ts: datetime) -> List[Alert]:
        alerts = []
        vehicle_classes = [d.class_name for d in record.detections if d.class_name in ("car", "truck", "bus")]
        for vclass in set(vehicle_classes):
            vkey = (location, vclass)
            window_start = ts - timedelta(minutes=self.repeated_vehicle_window_m)
            recent = [t for t in self._vehicle_log[vkey] if t >= window_start]
            if len(recent) >= self.repeated_vehicle_n:
                alert_key = f"repeated_vehicle:{location}:{vclass}"
                if self._can_alert(alert_key, ts):
                    color_hints = [d.color_estimate for d in record.detections if d.class_name == vclass and d.color_estimate]
                    color_str = f"{color_hints[0]} " if color_hints else ""
                    alerts.append(Alert(
                        timestamp=ts,
                        alert_type=AlertType.REPEATED_VEHICLE,
                        severity=AlertSeverity.MEDIUM,
                        location=location,
                        description=(
                            f"{color_str.capitalize()}{vclass} entered {location} "
                            f"{len(recent)} times in {self.repeated_vehicle_window_m} minutes."
                        ),
                        frame_ids=[record.frame_id],
                        metadata={"vehicle_class": vclass, "count": len(recent)},
                    ))
        return alerts

    def _check_unauthorized_zone(self, record: FrameRecord, location: str, ts: datetime) -> List[Alert]:
        alerts = []
        loc_lower = location.lower().replace(" ", "_")
        is_restricted = any(zone in loc_lower for zone in self.restricted_zones)
        if not is_restricted:
            return alerts
        has_person = any(d.class_name == "person" for d in record.detections)
        if not has_person:
            return alerts
        alert_key = f"unauth_zone:{location}"
        if self._can_alert(alert_key, ts):
            alerts.append(Alert(
                timestamp=ts,
                alert_type=AlertType.UNAUTHORIZED_ZONE,
                severity=AlertSeverity.CRITICAL,
                location=location,
                description=f"Unauthorized person detected in restricted area: {location}.",
                frame_ids=[record.frame_id],
                metadata={"zone": location, "restricted": True},
            ))
        return alerts

    def _check_crowd(self, record: FrameRecord, location: str, ts: datetime) -> List[Alert]:
        alerts = []
        person_count = sum(1 for d in record.detections if d.class_name == "person")
        if person_count >= self.crowd_threshold:
            alert_key = f"crowd:{location}"
            if self._can_alert(alert_key, ts):
                alerts.append(Alert(
                    timestamp=ts,
                    alert_type=AlertType.CROWD_DETECTED,
                    severity=AlertSeverity.MEDIUM,
                    location=location,
                    description=f"Crowd detected at {location}: {person_count} persons.",
                    frame_ids=[record.frame_id],
                    metadata={"person_count": person_count},
                ))
        return alerts

    def get_all_alerts(self) -> List[Alert]:
        with self._lock:
            return list(self._alerts)

    def clear_state(self):
        with self._lock:
            self._presence_log.clear()
            self._vehicle_log.clear()
            self._cooldown.clear()
            self._alerts.clear()
