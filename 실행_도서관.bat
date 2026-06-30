@echo off
cd /d "%~dp0"
REM Run library competition dashboard (separate app; shares helpers engine)
REM --server.address localhost : local PC only
".venv\Scripts\python.exe" -m streamlit run library_app\app.py --server.address localhost
pause

