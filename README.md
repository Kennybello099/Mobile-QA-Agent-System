# Agentic Mobile QA System

## 📘 Overview
🚀 **Mobile QA Agentic System**  
This project implements a next-generation **mobile Question Answering (QA) agentic pipeline** powered by **Gemini free-tier models** (`gemini-pro-latest` for text and vision).  
It integrates **LLM APIs** with **Python workflows** for robust, quota-aware question answering, including **mobile automation via ADB**.


## 🎯 Objective
The primary objective of this project is to:

- **Research different agentic frameworks**  
- **Design and implement a multi-agent system**  
- Apply the system to **mobile QA automation**, enabling real-time analysis and interaction with mobile environments

## ✨ Key Features
- Automated model selection with quota-aware fallbacks  
- Modular architecture for reproducibility and scalability  
- Secure API integration with environment variable management  
- Mobile automation using ADB for emulator/device interaction  
- Transparency and fairness in QA outputs

  
## 📂 Project Structure
- `main.py` — Entry point for running QA queries  
- `agents.py` — Agent orchestration and model selection logic  
- `mobile_qa.py` — Android emulator QA integration  
- `mobileagent.py` — Mobile agent logic for screen capture and interaction  
- `adb_helper.py` — ADB automation utilities for emulator control  
- `gemini_helper.py` — Gemini API wrapper and quota-aware model selection  
- `requirements.txt` — Python dependencies  
- `.env` — Environment variables (e.g., Gemini API key)  
- `.gitignore` — Git exclusions  
- `current_screen.png` — Screenshot used for image-based QA  
- `__pycache__/` — Python bytecode cache  

---

## ⚙️ Setup
### Prerequisites
- Python 3.9+
- ADB installed and emulator running
- Gemini API key stored in `.env`
- [Obsidian](https://obsidian.md/) installed for managing QA logs and notes

### Installation
Install dependencies:
```bash
pip install -r requirements.txt
pip install --upgrade google-generativeai
pip install google-generativeai pillow python-dotenv
```bash
pip install -r requirements.txt
