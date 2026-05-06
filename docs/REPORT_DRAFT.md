# Report Draft

## Approach

This prototype implements a Drone Security Analyst Agent for a docked drone monitoring a fixed property. It processes simulated frame descriptions and telemetry, detects objects and events, stores every frame in an indexed database, and generates security alerts in real time.

The system is intentionally runnable on a laptop. The main demo creates a short patrol sequence, processes each frame through the detection pipeline, writes frame context to SQLite, evaluates alerts immediately, and then demonstrates search plus follow-up Q&A over the indexed history.

## Assumptions

- The prototype uses text descriptions as simulated frames so it can run without drone hardware or a video dataset.
- YOLOv8 support is included as an optional path for real image inference.
- SQLite is sufficient for the assignment prototype; a production deployment could move to PostgreSQL plus a vector database.
- Rule-based captions and Q&A are used by default so the project runs offline. API-backed VLM captioning can be enabled with `ANTHROPIC_API_KEY`, and local LLM-enhanced agent answers can be enabled with Ollama.

## Tool Choices

- Python: fast to prototype and well supported by AI/CV libraries.
- Ultralytics YOLOv8: real-time object detection path for people and vehicles.
- Ollama with `llama3.2:3b`: optional free local LLM layer for clearer agent answers from SQLite evidence.
- SQLite + FTS5: local frame-by-frame indexing and full-text search.
- FastAPI: simple dashboard and JSON API.
- Pytest: automated validation of detection, alerting, indexing, and Q&A behavior.

## Architecture Summary

The prototype has five main layers:

1. Simulated inputs generate timestamped frame descriptions and telemetry.
2. The detection pipeline extracts people, vehicles, colors, counts, and frame summaries.
3. The alert engine evaluates temporal/context rules such as loitering, off-hours intrusion, repeated vehicles, restricted-zone access, and crowds.
4. SQLite stores frames, detections, telemetry, captions, and alerts with timestamp indexes plus FTS5 search.
5. The dashboard and query agent expose context retrieval, alert review, object lookup, and activity summaries.

## AI Assistance

AI assistance was used to speed up architecture planning, schema design, alert rule design, test scenario generation, and debugging. The generated suggestions were adapted into deterministic Python modules and verified with automated tests and live API checks.

Specific examples:

- Requirement decomposition into feature spec, architecture, prototype, indexing, QA, and submission artifacts.
- Alert rule brainstorming for loitering, off-hours intrusion, repeated vehicle entries, restricted zones, and crowds.
- SQLite FTS5 schema and query pattern validation for frame-by-frame indexing.
- Test scenario generation for truck logging, midnight loitering, time-range indexing, object Q&A, and crowd detection.
- Documentation drafting for README setup, design rationale, and report structure.

## Results

Sample outcomes:

- `Blue Ford F150 at garage` is logged as a blue truck event.
- A returning blue Ford F150 at the garage triggers a repeated-vehicle alert.
- A person remaining near the main gate around midnight triggers a loitering alert.
- Indexed frames can be queried by object, time range, or natural-language questions.
- The dashboard shows alert counts, recent alerts, frame map markers, search results, and agent answers.

Verification performed:

- `python -m pytest -q`: 6 tests passed.
- `python main.py`: demo completed, generated seven indexed frames, six alerts, search examples, and Q&A examples.
- `uvicorn app.main_api:app`: dashboard and API routes returned HTTP 200 for stats, alerts, frames, search, agent Q&A, and summary.

## Scalability and Reasoning

The current agent keeps context in SQLite rather than only in memory, so frame history survives between runs and can be queried by time, object, location, and text. For larger patrols, the same schema can be extended with pagination, partitioned date tables, vector embeddings, and asynchronous frame processing. The rule engine is stateful for short-term temporal patterns such as loitering and repeated vehicle activity, while the database provides long-term evidence for follow-up questions.

## Future Improvements

- Add true video ingestion with OpenCV frame sampling.
- Add CLIP embeddings and a vector database for semantic frame retrieval.
- Add notification integrations such as email, SMS, or webhook alerts.
- Fine-tune the detector on site-specific images for better vehicle and zone recognition.
- Add Docker packaging and a richer LangChain agent when cloud/API credentials are available.

## Submission Notes

The final submission should include this report exported as PDF, a private GitHub repository link with evaluator access, and a voiceover screen recording that demonstrates frame processing, generated captions/summaries, alerts, search/indexing, and agent recommendations.
