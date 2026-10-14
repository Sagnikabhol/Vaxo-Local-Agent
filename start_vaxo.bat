@echo off
echo ==========================================
echo   Vaxo — Local Voice AI Desktop Assistant
echo ==========================================
echo.

:: Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated.
) else (
    echo [!] Virtual environment not found.
    echo     Run: python -m venv venv
    echo     Then: venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Launch Vaxo using python module execution
python -m streamlit run app.py --server.port 8501 --server.headless false --theme.base dark

pause
