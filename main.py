"""Local demo runner for the Drone Security Analyst Agent."""
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
import os

from src.database import SecurityDatabase
from src.detector import DetectionPipeline
from src.engine import AlertEngine
from src.models import Telemetry
from src.settings import settings
from src.agent import SecurityQueryAgent
from src.vlm import VLMCaptionGenerator


def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, settings.logging.level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler()]
    )


def demo_frames(start_time: datetime | None = None):
    start_time = start_time or datetime.now().replace(hour=23, minute=58, second=0, microsecond=0)
    samples = [
        ("Blue Ford F150 at garage entrance", "Garage"),
        ("Person standing near main gate", "Main Gate"),
        ("Person still near main gate", "Main Gate"),
        ("Three people and a truck at restricted area", "Restricted Area"),
        ("Empty driveway", "Driveway"),
        ("Red car and motorcycle near back entrance", "Back Entrance"),
        ("Blue Ford F150 returned to garage entrance", "Garage"),
    ]
    for i, (desc, location) in enumerate(samples):
        ts = start_time + timedelta(seconds=i * 35)
        yield desc, Telemetry(
            timestamp=ts,
            latitude=18.5204,
            longitude=73.8567,
            altitude=45.0,
            heading=90.0,
            speed=2.5,
            location_label=location,
            battery_pct=88.0,
        )


def run_demo():
    setup_logging()
    db = SecurityDatabase(settings.database.db_path)
    db.clear_all()
    pipeline = DetectionPipeline(settings.detection)
    engine = AlertEngine(settings.alerts)
    vlm = VLMCaptionGenerator(settings.anthropic_api_key)

    records = []
    all_alerts = []

    for desc, telemetry in demo_frames():
        record = pipeline.process_frame(desc, telemetry=telemetry)
        record.caption = vlm.generate_caption(record)
        db.insert_frame(record)
        alerts = engine.process_frame(record)
        for alert in alerts:
            db.insert_alert(alert)
        records.append(record)
        all_alerts.extend(alerts)
        print()
        print("FRAME:", record.frame_id)
        print("TIME:", record.timestamp.isoformat())
        print("LOCATION:", record.telemetry.location_label if record.telemetry else "Unknown")
        print("SUMMARY:", record.object_summary)
        print("CAPTION:", record.caption)
        if alerts:
            for a in alerts:
                print("ALERT:", a.description, f"[{a.severity.value}]")
        else:
            print("ALERT: none")

    print()
    print("=== STATS ===")
    print(json.dumps(pipeline.get_stats(), indent=2))
    print()
    print("=== DATABASE STATS ===")
    print(json.dumps(db.get_statistics(), indent=2))
    print()
    print("=== DAILY SUMMARY ===")
    print(vlm.generate_daily_summary(records, alerts_summary=f"{len(all_alerts)} alerts"))

    print()
    print("=== SEARCH EXAMPLES ===")
    print("truck frames:", len(db.query_frames_by_object("truck")))
    print("person frames:", len(db.query_frames_by_object("person")))
    print("fulltext search 'gate':", len(db.fulltext_search("gate")))

    agent = SecurityQueryAgent(db)
    print()
    print("=== AGENT Q&A EXAMPLES ===")
    for question in [
        "show all truck events",
        "what alerts happened?",
        "summary of activity",
    ]:
        print("Q:", question)
        print("A:", agent.answer(question)["answer"])

    out = Path("data/demo_output.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "frames": [r.to_dict() for r in records],
        "alerts": [a.to_dict() for a in all_alerts],
        "stats": pipeline.get_stats(),
        "db_stats": db.get_statistics(),
    }, indent=2), encoding="utf-8")
    print()
    print(f"Saved demo output to {out}")


if __name__ == "__main__":
    run_demo()
