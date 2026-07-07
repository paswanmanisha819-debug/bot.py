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

# तुम्हारे कस्टम फाइल्स से इम्पॉर्ट (ये तुम्हारे पास पहले से हैं)
from config import API_ID, API_HASH, BOT_TOKEN, GEMINI_API_KEY, SYSTEM_PROMPT, QUIZ_PROMPT, TEMP_DIR
import database as db
from utils import generate_study_notes_pdf, safe_cleanup
from features import get_ai_generated_quiz_from_image, get_ai_generated_quiz

# --- INIT ---
app = Client("study_companion_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

user_profiles = {}
ACTIVE_QUIZZES = {}
USER_COOLDOWNS = {}

# --- 1. SMART START & CLASS SETUP ---
@app.on_message(filters.command(["start", "setup"]))
async def setup_profile(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("9th Class", callback_data="setclass_9"), InlineKeyboardButton("10th Class", callback_data="setclass_10")],
        [InlineKeyboardButton("11th Class", callback_data="setclass_11"), InlineKeyboardButton("12th Class", callback_data="setclass_12")]
    ])
    await message.reply_text("🎓 **Welcome to AI Study Bot!**\nसबसे पहले अपनी क्लास सिलेक्ट करो:", reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"^setclass_"))
async def select_sub(client, cb):
    grade = cb.data.split("_")[1]
    subs = {"9": ["Science", "Maths", "English"], "10": ["Science", "Maths", "SST"], "11": ["Physics", "Chemistry", "Biology", "Maths"], "12": ["Physics", "Chemistry", "Biology", "Maths"]}
    buttons = []
    row = []
    for s in subs.get(grade, []):
        row.append(InlineKeyboardButton(s, callback_data=f"setsub_{grade}_{s}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    await cb.message.edit_text(f"📚 **Class {grade}th** - अब अपना सब्जेक्ट चुनो:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^setsub_"))
async def save_profile(client, cb):
    d = cb.data.split("_")
    user_profiles[cb.from_user.id] = {"class": d[1], "subject": d[2]}
    # डेटाबेस में भी अपडेट कर दो (तुम्हारे पुराने लॉजिक के लिए)
    await db.create_or_update_user(cb.from_user.id, cb.from_user.username, student_class=d[1])
    await cb.message.edit_text(f"✅ **Setup Complete!**\n\nप्रोफ़ाइल **Class {d[1]}th - {d[2]}** सेट हो गई है।\nअब अपना कोई भी डाउट पूछो!")

# --- 2. ADVANCED TEXT SOLVER (Class-Aware) & PDF ---
@app.on_message(filters.text & ~filters.command(["start", "setup", "quiz", "owner", "space"]))
async def smart_solver(client, message):
    uid = message.from_user.id
    if uid not in user_profiles: 
        return await message.reply("⚠️ प्लीज़ पहले `/setup` दबाकर अपनी क्लास और सब्जेक्ट चुनो!")
    
    u = user_profiles[uid]
    processing_msg = await message.reply("🔍 *Thinking...* ⏳")
    
    try:
        sys_prompt = (f"You are an AI Study Companion developed by Aditya. "
                      f"Answer perfectly for a {u['class']}th grade {u['subject']} student. "
                      f"Do NOT use markdown headers like # or ###. Use bold text for headings.")
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": message.text}],
            model="llama-3.3-70b-versatile"
        )
        answer = chat_completion.choices[0].message.content.replace("### ", "🔹 ").replace("## ", "🔸 ").replace("# ", "🎯 ")
        
        await db.log_conversation(uid, "user", message.text)
        await db.log_conversation(uid, "model", answer)

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download Notes as PDF", callback_data=f"gen_pdf_{message.id}")]])
        
        await processing_msg.edit_text(f"🎓 **Answer for Class {u['class']} ({u['subject']})**\n━━━━━━━━━━━━━━━━━━━━\n{answer}\n━━━━━━━━━━━━━━━━━━━━\n👨‍💻 *Developed by Aditya*", reply_markup=keyboard)
    except Exception as e:
        await processing_msg.edit_text(f"⚠️ *Error:* `{str(e)}`")

# --- 3. PDF GENERATION CALLBACK ---
@app.on_callback_query(filters.regex(r"^gen_pdf_"))
async def handle_pdf_generation(client, cb):
    await cb.answer("Generating PDF... Please wait.")
    text_content = cb.message.text
    topic_header = text_content[:30] + "..." if len(text_content) > 30 else text_content
    pdf_path = None
    try:
        pdf_path = await asyncio.to_thread(generate_study_notes_pdf, cb.from_user.id, topic_header, text_content)
        await app.send_document(chat_id=cb.message.chat.id, document=pdf_path, caption="📚 Here are your formatted compilation notes!")
    except Exception as e:
        await app.send_message(cb.message.chat.id, f"❌ PDF failed: {e}")
    finally:
        if pdf_path: safe_cleanup(pdf_path)

# --- 4. ADVANCED VISION HANDLER (Image + Quiz Button) ---
@app.on_message(filters.photo)
async def vision_handler(client, message):
    msg = await message.reply_text("🔍 *Scanning Image & Finding Answer...* ⏳")
    image_path = None
    try:
        image_path = await message.download()
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        user_q = message.caption if message.caption else "Explain this diagram clearly."
        ai_prompt = f"Answer concisely. IMPORTANT FOR TELEGRAM UI: Do NOT use markdown headers like #, ##. Use **bold text**. Question: {user_q}"

        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": ai_prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model="meta-llama/llama-4-scout-17b-16e-instruct"
        )
        answer = chat_completion.choices[0].message.content.replace("### ", "🔹 ").replace("## ", "🔸 ")
        
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🧠 Generate Quiz from this Image", callback_data=f"imgquiz_{message.id}")]])
        await msg.edit_text(f"🖼️ **Image Analysis**\n━━━━━━━━━━━━━━━━━━━━\n{answer}\n━━━━━━━━━━━━━━━━━━━━\n👨‍💻 *Developed by Aditya*", reply_markup=keyboard)
    except Exception as e:
        await msg.edit_text(f"⚠️ *Vision Error:* `{str(e)}`")
    finally:
        if image_path and os.path.exists(image_path): os.remove(image_path)

