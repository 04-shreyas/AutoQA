@echo off
REM AutoQA batch file for Windows

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="install" goto install
if "%1"=="run" goto run
if "%1"=="dashboard" goto dashboard
if "%1"=="test" goto test
if "%1"=="clean" goto clean
goto help

:help
echo Available commands:
echo.
echo   autoqa.bat install    - Install dependencies
echo   autoqa.bat run        - Run the main AutoQA application
echo   autoqa.bat dashboard  - Start the Streamlit dashboard
echo   autoqa.bat test       - Run all tests
echo   autoqa.bat clean      - Clean up generated files
goto end

:install
echo Installing dependencies...
pip install -r requirements.txt
goto end

:run
echo Running AutoQA...
python -m src.autoqa.cli
goto end

:dashboard
echo Starting dashboard...
streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0
goto end

:test
echo Running tests...
python -m pytest tests/ -v --tb=short
goto end

:clean
echo Cleaning up...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (.pytest_cache) do @if exist "%%d" rd /s /q "%%d"
del /s /q data\*.json 2>nul
del /s /q reports\*.md 2>nul
del /s /q logs\*.log 2>nul
echo Cleanup complete
goto end

:end