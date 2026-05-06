"""VLM caption generator."""
import logging
import os
from typing import List, Optional

from src.models import Detection, FrameRecord, Telemetry

logger = logging.getLogger(__name__)


def _build_detection_context(detections: List[Detection], telemetry: Optional[Telemetry]) -> str:
    if not detections:
        return "No objects detected."
    parts = []
    for d in detections:
        color = f"{d.color_estimate} " if d.color_estimate else ""
        parts.append(f"- {color}{d.class_name} (confidence: {d.confidence:.0%})")
    loc = telemetry.location_label if telemetry else "unknown"
    ts = telemetry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if telemetry else "?"
    return (
        f"Location: {loc}\n"
        f"Time: {ts}\n"
        f"Objects:\n"
        + "\n".join(parts)
    )


class VLMCaptionGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.info("VLM captions disabled - no ANTHROPIC_API_KEY found. Using rule-based captions.")

    def generate_caption(self, record: FrameRecord) -> str:
        if self.enabled:
            try:
                return self._claude_caption(record)
            except Exception as e:
                logger.warning(f"Claude API failed, falling back: {e}")
        return self._rule_based_caption(record)

    def _claude_caption(self, record: FrameRecord) -> str:
        import urllib.request, json
        context = _build_detection_context(record.detections, record.telemetry)
        raw_desc = record.frame_description or ""
        prompt = f"""You are a drone security analyst AI. Generate a concise, professional security log entry.

Frame context:
{context}

Raw frame description: {raw_desc}

Write ONE sentence (max 25 words) describing what was observed in security surveillance language.
Focus on: who/what, where, when, any anomalies. Be factual and specific."""
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 80,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data["content"][0]["text"].strip()

    def _rule_based_caption(self, record: FrameRecord) -> str:
        if not record.detections:
            loc = record.telemetry.location_label if record.telemetry else "the area"
            ts = record.timestamp.strftime("%H:%M")
            return f"No objects detected at {loc} at {ts}."
        parts = []
        for d in record.detections:
            color = f"{d.color_estimate} " if d.color_estimate else ""
            parts.append(f"{color}{d.class_name}")
        obj_list = ", ".join(parts)
        loc = record.telemetry.location_label if record.telemetry else "unknown location"
        ts = record.timestamp.strftime("%H:%M")
        return f"{obj_list.capitalize()} observed at {loc} at {ts}."

    def generate_daily_summary(self, records: List[FrameRecord], alerts_summary: str) -> str:
        if not records:
            return "No activity recorded today."
        if self.enabled:
            try:
                return self._claude_daily_summary(records, alerts_summary)
            except Exception as e:
                logger.warning(f"Daily summary API failed: {e}")
        return self._rule_based_summary(records, alerts_summary)

    def _claude_daily_summary(self, records: List[FrameRecord], alerts_summary: str) -> str:
        import urllib.request, json
        object_counts: dict = {}
        locations_seen = set()
        for r in records:
            for d in r.detections:
                object_counts[d.class_name] = object_counts.get(d.class_name, 0) + 1
            if r.telemetry:
                locations_seen.add(r.telemetry.location_label)
        events_str = ", ".join(f"{v} {k}(s)" for k, v in sorted(object_counts.items(), key=lambda x: -x[1]))
        prompt = f"""Summarize a drone security patrol day in ONE sentence (max 30 words).

Observed: {events_str}
Locations covered: {', '.join(locations_seen)}
Alerts: {alerts_summary}

Write a professional summary sentence for a security report."""
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 60,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data["content"][0]["text"].strip()

    def _rule_based_summary(self, records: List[FrameRecord], alerts_summary: str) -> str:
        object_counts: dict = {}
        for r in records:
            for d in r.detections:
                object_counts[d.class_name] = object_counts.get(d.class_name, 0) + 1
        top = sorted(object_counts.items(), key=lambda x: -x[1])[:3]
        events = ", ".join(f"{v} {k}(s)" for k, v in top) if top else "no objects"
        return f"Daily patrol recorded {len(records)} frames with {events}; alerts: {alerts_summary}."
