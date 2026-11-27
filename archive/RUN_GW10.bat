@echo off
cd /d "%~dp0"
py -m analysis.predict_next_week --week 10 --live
pause
