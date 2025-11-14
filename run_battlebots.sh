#!/bin/bash

# --- Script for macOS/Linux (Python) ---

# Set the path to your Python script
PYTHON_SCRIPT="./battlebots.py"

echo "Starting BattleBots Python Simulation..."

# Execute the script using the python interpreter
# The 'exec' command replaces the shell with the program.
exec python3 $PYTHON_SCRIPT "$@"
