# 🛡️ Drone Security Analyst — Intelligent Autonomous Surveillance System

> **Enterprise-grade AI security platform** built as a fully functional prototype for autonomous drone-based property monitoring — featuring real-time threat detection, frame-by-frame intelligence indexing, natural language Q&A, and a live operational dashboard.

---

## 🎯 Project Overview

This system demonstrates a **production-architected, AI-powered drone security platform** capable of autonomously monitoring a fixed property, analyzing video intelligence frame-by-frame, and surfacing actionable security alerts in real time — all runnable on a standard laptop without drone hardware or cloud dependencies.

The project was designed to reflect real-world enterprise constraints: **explainable alert logic**, **offline-first architecture**, **modular AI upgrade paths**, and **end-to-end test coverage**.

---

## ✨ Key Capabilities

| Capability | Implementation | Highlights |
|---|---|---|
| 🎥 **Video Intelligence** | `main.py` + `src/detector.py` | Timestamped frame simulation with deterministic object/event extraction |
| 🚨 **Real-Time Alerting** | `src/engine.py` | Rule-based: loitering, intrusion, crowd surges, restricted zones, repeat vehicles |
| 🗄️ **Frame Indexing** | `src/database.py` | SQLite + FTS5 full-text search — every frame and alert is queryable by object, time, or keyword |
| 🤖 **AI Q&A Agent** | `src/agent.py` | Database-first retrieval + optional Ollama LLM for natural-language analyst answers |
| 📊 **Live Dashboard** | `app/main_api.py` + `dashboard_pro.html` | FastAPI-powered REST endpoints + browser-based operational UI |
| 📝 **Daily Summaries** | `VLMCaptionGenerator` | Automated end-of-day video intelligence summaries via `/api/summary` |
| 🔍 **Optional YOLO** | `DetectionPipeline` | Drop-in YOLOv8 inference on real images — no code changes required |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      DRONE SECURITY PLATFORM                    │
├──────────────┬──────────────────────────┬───────────────────────┤
│  Ingestion   │      Analysis Core       │   Intelligence Layer  │
│              │                          │                        │
│  Telemetry   │  detector.py             │  engine.py            │
│  Simulator   │  ├─ Text-based sim       │  ├─ Loitering rules   │
│  +           │  ├─ YOLOv8 (optional)    │  ├─ Intrusion rules   │
│  Frame       │  └─ Object/event parser  │  ├─ Vehicle tracking  │
│  Generator   │                          │  └─ Crowd detection   │
├──────────────┴──────────────────────────┴───────────────────────┤
│                       Data & Query Layer                        │
│  SQLite (database.py)  ·  FTS5 Full-Text Search  ·  REST API   │
├─────────────────────────────────────────────────────────────────┤
│              Agent Q&A  ·  Ollama LLM (optional)               │
│              Dashboard  ·  FastAPI  ·  HTML UI                  │
└─────────────────────────────────────────────────────────────────┘
```

> Full Mermaid pipeline and component documentation: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## 📋 Requirement Coverage

| Assignment Requirement | Deliverable | Status |
|---|---|---|
| Feature spec with value proposition and key requirements | `docs/FEATURE_SPEC.md` | ✅ Complete |
| Architecture for telemetry, video processing, storage, and alerting | `docs/ARCHITECTURE.md` with Mermaid diagram | ✅ Complete |
| Prototype implementation | `main.py`, `src/`, `app/main_api.py` | ✅ Complete |
| Simulated video frames and telemetry | `main.py::demo_frames`, `src.models.Telemetry` | ✅ Complete |
| Object and event analysis | `src/detector.py`, optional YOLOv8 path | ✅ Complete |
| Real-time predefined alert rules | `src/engine.py` | ✅ Complete |
| Frame-by-frame indexing | SQLite tables, indexes, FTS5 in `src/database.py` | ✅ Complete |
| Query by object / time / keyword | `SecurityDatabase` methods + `/api/search` | ✅ Complete |
| Follow-up Q&A *(Bonus)* | `src/agent.py` + `/api/agent/ask` | ✅ Complete |
| Video summary *(Bonus)* | `VLMCaptionGenerator.generate_daily_summary` + `/api/summary` | ✅ Complete |
| Test coverage | `tests/test_smoke.py` — detection, alerting, indexing, agent answers | ✅ Complete |
| AI tool usage documentation | `README.md` + `docs/REPORT_DRAFT.md` | ✅ Complete |

---

## 🔬 Design Decisions & Engineering Rationale

### 1. Offline-First by Default
The default execution path uses **deterministic text-simulated frames** — evaluators and reviewers can run the complete prototype without drone hardware, camera feeds, or cloud credentials. The system degrades gracefully at every layer.

### 2. SQLite + FTS5 for Frame Intelligence
SQLite was chosen for persistent, lightweight, local frame indexing with **FTS5 full-text search** built in. Every captured frame and alert is immediately queryable by object type, timestamp range, or natural-language keyword — no external database setup required.

### 3. Explainable Alert Rules
Security alerts are implemented as **explicit Python logic** in `engine.py`, not opaque model calls. Every loitering, intrusion, crowd, or restricted-zone alert can be traced to a specific rule — making the system auditable, testable, and production-safe.

### 4. Modular AI Upgrade Paths
The architecture separates deterministic logic from AI inference, enabling clean upgrades:
- **YOLOv8** inference activates automatically when a real image is supplied
- **Ollama LLM** enhances agent Q&A when the service is available, with automatic rule-based fallback
- No code modifications required to switch between modes

---

## ⚙️ Setup

**Requirements:** Python 3.10+

```powershell
cd D:\AIML_73\drone_security_project
C:\Users\jayka\AppData\Local\Programs\Python\Python310\python.exe -m pip install -r requirements.txt
```

> **Note:** Use the full Python path above if your local `.venv` points to a broken interpreter path.

---

## 🚀 Running the System

### Terminal Demo
```powershell
C:\Users\jayka\AppData\Local\Programs\Python\Python310\python.exe main.py
```
Outputs: frame logs → captions → alerts → DB stats → search examples → agent Q&A  
Writes: `data/demo_output.json` · `data/security.db`

---

### Web Dashboard
```powershell
C:\Users\jayka\AppData\Local\Programs\Python\Python310\python.exe -m uvicorn app.main_api:app --reload
```
Open: **http://127.0.0.1:8000**

| Endpoint | Description |
|---|---|
| `/api/stats` | System-wide frame and alert statistics |
| `/api/alerts` | All active security alerts |
| `/api/frames` | Complete frame index |
| `/api/frames/object/truck` | Frames filtered by detected object |
| `/api/search?q=gate` | Full-text keyword search across all frames |
| `/api/agent/ask?q=show%20all%20truck%20events` | Natural language Q&A against indexed data |
| `/api/summary` | AI-generated daily intelligence summary |

---

### Test Suite
```powershell
C:\Users\jayka\AppData\Local\Programs\Python\Python310\python.exe -m pytest -q
```
Tests cover: detection accuracy · alert rule logic · time-range indexing · object queries · agent answer quality

---

## 🤖 Optional: Local LLM Agent (Ollama)

The Q&A agent queries SQLite first, then optionally routes to a local Ollama model for richer natural-language answers — ensuring responses are always grounded in real frame evidence, never hallucinated.

```powershell
# Pull recommended laptop-optimized model
ollama pull llama3.2:3b

