"""Simple query agent over indexed drone security events."""
from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from datetime import datetime, time
from typing import Any, Dict, List, Optional

from src.database import SecurityDatabase
from src.settings import settings


OBJECT_TERMS = ("person", "truck", "car", "bus", "motorcycle", "vehicle")
logger = logging.getLogger(__name__)


class SecurityQueryAgent:
    """Answers common follow-up questions from the SQLite frame index.

    The deterministic database query is always performed first. When local
    Ollama is available, the retrieved evidence is passed to a small local LLM
    for a clearer analyst-style answer.
    """

    def __init__(
        self,
        db: SecurityDatabase,
        enable_llm: Optional[bool] = None,
        ollama_model: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
    ):
        self.db = db
        self.enable_llm = settings.ollama.enabled if enable_llm is None else enable_llm
        self.ollama_model = ollama_model or settings.ollama.model
        self.ollama_base_url = (ollama_base_url or settings.ollama.base_url).rstrip("/")
        self.ollama_timeout = settings.ollama.timeout_seconds
        self.ollama_temperature = settings.ollama.temperature

    def answer(self, question: str) -> Dict[str, Any]:
        q = question.strip()
        q_lower = q.lower()
        if not q:
            return {
                "answer": "Ask about alerts, objects, frames, or activity summaries.",
                "frames": [],
                "alerts": [],
                "answer_source": "rules",
            }

        if "alert" in q_lower:
            alerts = self.db.get_alerts(limit=10)
            if not alerts:
                return {"answer": "No alerts are currently indexed.", "frames": [], "alerts": [], "answer_source": "rules"}
            result = {
                "answer": f"Found {len(alerts)} recent alert(s). Most recent: {alerts[0]['description']}",
                "frames": [],
                "alerts": alerts,
            }
            return self._enhance_with_llm(q, result)

        object_class = self._find_object(q_lower)
        if object_class:
            frames = self.db.query_frames_by_object(object_class, limit=20)
            frames = self._filter_after_midnight(frames) if "after midnight" in q_lower else frames
            result = {
                "answer": self._describe_frames(frames, object_class),
                "frames": frames,
                "alerts": [],
            }
            return self._enhance_with_llm(q, result)

        if "summary" in q_lower or "what happened" in q_lower or "activity" in q_lower:
            return self.summary()

        frames = self.db.fulltext_search(self._safe_fts_query(q), limit=10)
        result = {
            "answer": self._describe_frames(frames, "matching event"),
            "frames": frames,
            "alerts": [],
        }
        return self._enhance_with_llm(q, result)

    def summary(self) -> Dict[str, Any]:
        stats = self.db.get_statistics()
        alerts = self.db.get_alerts(limit=5)
        answer = (
            f"Indexed {stats['total_frames']} frame(s), {stats['total_alerts']} alert(s), "
            f"and {stats['open_alerts']} open alert(s)."
        )
        if alerts:
            answer += f" Latest alert: {alerts[0]['description']}"
        return {"answer": answer, "stats": stats, "alerts": alerts, "frames": [], "answer_source": "rules"}

    def _find_object(self, q_lower: str) -> str | None:
        for term in OBJECT_TERMS:
            if term in q_lower:
                return "car" if term == "vehicle" else term
        return None

    def _filter_after_midnight(self, frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered = []
        for frame in frames:
            ts = datetime.fromisoformat(frame["timestamp"]).time()
            if time(0, 0) <= ts < time(6, 0):
                filtered.append(frame)
        return filtered

    def _describe_frames(self, frames: List[Dict[str, Any]], label: str) -> str:
        if not frames:
            return f"No {label} frames found in the index."
        first = frames[0]
        location = first.get("location") or "unknown location"
        timestamp = first.get("timestamp", "")
        return f"Found {len(frames)} {label} frame(s). Most recent was at {location} around {timestamp}."

    def _safe_fts_query(self, question: str) -> str:
        terms = re.findall(r"\w+", question)
        if not terms:
            return '""'
        return " OR ".join(f'"{term}"' for term in terms[:8])

    def _enhance_with_llm(self, question: str, result: Dict[str, Any]) -> Dict[str, Any]:
        result.setdefault("answer_source", "rules")
        if not self.enable_llm:
            return result

        evidence = self._build_evidence(result)
        if not evidence:
            return result

        try:
            llm_answer = self._ask_ollama(question, result["answer"], evidence)
        except Exception as exc:
            logger.info("Ollama agent answer unavailable; using rule-based answer: %s", exc)
            return result

        if not llm_answer:
            return result

        llm_answer = self._clean_llm_answer(llm_answer, result["answer"])
        if not llm_answer:
            return result

        result["answer"] = f"{result['answer']} {llm_answer}"
        result["answer_source"] = f"ollama:{self.ollama_model}"
        return result

    def _build_evidence(self, result: Dict[str, Any]) -> str:
        lines = [f"Rule answer: {result.get('answer', '')}"]

        frames = result.get("frames") or []
        if frames:
            lines.append("Frames:")
            for frame in frames[:8]:
                objects = self._decode_json(frame.get("objects_json"), [])
                lines.append(
                    "- "
                    f"time={frame.get('timestamp')}; "
                    f"location={frame.get('location') or 'unknown'}; "
                    f"objects={objects}; "
                    f"description={frame.get('frame_desc') or ''}; "
                    f"summary={frame.get('summary') or ''}; "
                    f"caption={frame.get('caption') or ''}"
                )

        alerts = result.get("alerts") or []
        if alerts:
            lines.append("Alerts:")
            for alert in alerts[:8]:
                lines.append(
                    "- "
                    f"time={alert.get('timestamp')}; "
                    f"type={alert.get('alert_type')}; "
                    f"severity={alert.get('severity')}; "
                    f"location={alert.get('location') or 'unknown'}; "
                    f"description={alert.get('description') or ''}"
                )

        stats = result.get("stats")
        if stats:
            lines.append(f"Stats: {json.dumps(stats, sort_keys=True)}")

        return "\n".join(lines).strip()

    def _ask_ollama(self, question: str, rule_answer: str, evidence: str) -> str:
        prompt = f"""You are a local drone security analyst assistant.
Answer the user's question using only the evidence below.
Do not invent people, vehicles, times, locations, or alerts.
Preserve all counts and facts from the deterministic answer exactly.
Do not infer closed alerts, resolved alerts, or missing records unless they are explicitly in the evidence.
Add at most one concise sentence.
If the evidence is insufficient, say what is missing.

User question: {question}
Deterministic answer: {rule_answer}

Evidence:
{evidence}

Analyst answer:"""
        payload = json.dumps({
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.ollama_temperature, "num_predict": 80},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.ollama_timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
        return str(data.get("response", "")).strip()

    def _clean_llm_answer(self, answer: str, rule_answer: str) -> str:
        blocked_markers = ("Frames:", "Alerts:", "Stats:", "time=", "objects=", "description=", "summary=", "caption=")
        if any(marker in answer for marker in blocked_markers):
            return ""

        answer = " ".join(line.strip() for line in answer.splitlines() if line.strip())
        answer = answer.strip(" -")
        if not answer:
            return ""

        if answer.lower().startswith(rule_answer.lower()):
            answer = answer[len(rule_answer):].strip(" .")
        if not answer:
            return ""

        return answer[:400]

    def _decode_json(self, raw: Any, default: Any) -> Any:
        if raw is None:
            return default
        if not isinstance(raw, str):
            return raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default
