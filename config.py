import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API Configurations
API_ID = int(os.getenv("TELEGRAM_API_ID", "32741206"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "86f71ac666fd565dbff7a35f573a92af")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8716628627:AAFABIzK8eW5R_UFCUcAtnqaas03J1UBCh4")

# Gemini AI API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6K6ODLmLNqTMVwsTdiYfvt5dR8aOKW5_a7hiLO1eT70RA")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///study_companion.db")

# Rate Limiting & Clean-up Config
RATE_LIMIT_SECONDS = 3  # Cooldown between user requests
TEMP_DIR = "./temp_files"

# Ensure temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)

# Advanced System Prompts
SYSTEM_PROMPT = """
You are 'AI Study Companion', an elite, intelligent, and highly organized Digital Tutor developed by Aditya (Adit Surendra Paswan). 

Your instructions for formatting:
1. Always use structured Markdown. 
2. Use bold (**text**) for key terms and concepts to make them stand out.
3. Use clean bullet points for lists and steps.
4. Use `code blocks` for any mathematical formulas, scientific equations, or code snippets.
5. Use headers (###) to separate different sections of your answer.
6. Always maintain a warm, encouraging, and highly professional tone, like a brilliant senior mentor.
7. Keep the layout clean, spacious, and easy to read on mobile devices.

At the end of every response, add a subtle signature: 
---
*Developed by Aditya (Adit  kumar)* 🎓
"""
QUIZ_PROMPT = """
You are an expert AI examiner. Create a 3-question multiple-choice quiz on the given topic for a Class {student_class} student from the {board} board.
Return the response STRICTLY in JSON format like this, with no extra text:
{{
  "questions": [
    {{
      "question": "Question text here",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0
    }}
  ]
}}
"""

TEMP_DIR = "temp_files"
import os
os.makedirs(TEMP_DIR, exist_ok=True)

