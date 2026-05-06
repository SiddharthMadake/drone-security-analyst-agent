"""Production configuration for Drone Security Analyst Agent."""
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DetectionConfig:
    model_name: str = "yolov8n"
    confidence_threshold: float = 0.45
    iou_threshold: float = 0.50
    device: str = "cpu"
    imgsz: int = 640
    classes_of_interest: List[int] = field(default_factory=lambda: [0, 2, 5, 7, 3, 15, 16])
    coco_class_names: dict = field(default_factory=lambda: {
        0: "person", 2: "car", 5: "bus", 7: "truck",
        3: "motorcycle", 15: "cat", 16: "dog",
        1: "bicycle", 4: "airplane", 6: "train"
    })


@dataclass
class AlertConfig:
    loitering_threshold_seconds: int = 30
    intrusion_off_hours_start: int = 22
    intrusion_off_hours_end: int = 6
    repeated_vehicle_threshold: int = 2
    repeated_vehicle_window_minutes: int = 60
    restricted_zones: List[str] = field(default_factory=lambda: [
        "server_room", "vault", "restricted_area", "back_entrance"
    ])
    alert_cooldown_seconds: int = 60


@dataclass
class DatabaseConfig:
    db_path: str = "data/security.db"
    vector_store_path: str = "data/vector_store"
    enable_vector_search: bool = True
    embedding_model: str = "clip"


@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["*"])


@dataclass
class OllamaConfig:
    enabled: bool = field(default_factory=lambda: os.getenv("OLLAMA_AGENT_ENABLED", "1").lower() not in {"0", "false", "no"})
    base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2:3b"))
    timeout_seconds: float = field(default_factory=lambda: float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60.0")))
    temperature: float = field(default_factory=lambda: float(os.getenv("OLLAMA_TEMPERATURE", "0.2")))


@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_file: str = "logs/agent.log"
    max_bytes: int = 10_000_000
    backup_count: int = 5


@dataclass
class Settings:
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    api: APIConfig = field(default_factory=APIConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    enable_vlm_captions: bool = True
    enable_langchain_agent: bool = True


settings = Settings()
