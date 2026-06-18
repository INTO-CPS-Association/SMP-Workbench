@echo off
start "Backend" cmd /k "python -m backend.main"
start "Frontend" cmd /k "cd frontend && npm run dev"
rem For the packaged desktop development flow, run: npm run desktop:dev
