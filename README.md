# Battle of the Bots: A Local AI Debate & Model Testbed

Battle of the Bots is a local-first, offline-capable Streamlit dashboard for running structured AI debates, A/B testing models, and managing your local Ollama library. This tool was built to explore model "personalities," instruction-following, and adversarial robustness. It features a robust multi-round debate app, a side-by-side model comparator, a single-model playground, and a model-management tool.

## ⚠️ Disclaimer & The Mad Man Warning ⚠️

This project is a personal build and experimental ground. It is **not a commercial offering** and comes with absolutely **no warranty or implied liability** whatsoever. It is the brainchild of a self-proclaimed **mad man** exploring the frontiers of local AI as a sidekick. Use at your own risk, and have fun!

---

## Features
This project is a multi-page Streamlit dashboard. The sidebar will guide you through four apps:

### 1. Battle of the Bots (Debate App)
This is the core app for running structured, multi-round debates between two AI models.
* **Dynamic Model Selection:** Pit any two of your local models against each other as "PRO" and "CON."
* **Unified Persona System:** Control each debater's personality for the entire debate. The model's instructions are a combination of **Persona Text** and **4 Attitude Sliders** (Tone, Argument Style, Formality, and Reasoning Complexity).
* **"Permission to Lie" Mode:** A "Force Adversarial" checkbox that forces models to defend their side, even if it contradicts their "truth bias."
* **Live Performance Metrics:** See real-time tok/s, generation time, and token counts for every single message.
* **AI Critic & Judge:** After the debate, a third AI model reads the final arguments and provides a human-readable verdict on who won.
* **Drift & Protest Detection:** The UI automatically flags "Side Mismatches" and "Model Protests" (when a model refuses to follow its SIDE\_CONFIRM instruction).
* **Export to JSON:** Download the entire debate transcript, including all prompts, raw outputs, and metrics.

### 2. A/B Model Test (Comparator App)
A simple tool for rapid, side-by-side comparison.
* **One Prompt, Two Models:** Send a single prompt to any two of your models.
* **Persona Support:** Give each model a unique system prompt or persona.
* **AI Critic:** The critic model reads the prompt and both responses, then provides a verdict on which response was better and why.
* **Full Metrics:** See detailed performance metrics (tok/s, load time, etc.) for all three models.

### 3. Model Playground
A single-page chat interface to test any one of your local models with a custom system prompt and see its performance metrics.

### 4. Model Explorer
A dashboard for managing your Ollama models.
* **Discover & Pull:** Shows a curated list of popular models, filterable by specialty (e.g., "Coding", "Multimodal"). You can pull them directly from the UI.
* **Pull by Name:** A text box to pull any model from the official Ollama library.
* **Manage Local Models:** Displays a list of all models currently installed on your machine, with a "Delete" button for each.

---

## Project Structure
This project is organized as a Streamlit Multipage App:

battlebots/
 app/
    __init__.py
    coordinator.py      # Debate App "brain"
    comparator.py       # Comparator App "brain"
    critic.py           # Critic logic
    parsing.py          # Robust XML parser
    prompts.py          # All debate prompts
    comparator_prompts.py # Comparator prompts
    runner.py           # Runs Ollama, gets metrics
    config.py           # Default settings
    user_config.py      # Saves user's last-used models/sliders
 pages/
    1_Debate_App.py
    2_Model_Comparator.py
    3_Model_Explorer.py
    4_Model_Playground.py
 config/
    debate_defaults.json  # (This is auto-generated on first run)
 dashboard.py             # <--- The main file to run
 setup.sh                 # (For macOS/Linux)
 setup.bat                # (For Windows)
 run_dashboard.sh         # (For macOS/Linux)
 run_dashboard.bat        # (For Windows)
 requirements.txt
 README.md                # (This file)

---

## Installation & Setup
This app runs 100% locally. You will need **Python 3.9+** and **Ollama**.

* **Step 1: Install Ollama**
    If you don't have it, download and install it from [link].
* **Step 2: Get the Project Code**
    Clone this repository to your machine:
    `git clone [https://github.com/YOUR_USERNAME/battlebots.git]`
    `cd battlebots`
* **Step 3: Run the One-Time Setup**
    This script will create a virtual environment, install Python libraries, and pull the default models (`llama3:8b` and `mistral:7b`).
    * **On macOS / Linux:** `chmod +x setup.sh` and `./setup.sh`.
    * **On Windows:** Just double-click the file: `setup.bat`.

## How to Run the Dashboard
After the setup is complete, you can run the app at any time.
* **On macOS / Linux:** `./run_dashboard.sh`.
* **On Windows:** Double-click the file: `run_dashboard.bat`.
This will launch the app in your browser, typically at `http://localhost:8501`.

---

## Troubleshooting & Known Issues
* **"Model Protest" / "Side Mismatch":**
    * **Symptom:** You see a Model Protest Detected! warning in the debate.
    * **Note:** This is **not a bug, it is a feature**! This happens when you check the "Force Adversarial" box and give a model a topic it "knows" is false (e.g., "The sky is purple"). The model is so biased to be "truthful" that it is refusing to follow your `SIDE_CONFIRM` instruction. This is the core of the experiment!
* **"Schizophrenic" Custom Models:**
    * **Symptom:** A model writes two contradictory arguments in the same turn.
    * **Cause:** This happens if you use a custom model (like `mike:debater`) that was created with an old Modelfile containing its own system prompts. These old, baked-in prompts will conflict with the new 4-slider persona system.
    * **Fix:** For the cleanest results, use "base" models (like `llama3:8b`, `mistral:7b`) in the debater dropdowns. The 4-slider system is designed to add the persona to them.

