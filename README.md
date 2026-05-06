# Drone Security Analyst Agent

A laptop-runnable prototype for a docked drone that monitors a fixed property, processes simulated video frames and telemetry, indexes every frame, and raises real-time security alerts.

## Assignment Fit

- Simulated telemetry and video frames: `main.py` generates timestamped frame descriptions and drone telemetry.
- Object and event analysis: `src/detector.py` detects people, vehicles, colors, and simple counts from text descriptions, with optional YOLOv8 support for real images.
- Real-time alerts: `src/engine.py` generates loitering, intrusion, repeated vehicle, restricted-zone, and crowd alerts.
- Frame-by-frame indexing: `src/database.py` stores frames and alerts in SQLite with FTS5 search.
- Querying and follow-up questions: `src/agent.py` answers questions from indexed frames and alerts.
- Web dashboard: `app/main_api.py` and `app/templates/dashboard_pro.html` expose stats, alerts, frames, search, and agent Q&A.
- QA: `tests/test_smoke.py` validates detection, alerting, time indexing, object querying, and agent answers.

## Requirement Coverage

| Assignment requirement | Project evidence | Status |
| --- | --- | --- |
| Short feature spec with value and key requirements | `docs/FEATURE_SPEC.md` | Complete |
| Architecture for telemetry/video processing, storage, and alerts | `docs/ARCHITECTURE.md` Mermaid pipeline and component notes | Complete |
| Prototype implementation | `main.py`, `src/`, `app/main_api.py` | Complete |
| Simulated video frames and telemetry | `main.py::demo_frames` and `src.models.Telemetry` | Complete |
| Object/event analysis | `src/detector.py`, optional YOLOv8 path | Complete |
| Real-time predefined alert rules | `src/engine.py` | Complete |
| Frame-by-frame indexing | `src/database.py` SQLite tables, indexes, and FTS5 | Complete |
| Query by object/time/search | `SecurityDatabase` query methods and `/api/search` | Complete |
| Follow-up Q&A bonus | `src/agent.py` and `/api/agent/ask` | Complete |
| Video summary bonus | `VLMCaptionGenerator.generate_daily_summary` and `/api/summary` | Complete |
| Tests for detection, alerting, indexing, and agent answers | `tests/test_smoke.py` | Complete |
| AI tool usage documentation | README plus `docs/REPORT_DRAFT.md` | Complete |

## Design Decisions

- The default path uses deterministic text-simulated frames so evaluators can run the full prototype offline without drone hardware, camera feeds, or cloud credentials.
- SQLite was chosen for local frame-by-frame indexing because it is lightweight, persistent, and supports FTS5 full-text search.
- Alert rules are explicit Python logic instead of opaque model calls, making every safety/security alert explainable and testable.
- YOLOv8, API-backed captioning, and local Ollama-backed agent answers are optional upgrade paths; the project still runs with rule-based captions and Q&A when no model service is available.
- The query agent is database-backed first, then optionally uses Ollama to produce a clearer natural-language analyst answer from the retrieved frame and alert evidence.

## Setup

Use Python 3.10+.

```powershell
cd D:\AIML_73\drone_security_project
C:\Users\jayka\AppData\Local\Programs\Python\Python310\python.exe -m pip install -r requirements.txt
```

Your local `.venv` currently points to a broken Python path, so use the full Python path above unless you recreate the venv.

## Run Demo

```powershell
C:\Users\jayka\AppData\Local\Programs\Python\Python310\python.exe main.py
```

The demo prints frame logs, generated captions, alerts, database stats, search examples, and agent Q&A examples. It also writes:

```text
data/demo_output.json
data/security.db
```

## Run Web Dashboard

```powershell
C:\Users\jayka\AppData\Local\Programs\Python\Python310\python.exe -m uvicorn app.main_api:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Useful API endpoints:

- `/api/stats`
- `/api/alerts`
- `/api/frames`
- `/api/frames/object/truck`
- `/api/search?q=gate`
- `/api/agent/ask?q=show%20all%20truck%20events`
- `/api/summary`

## Optional Local LLM Agent With Ollama

The agent can use a free local Ollama model for better Q&A answers. It still queries SQLite first, so the LLM only summarizes real frame and alert evidence.

Recommended laptop model:

```powershell
ollama pull llama3.2:3b
```

Optional settings:

```powershell
$env:OLLAMA_AGENT_ENABLED="1"
$env:OLLAMA_MODEL="llama3.2:3b"
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
$env:OLLAMA_TIMEOUT_SECONDS="60"
```

If Ollama is not installed, not running, or the model is missing, `/api/agent/ask` automatically falls back to the deterministic rule-based answer.

## Run Tests

```powershell
C:\Users\jayka\AppData\Local\Programs\Python\Python310\python.exe -m pytest -q
```

## Design Artifacts

- [Feature Spec](docs/FEATURE_SPEC.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Testing Notes](docs/TESTING.md)
- [Report Draft](docs/REPORT_DRAFT.md)

## AI Tools Used

AI assistance was used for requirement analysis, architecture refinement, bug fixing, alert rule design, test case generation, and documentation drafting. The AI-generated ideas were adapted into explicit Python modules and verified with automated tests plus live FastAPI endpoint checks.

## Submission Checklist

Before sending the assignment, complete these external deliverables:

- Push this folder to a private GitHub repository.
- Add `assignments@flytbase.com` as a repository contributor.
- Export `docs/REPORT_DRAFT.md` as a PDF report and include links/references to the demo video.
- Record a voiceover demo showing the terminal demo, dashboard/API, frame indexing/search, agent Q&A, alerts, and summary output.
- Make sure any shared video/report links have view access enabled.

## Optional Real YOLO Support

The project includes `ultralytics` and a local `yolov8n.pt`. If an image is provided to `DetectionPipeline.process_frame(..., image=...)`, the pipeline attempts YOLOv8 inference. Without images, it uses the deterministic simulator so the assignment can run offline.

## Production Notes

For a production version, add OpenCV video ingestion, edge GPU inference, vector search with CLIP embeddings, notification integrations, Docker packaging, and site-specific detector fine-tuning.
