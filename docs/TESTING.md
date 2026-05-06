# Testing

Run tests:

```powershell
C:\Users\jayka\AppData\Local\Programs\Python\Python310\python.exe -m pytest -q
```

## Covered Scenarios

- Truck logging: a simulated "Blue Ford F150 at garage" frame is detected as a blue truck and can be queried from the frame index.
- Midnight loitering: a person staying at the main gate for more than 30 seconds around midnight triggers a loitering alert.
- Time indexing: frames can be retrieved by timestamp range.
- Query agent: a natural-language object question returns matching indexed frames.
- Crowd detection: a simulated "Three people..." frame creates three person detections and triggers a crowd alert.
- Repeated vehicle: a returning blue Ford F150 at the garage triggers a repeated-vehicle alert.

## Manual API Checks

Start the app:

```powershell
C:\Users\jayka\AppData\Local\Programs\Python\Python310\python.exe -m uvicorn app.main_api:app --reload
```

Then check:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/api/stats`
- `http://127.0.0.1:8000/api/alerts`
- `http://127.0.0.1:8000/api/frames`
- `http://127.0.0.1:8000/api/search?q=truck`
- `http://127.0.0.1:8000/api/agent/ask?q=show%20all%20truck%20events`
