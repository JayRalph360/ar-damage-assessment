@echo off
REM If Windows "Smart App Control" blocks this file, do not disable it.
REM Run the commands manually instead - see README.md, section 1.
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
  .venv\Scripts\python -m pip install -r backend\requirements.txt
)
.venv\Scripts\python run.py %*
pause
