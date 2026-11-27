@echo off
cd /d "%~dp0"
if "%1"=="" (
  echo Usage: RUN_CAPTURE.bat ^<week^>   e.g. RUN_CAPTURE.bat 13
  exit /b 1
)
py -m analysis.capture_week --week %1
pause