# Enable Ollama agent
$env:OLLAMA_AGENT_ENABLED="1"
$env:OLLAMA_MODEL="llama3.2:3b"
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
$env:OLLAMA_TIMEOUT_SECONDS="60"
```

If Ollama is not running, `/api/agent/ask` automatically falls back to the deterministic rule-based answer with zero configuration changes.

---

## 🧪 Optional: Real YOLO Inference

The `DetectionPipeline` includes a drop-in YOLOv8 path:

```python
# Activates automatically when an image is provided
DetectionPipeline.process_frame(frame_data, image=<your_image>)
```

Without images, the pipeline uses the deterministic text simulator — enabling fully offline evaluation.

---

## 📄 Design Artifacts

| Document | Contents |
|---|---|
| [`docs/FEATURE_SPEC.md`](docs/FEATURE_SPEC.md) | Value proposition, user stories, and functional requirements |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Mermaid pipeline diagram, component breakdown, data flow |
| [`docs/TESTING.md`](docs/TESTING.md) | Test strategy, coverage scope, and edge case notes |
| [`docs/REPORT_DRAFT.md`](docs/REPORT_DRAFT.md) | AI tool usage log, design rationale, lessons learned |

---

## 🛣️ Production Roadmap

The current prototype is architected to support production upgrades without structural changes:

- **Video Ingestion** — OpenCV camera feed integration
- **Edge Inference** — GPU-accelerated YOLOv8 on embedded hardware
- **Vector Search** — CLIP embeddings for semantic frame retrieval
- **Notifications** — Webhook / SMS / email alert dispatch
- **Containerisation** — Docker + Compose packaging for deployment
- **Fine-Tuning** — Site-specific detector training for custom threat profiles

---

## 🤝 AI Tool Disclosure

AI assistance was used during: requirement analysis, architecture refinement, alert rule design, bug resolution, test case generation, and documentation drafting. All AI-generated ideas were translated into explicit, testable Python modules and verified through automated testing and live FastAPI endpoint validation.

-
---

<div align="center">

**Built with precision. Designed for production. Ready for evaluation.**

</div>
