@echo off
cd /d "%~dp0"
REM --server.address localhost : 내 PC에서만 접속 가능(같은 WiFi의 외부 기기 노출 차단)
".venv\Scripts\python.exe" -m streamlit run app.py --server.address localhost
pause
