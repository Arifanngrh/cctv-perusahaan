@echo off
echo Starting AI CCTV System...

start cmd /k "cd backend && python -m uvicorn api:app --reload"
timeout /t 3
start cmd /k "cd ai_engine && python detect.py"
timeout /t 5
start cmd /k "cd frontend && npm start"

echo System started.
