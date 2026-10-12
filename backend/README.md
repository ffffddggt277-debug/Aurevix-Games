---
title: Aurevix Games API
emoji: 🌌
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: 6.30.0
app_file: app.py
python_version: 3.12
pinned: false
---
# Aurevix Games API
FastAPI REST API with a mounted Gradio Blank-compatible status panel at `/gradio`.
`app.py` runs Uvicorn on port 7860. CPU only: OpenRouter is remote and no local task requires GPU.
Before startup run `alembic upgrade head`. Production needs persistent storage; see the root deployment guide.
