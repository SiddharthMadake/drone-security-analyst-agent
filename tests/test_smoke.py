from datetime import datetime, timedelta

from src.agent import SecurityQueryAgent
from src.database import SecurityDatabase
from src.detector import DetectionPipeline
from src.engine import AlertEngine
from src.models import Telemetry
from src.settings import settings


def telemetry_at(ts, location="Main Gate"):
    return Telemetry(ts, 0.0, 0.0, 10.0, 0.0, 0.0, location)


def test_truck_logged_and_queryable_by_object(tmp_path):
    db = SecurityDatabase(str(tmp_path / "test.db"))
    pipe = DetectionPipeline(settings.detection)

    ts = datetime(2026, 1, 1, 12, 0)
    record = pipe.process_frame("Blue Ford F150 at garage", telemetry_at(ts, "Garage"))

    assert any(d.class_name == "truck" and d.color_estimate == "blue" for d in record.detections)
    assert "truck" in record.object_summary.lower()
    assert db.insert_frame(record)

    truck_frames = db.query_frames_by_object("truck")
    assert len(truck_frames) == 1
    assert truck_frames[0]["location"] == "Garage"


def test_loitering_alert_triggers_around_midnight():
    pipe = DetectionPipeline(settings.detection)
    engine = AlertEngine(settings.alerts)

    first_ts = datetime(2026, 1, 1, 23, 59, 30)
    second_ts = first_ts + timedelta(seconds=35)

    first = pipe.process_frame("Person standing near main gate", telemetry_at(first_ts))
    second = pipe.process_frame("Person still near main gate", telemetry_at(second_ts))

    engine.process_frame(first)
    alerts = engine.process_frame(second)

    assert any(a.alert_type.value == "LOITERING" for a in alerts)
    assert any("main gate" in a.description.lower() for a in alerts)


def test_frame_index_queryable_by_time_range(tmp_path):
    db = SecurityDatabase(str(tmp_path / "test.db"))
    pipe = DetectionPipeline(settings.detection)

    start = datetime(2026, 1, 1, 0, 0)
    records = [
        pipe.process_frame("Empty driveway", telemetry_at(start, "Driveway")),
        pipe.process_frame("Blue truck at gate", telemetry_at(start + timedelta(minutes=1), "Gate")),
    ]
    for record in records:
        assert db.insert_frame(record)

    rows = db.query_frames_by_timerange(start, start + timedelta(minutes=2))
    assert len(rows) == 2
    assert rows[1]["location"] == "Gate"


def test_agent_answers_object_question(tmp_path):
    db = SecurityDatabase(str(tmp_path / "test.db"))
    pipe = DetectionPipeline(settings.detection)
    record = pipe.process_frame("Blue truck at gate", telemetry_at(datetime(2026, 1, 1, 0, 1), "Gate"))
    assert db.insert_frame(record)

    answer = SecurityQueryAgent(db).answer("show all truck events")

    assert "Found 1 truck frame" in answer["answer"]
    assert answer["frames"][0]["location"] == "Gate"


def test_agent_can_enhance_answer_with_local_llm_without_changing_evidence(tmp_path):
    class FakeLLMAgent(SecurityQueryAgent):
        def _ask_ollama(self, question, rule_answer, evidence):
            assert "Blue truck at gate" in evidence
            return "The local analyst view confirms one blue truck event at Gate."

    db = SecurityDatabase(str(tmp_path / "test.db"))
    pipe = DetectionPipeline(settings.detection)
    record = pipe.process_frame("Blue truck at gate", telemetry_at(datetime(2026, 1, 1, 0, 1), "Gate"))
    assert db.insert_frame(record)

    answer = FakeLLMAgent(db, enable_llm=True).answer("was a truck seen at gate?")

    assert "Found 1 truck frame" in answer["answer"]
    assert "local analyst view" in answer["answer"]
    assert answer["answer_source"].startswith("ollama:")
    assert answer["frames"][0]["location"] == "Gate"


def test_crowd_rule_uses_simulated_people_count():
    pipe = DetectionPipeline(settings.detection)
    engine = AlertEngine(settings.alerts)
    record = pipe.process_frame(
        "Three people and a truck at restricted area",
        telemetry_at(datetime(2026, 1, 1, 12, 0), "Restricted Area"),
    )

    alerts = engine.process_frame(record)

    assert sum(1 for d in record.detections if d.class_name == "person") == 3
    assert any(a.alert_type.value == "CROWD_DETECTED" for a in alerts)


def test_repeated_vehicle_alert_for_returning_truck():
    pipe = DetectionPipeline(settings.detection)
    engine = AlertEngine(settings.alerts)

    first_ts = datetime(2026, 1, 1, 12, 0)
    second_ts = first_ts + timedelta(minutes=10)
    first = pipe.process_frame("Blue Ford F150 at garage", telemetry_at(first_ts, "Garage"))
    second = pipe.process_frame("Blue Ford F150 returned to garage", telemetry_at(second_ts, "Garage"))

    engine.process_frame(first)
    alerts = engine.process_frame(second)

    assert any(a.alert_type.value == "REPEATED_VEHICLE" for a in alerts)
    assert any("truck entered Garage 2 times" in a.description for a in alerts)
