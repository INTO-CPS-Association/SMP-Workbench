@echo off
start "Backend" cmd /k "python -m backend.main"
start "Frontend" cmd /k "cd frontend && npm run dev"
