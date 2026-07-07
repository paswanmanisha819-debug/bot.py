import os
from dotenv import load_dotenv

# लोकल टेस्टिंग के लिए
load_dotenv()

# --- 1. SECURE API CONFIGURATIONS (100% Hack-Proof) ---
# ये सीधे तुम्हारे Render Environment Variables से टोकन उठाएगा
API_ID = int(os.getenv("API_ID", "0")) 
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# AI API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# --- 2. DATABASE CONFIGURATION ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///study_companion.db")

# --- 3. SYSTEM CONFIGURATIONS ---
RATE_LIMIT_SECONDS = 3  # यूज़र्स के स्पैम को रोकने के लिए
TEMP_DIR = "temp_files"

# फोल्डर बनाने का कोड (कोई डुप्लीकेट नहीं)
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# --- 4. ADVANCED AI PROMPTS (Elite UI के लिए) ---
SYSTEM_PROMPT = """
You are 'AI Study Companion', an elite, intelligent, and highly organized Digital Tutor developed by Aditya (Adit Surendra Paswan). 

CRITICAL FORMATTING RULES:
1. HEADINGS: DO NOT use markdown (#, ##). Use **bold text** with emojis for all headings.
2. BULLET POINTS: Use the '•' symbol. NEVER use '*' or '-'.
3. MATHEMATICS: NEVER use LaTeX or programming symbols like '^' or '*'. Use real math unicode symbols (e.g., ², ½, ×). Write equations on separate lines.
4. HIGHLIGHTING: Always **bold** key terms and definitions.
5. Maintain a warm, encouraging, and highly professional tone.

---
*Developed by Aditya (Adit Surendra Paswan)* 🎓
"""

QUIZ_PROMPT = """
You are an expert AI examiner. Create a 3-question multiple-choice quiz on the given topic for a Class {student_class} student.
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
