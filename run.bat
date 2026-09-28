@echo off
REM One-click start on Windows: creates a virtual env the first time, then runs the API.
cd /d "%~dp0"
if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
echo.
echo  API running at http://127.0.0.1:8000   (docs: http://127.0.0.1:8000/docs)
echo.
python -m uvicorn app.main:app --reload --port 8000
