@echo off
rem Monthly refresh, for Windows Task Scheduler.
rem Runs the full refresh, keeps a dated log, and pushes the updated results to GitHub.
cd /d C:\Projects\fund-voting
call .venv\Scripts\activate.bat
if not exist cloud\logs mkdir cloud\logs
set STAMP=%DATE:~-4%-%DATE:~4,2%-%DATE:~7,2%
python cloud\refresh.py > cloud\logs\refresh_%STAMP%.txt 2>&1
if errorlevel 1 exit /b 1
git add reports cloud\refresh_log.csv cloud\publish_log.csv
git commit -m "Monthly refresh %STAMP%" >nul 2>&1
git push >nul 2>&1