# --- 5. IMAGE QUIZ CALLBACK ---
@app.on_callback_query(filters.regex(r"^imgquiz_"))
async def imgquiz_callback(client, cb):
    await cb.answer("Generating Quiz... Please wait! 🧠")
    await cb.message.edit_text("⏳ *Creating Quiz from your Image...*")
    try:
        msg_id = int(cb.data.split("_")[1])
        orig_msg = await client.get_messages(cb.message.chat.id, msg_id)
        image_path = await orig_msg.download()
        
        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
            
        quiz_content = get_ai_generated_quiz_from_image(base64_image)
        await cb.message.edit_text(f"🧠 **Image-Based AI Quiz**\n━━━━━━━━━━━━━━━━━━━━\n{quiz_content}\n━━━━━━━━━━━━━━━━━━━━\n👨‍💻 *Developed by Aditya*")
        if os.path.exists(image_path): os.remove(image_path)
    except Exception as e:
        await cb.message.edit_text(f"⚠️ *Quiz Error:* `{str(e)}`")

# --- 6. VOICE PIPELINE ---
@app.on_message(filters.voice)
async def voice_handler(client, message):
    msg = await message.reply_text("🎧 तुम्हारी आवाज़ सुन रहा हूँ... ⏳")
    audio_path = None
    try:
        audio_path = await message.download()
        with open(audio_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(file=(audio_path, file.read()), model="whisper-large-v3", response_format="text")
        
        user_question = transcription.strip()
        if not user_question: return await msg.edit_text("⚠️ मुझे कुछ सुनाई नहीं दिया।")

        await msg.edit_text(f"🗣️ *सवाल:* {user_question}\n\n🧠 जवाब ढूँढ रहा हूँ...")
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": "You are an AI Study Companion developed by Aditya."}, {"role": "user", "content": user_question}],
            model="llama-3.3-70b-versatile"
        )
        answer = chat_completion.choices[0].message.content
        await msg.edit_text(f"🗣️ *सवाल:* {user_question}\n━━━━━━━━━━━━━━━━━━━━\n{answer}\n━━━━━━━━━━━━━━━━━━━━\n👨‍💻 *Developed by Aditya*")
    except Exception as e:
        await msg.edit_text(f"⚠️ Audio Error: `{str(e)}`")
    finally:
        if audio_path and os.path.exists(audio_path): os.remove(audio_path)

# --- 7. BASIC COMMANDS (/owner, /space) ---
@app.on_message(filters.command("owner"))
async def owner_info(client, message):
    owner_text = "👤 **Developer Info**\n━━━━━━━━━━━━━━━━━━━━\n🎓 **Name:** Aditya\n💻 **Role:** Software Developer\n🚀 **Project:** Local AI Study Companion"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📱 Follow me on Instagram", url="https://www.instagram.com/aadit_paswan.007")]])
    await message.reply_text(owner_text, reply_markup=keyboard)

@app.on_message(filters.command("space"))
async def space_handler(client, message):
    facts = ["Did you know? A day on Venus is longer than a year on Venus! 🪐", "Space is completely silent. 🌌", "There are more stars in the universe than grains of sand on all Earth's beaches. ✨"]
    await message.reply_text(random.choice(facts))

# --- MAIN RUNNER ---
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.init_db())
    print("🚀 Aditya's AI Study Companion is LIVE with latest Groq Models!")
    app.run()
    
