import asyncio
import os
import json
import base64
import random
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from groq import Groq

# Custom File Imports
from config import API_ID, API_HASH, BOT_TOKEN, GEMINI_API_KEY, SYSTEM_PROMPT, QUIZ_PROMPT, TEMP_DIR
import database as db
from utils import generate_study_notes_pdf, safe_cleanup
from features import get_ai_generated_quiz_from_image, get_ai_generated_quiz

# --- INIT ---
app = Client("study_companion_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

user_profiles = {}

# --- 1. SMART START & CLASS SETUP (Strict English) ---
@app.on_message(filters.command(["start", "setup"]))
async def setup_profile(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 9th Grade", callback_data="setclass_9"), InlineKeyboardButton("🎓 10th Grade", callback_data="setclass_10")],
        [InlineKeyboardButton("🎓 11th Grade", callback_data="setclass_11"), InlineKeyboardButton("🎓 12th Grade", callback_data="setclass_12")]
    ])
    welcome_text = (
        "🤖 **Welcome to the Elite AI Study Companion!**\n\n"
        "To provide you with highly accurate and personalized answers, "
        "please select your current academic grade below:"
    )
    await message.reply_text(welcome_text, reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"^setclass_"))
async def select_sub(client, cb):
    grade = cb.data.split("_")[1]
    subs = {
        "9": ["Science", "Mathematics", "English"], 
        "10": ["Science", "Mathematics", "Social Science"], 
        "11": ["Physics", "Chemistry", "Biology", "Mathematics"], 
        "12": ["Physics", "Chemistry", "Biology", "Mathematics"]
    }
    buttons = []
    row = []
    for s in subs.get(grade, []):
        row.append(InlineKeyboardButton(f"📚 {s}", callback_data=f"setsub_{grade}_{s}"))
        if len(row) == 2:
            buttons.append(row); row = []
    if row: buttons.append(row)
    await cb.message.edit_text(f"📘 **Grade {grade} Selected.**\nNow, please select your target subject:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^setsub_"))
async def save_profile(client, cb):
    d = cb.data.split("_")
    user_profiles[cb.from_user.id] = {"class": d[1], "subject": d[2]}
    await db.create_or_update_user(cb.from_user.id, cb.from_user.username, student_class=d[1])
    
    success_msg = (
        f"✅ **Configuration Complete!**\n━━━━━━━━━━━━━━━━━━━━\n"
        f"🎓 **Grade:** {d[1]}th\n"
        f"📚 **Subject:** {d[2]}\n━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *You are all set! Type any doubt, send a photo of a diagram, or record a voice note to get started.*"
    )
    await cb.message.edit_text(success_msg)

# --- 2. ADVANCED TEXT SOLVER (ChatGPT Premium UI & Math) ---
@app.on_message(filters.text & ~filters.command(["start", "setup", "quiz", "owner", "space"]))
async def smart_solver(client, message):
    uid = message.from_user.id
    if uid not in user_profiles: 
        return await message.reply("⚠️ **Please use the `/setup` command first to select your grade and subject.**")
    
    u = user_profiles[uid]
    processing_msg = await message.reply("🔍 *Analyzing your query like a Pro...* ⏳")
    
    try:
        # 🌟 ELITE CHATGPT-STYLE & MATH-PERFECT SYSTEM PROMPT 🌟
        sys_prompt = (
            f"You are an Elite AI Study Companion developed by Aditya. "
            f"Provide a highly accurate, outstanding answer for a {u['class']}th grade {u['subject']} CBSE student. "
            f"CRITICAL FORMATTING RULES TO MIMIC CHATGPT UI: "
            f"1. DO NOT use markdown headers (#, ##, ###). Use **bold text** with emojis for headings. "
            f"2. BULLET POINTS: Use standard bullets '•' or '✅', NEVER use '*'. "
            f"3. HIGHLIGHTING: **bold** the most important keywords and definitions. "
            f"4. MATHEMATICS & FORMULAS (STRICT): NEVER use programming symbols like '^' or '*' or '(1/2)'. "
            f"You MUST use proper Unicode math characters. Use '²' or '³' for powers (e.g., m/s², at²). "
            f"Use '½' or '¼' for fractions. Use '×' for multiplication (not '*'). "
            f"Write equations on separate lines so they look like a real math textbook. "
            f"5. SPACING: Add a clear blank line between every paragraph and section. "
            f"6. CONCLUSION: Always end with a beautifully formatted '**💡 Quick Summary:**' section."
        )
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": message.text}],
            model="llama-3.3-70b-versatile"
        )
        
        answer = chat_completion.choices[0].message.content.replace("### ", "").replace("## ", "").replace("# ", "")
        
        await db.log_conversation(uid, "user", message.text)
        await db.log_conversation(uid, "model", answer)

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download Notes as PDF", callback_data=f"gen_pdf_{message.id}")]])
        
        # 📸 यहाँ है तुम्हारा इंस्टा लिंक
        final_reply = (
            f"📖 **Detailed Explanation ({u['subject']})**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{answer}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 *Engineered by Aditya*\n"
            f"📸 [Follow me on Instagram](https://www.instagram.com/aadit_paswan.007)"
        )
        await processing_msg.edit_text(final_reply, reply_markup=keyboard, disable_web_page_preview=True)
    except Exception as e:
        await processing_msg.edit_text(f"⚠️ *System Error:* `{str(e)}`")
        

