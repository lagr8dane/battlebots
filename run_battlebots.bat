@echo off
REM --- Script for Windows (Python) ---

REM Set the title for the command prompt window
title BattleBots Python Runner

REM Set the path to your Python script (adjust 'battlebots.py' if your file is named differently)
SET PYTHON_SCRIPT=.\battlebots.py

echo Starting BattleBots Python Simulation...

REM Execute the script using the Python interpreter.
REM %* passes any command line arguments given to the batch file to the script.
python %PYTHON_SCRIPT% %*

REM The 'pause' command keeps the command window open after the script finishes
REM This lets users see any output or error messages.
pause
