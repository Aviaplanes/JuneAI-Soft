@echo off
title June Soft v3.1.0-beta
echo Starting...
cd src
set PYTHONDONTWRITEBYTECODE=1
..\venv\Scripts\python.exe main.py
pause