# --- 3. PDF GENERATION (Unchanged & Safe) ---
@app.on_callback_query(filters.regex(r"^gen_pdf_"))
async def handle_pdf_generation(client, cb):
    await cb.answer("Compiling Document... Please wait.")
    text_content = cb.message.text
    topic_header = text_content[:30] + "..." if len(text_content) > 30 else text_content
    pdf_path = None
    try:
        pdf_path = await asyncio.to_thread(generate_study_notes_pdf, cb.from_user.id, topic_header, text_content)
        await app.send_document(chat_id=cb.message.chat.id, document=pdf_path, caption="📚 **Your High-Quality PDF Notes are ready!**")
    except Exception as e:
        await app.send_message(cb.message.chat.id, f"❌ PDF Engine Error: {e}")
    finally:
        if pdf_path: safe_cleanup(pdf_path)

# --- 4. ADVANCED VISION HANDLER ---
@app.on_message(filters.photo)
async def vision_handler(client, message):
    msg = await message.reply_text("👁️ *Processing image through Vision AI...* ⏳")
    image_path = None
    try:
        image_path = await message.download()
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        user_q = message.caption if message.caption else "Analyze this educational image and explain its core concepts in detail."
        ai_prompt = (
            f"Respond STRICTLY in English. Provide a highly structured explanation. "
            f"Do NOT use markdown headers like #. Use **bold text** for headings and use bullet points. "
            f"Question: {user_q}"
        )

        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": ai_prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model="meta-llama/llama-4-scout-17b-16e-instruct"
        )
        answer = chat_completion.choices[0].message.content.replace("### ", "🔹 ").replace("## ", "🔸 ")
        
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🧠 Generate Quick Quiz from Image", callback_data=f"imgquiz_{message.id}")]])
        await msg.edit_text(f"🖼️ **Visual Analysis Report**\n━━━━━━━━━━━━━━━━━━━━\n{answer}\n━━━━━━━━━━━━━━━━━━━━\n👨‍💻 *Engineered by Aditya*", reply_markup=keyboard)
    except Exception as e:
        await msg.edit_text(f"⚠️ *Vision Error:* `{str(e)}`")
    finally:
        if image_path and os.path.exists(image_path): os.remove(image_path)

# --- 4. ADVANCED VISION HANDLER (With Insta Link) ---
@app.on_message(filters.photo)
async def vision_handler(client, message):
    msg = await message.reply_text("👁️ *Processing image through Vision AI...* ⏳")
    image_path = None
    try:
        image_path = await message.download()
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        user_q = message.caption if message.caption else "Analyze this educational image and explain its core concepts in detail."
        ai_prompt = (
            f"Respond STRICTLY in English. Provide a highly structured explanation. "
            f"Do NOT use markdown headers like #. Use **bold text** for headings and use bullet points. "
            f"Question: {user_q}"
        )

        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": ai_prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model="meta-llama/llama-4-scout-17b-16e-instruct"
        )
        answer = chat_completion.choices[0].message.content.replace("### ", "🔹 ").replace("## ", "🔸 ")
        
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🧠 Generate Quick Quiz from Image", callback_data=f"imgquiz_{message.id}")]])
        
        # 📸 यहाँ भी लगा दिया तुम्हारा इंस्टा लिंक
        final_reply = (
            f"🖼️ **Visual Analysis Report**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{answer}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 *Engineered by Aditya*\n"
            f"📸 [Follow me on Instagram](https://www.instagram.com/aadit_paswan.007)"
        )
        await msg.edit_text(final_reply, reply_markup=keyboard, disable_web_page_preview=True)
    except Exception as e:
        await msg.edit_text(f"⚠️ *Vision Error:* `{str(e)}`")
    finally:
        if image_path and os.path.exists(image_path): os.remove(image_path)
        

# --- 7. BASIC COMMANDS ---
@app.on_message(filters.command("owner"))
async def owner_info(client, message):
    owner_text = "👤 **Developer Profile**\n━━━━━━━━━━━━━━━━━━━━\n🎓 **Name:** Aditya\n💻 **Role:** Lead Software Developer & AI Engineer\n🚀 **System:** Elite AI Study Companion"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📱 Follow Developer on Instagram", url="https://www.instagram.com/aadit_paswan.007")]])
    await message.reply_text(owner_text, reply_markup=keyboard)

@app.on_message(filters.command("space"))
async def space_handler(client, message):
    facts = ["Did you know? A day on Venus is longer than a year on Venus! 🪐", "Space is completely silent. 🌌", "There are more stars in the universe than grains of sand on all Earth's beaches. ✨"]
    await message.reply_text(random.choice(facts))

# --- MAIN RUNNER ---
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.init_db())
    print("🚀 Aditya's Elite AI Study Companion is LIVE on Secure Servers!")
    app.run()
        
