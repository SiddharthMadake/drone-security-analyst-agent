"""Object detection module."""
import re
import logging
import time
from typing import List, Optional
from datetime import datetime

from src.models import Detection, FrameRecord, Telemetry

logger = logging.getLogger(__name__)

COLOR_KEYWORDS = [
    "red", "blue", "green", "black", "white", "silver", "gray", "grey",
    "yellow", "orange", "brown", "purple", "gold", "dark", "light"
]

COUNT_WORDS = {
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}

KEYWORD_DETECTION_MAP = {
    "person": (0, "person"),
    "people": (0, "person"),
    "man": (0, "person"),
    "woman": (0, "person"),
    "individual": (0, "person"),
    "car": (2, "car"),
    "sedan": (2, "car"),
    "vehicle": (2, "car"),
    "truck": (7, "truck"),
    "pickup": (7, "truck"),
    "f150": (7, "truck"),
    "ford": (7, "truck"),
    "suv": (2, "car"),
    "bus": (5, "bus"),
    "motorcycle": (3, "motorcycle"),
    "bike": (3, "motorcycle"),
}


def _stable_track_id(keyword: str, location: str = "") -> int:
    s = f"{keyword}:{location}"
    return sum((i + 1) * ord(ch) for i, ch in enumerate(s)) % 10000


class SimulatedDetector:
    def detect(self, description: str, telemetry: Optional[Telemetry] = None) -> List[Detection]:
        desc_lower = description.lower()
        detections = []
        seen_classes = set()

        for keyword, (class_id, class_name) in KEYWORD_DETECTION_MAP.items():
            if keyword in desc_lower and class_name not in seen_classes:
                color = self._extract_color(desc_lower, keyword)
                conf = self._estimate_confidence(desc_lower, keyword)
                count = self._extract_count(desc_lower, keyword)
                for idx in range(count):
                    detections.append(Detection(
                        class_id=class_id,
                        class_name=class_name,
                        confidence=conf,
                        bbox=(0.1, 0.1, 0.9, 0.9),
                        track_id=_stable_track_id(f"{keyword}:{idx}", telemetry.location_label if telemetry else ""),
                        color_estimate=color,
                    ))
                seen_classes.add(class_name)
        return detections

    def _extract_color(self, text: str, near_keyword: str) -> Optional[str]:
        pattern = r'(\w+)\s+' + near_keyword
        match = re.search(pattern, text)
        if match:
            word = match.group(1)
            if word in COLOR_KEYWORDS:
                return word
        tokens = re.findall(r"\w+", text)
        for idx, token in enumerate(tokens):
            if token != near_keyword:
                continue
            for candidate in reversed(tokens[max(0, idx - 3):idx]):
                if candidate in COLOR_KEYWORDS:
                    return candidate
        return None

    def _estimate_confidence(self, text: str, keyword: str) -> float:
        base = 0.82
        if f"a {keyword}" in text or f"the {keyword}" in text:
            base += 0.08
        if "clearly" in text or "identified" in text:
            base += 0.05
        return min(0.97, base)

    def _extract_count(self, text: str, keyword: str) -> int:
        plural = f"{keyword}s"
        patterns = [
            rf"(\d+)\s+{keyword}",
            rf"(\d+)\s+{plural}",
            rf"({'|'.join(COUNT_WORDS)})\s+{keyword}",
            rf"({'|'.join(COUNT_WORDS)})\s+{plural}",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            raw = match.group(1)
            if raw.isdigit():
                return max(1, min(int(raw), 10))
            return COUNT_WORDS.get(raw, 1)
        return 1


class YOLODetector:
    def __init__(self, model_name: str = "yolov8n", confidence: float = 0.45, device: str = "cpu"):
        self.model_name = model_name
        self.confidence = confidence
        self.device = device
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            self.model = YOLO(f"{self.model_name}.pt")
            self.model.to(self.device)
            logger.info(f"YOLOv8 model '{self.model_name}' loaded on {self.device}")
        except ImportError:
            logger.warning("ultralytics not installed - falling back to simulation")
            self.model = None
        except Exception as e:
            logger.error(f"Failed to load YOLO: {e}")
            self.model = None

    def detect(self, image, telemetry: Optional[Telemetry] = None) -> List[Detection]:
        if self.model is None:
            return []
        results = self.model(image, conf=self.confidence, verbose=False)
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                track_id = int(box.id[0]) if box.id is not None else None
                detections.append(Detection(
                    class_id=class_id,
                    class_name=class_name,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                    track_id=track_id,
                ))
        return detections


class DetectionPipeline:
    def __init__(self, config=None):
        self.config = config
        self.yolo = None
        self.simulator = SimulatedDetector()
        self._init_yolo()
        self.stats = {"frames_processed": 0, "total_detections": 0, "inference_ms_avg": 0}

    def _init_yolo(self):
        try:
            model = "yolov8n"
            conf = 0.45
            device = "cpu"
            if self.config:
                model = self.config.model_name
                conf = self.config.confidence_threshold
                device = self.config.device
            self.yolo = YOLODetector(model, conf, device)
            if self.yolo.model is None:
                self.yolo = None
        except Exception as e:
            logger.warning(f"YOLO init failed: {e}")
            self.yolo = None

    def process_frame(self, frame_description: str, telemetry: Optional[Telemetry] = None, image=None) -> FrameRecord:
        t0 = time.perf_counter()
        if image is not None and self.yolo is not None:
            detections = self.yolo.detect(image, telemetry)
        else:
            detections = self.simulator.detect(frame_description, telemetry)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self._update_stats(len(detections), elapsed_ms)
        record = FrameRecord(
            timestamp=telemetry.timestamp if telemetry else datetime.now(),
            telemetry=telemetry,
            detections=detections,
            frame_description=frame_description,
            object_summary=self._build_summary(detections, telemetry),
        )
        logger.debug(f"Frame processed in {elapsed_ms:.1f}ms: {record.object_summary}")
        return record

    def _build_summary(self, detections: List[Detection], telemetry: Optional[Telemetry]) -> str:
        if not detections:
            loc = telemetry.location_label if telemetry else "unknown"
            ts = telemetry.timestamp.strftime("%H:%M") if telemetry else "?"
            return f"No objects detected at {loc}, {ts}."
        parts = []
        for d in detections:
            color = f"{d.color_estimate} " if d.color_estimate else ""
            parts.append(f"{color}{d.class_name}")
        obj_str = ", ".join(parts)
        loc = telemetry.location_label if telemetry else "Unknown"
        ts = telemetry.timestamp.strftime("%H:%M") if telemetry else "?"
        return f"{obj_str.capitalize()} spotted at {loc}, {ts}."

    def _update_stats(self, n_detections: int, ms: float):
        self.stats["frames_processed"] += 1
        self.stats["total_detections"] += n_detections
        n = self.stats["frames_processed"]
        prev_avg = self.stats["inference_ms_avg"]
        self.stats["inference_ms_avg"] = prev_avg + (ms - prev_avg) / n

    def get_stats(self) -> dict:
        return dict(self.stats)
