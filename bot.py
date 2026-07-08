import asyncio
import os
import json
import base64
import random
from datetime import datetime, timedelta
import urllib.parse

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

# --- YOUTUBE SCRAPER (This was missing) ---
def get_direct_video(query):
    import urllib.request, urllib.parse, re
    try:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}&sp=EgIYQA%3D%3D"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read().decode()
        video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        if video_ids:
            return f"https://www.youtube.com/watch?v={video_ids[0]}"
    except Exception:
        pass
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"

# --- 1. SMART START & CLASS SETUP (Full Crash-Proof Fix) ---

# सबसे पहले ये फंक्शन रखो
async def send_welcome(client, message, is_callback=False):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 9th Grade", callback_data="setclass_9"), InlineKeyboardButton("🎓 10th Grade", callback_data="setclass_10")],
        [InlineKeyboardButton("🎓 11th Grade", callback_data="setclass_11"), InlineKeyboardButton("🎓 12th Grade", callback_data="setclass_12")],
        [InlineKeyboardButton("🎓 CBSE Exam Mode", callback_data="exam_mode")]
    ])
    text = (
        "🤖 **Welcome to the Elite AI Study Companion!**\n\n"
        "To provide you with highly accurate and personalized answers, "
        "please select your current academic grade below:"
    )
    if is_callback:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.reply_text(text, reply_markup=keyboard)

# स्टार्ट कमांड
@app.on_message(filters.command(["start", "setup"]))
async def start_command(client, message):
    await send_welcome(client, message, is_callback=False)

# यूनिवर्सल बैक बटन (मैसेज एडिट करेगा, नया नहीं भेजेगा)
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
    
    # यह वाला कोड 'वाइट लाइन' वाली समस्या खत्म कर देगा
    await cb.message.edit_text(
        f"📘 **Grade {grade} Selected.**\nNow, please select your target subject:", 
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await cb.answer() # यह बटन दबाते ही लोडिंग को खत्म कर देगा!
    
    
# --- 2. ADVANCED TEXT SOLVER (100% Clean UI & Crash-Proof Edition) ---
@app.on_message(filters.text & ~filters.command(["start", "setup", "quiz", "owner", "space"]))
async def smart_solver(client, message):
    uid = message.from_user.id
    if uid not in user_profiles: 
        return await message.reply("⚠️ **Please use the `/setup` command first.**")
    
    u = user_profiles[uid]
    processing_msg = await message.reply("🔍 *Analyzing your query for a perfect answer...* ⏳")
    
    try:
        from groq import Groq
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

        # 🌟 THE ULTIMATE STRICT PROMPT FOR CLEAN UI & MATH 🌟
        sys_prompt = (
            f"You are an Elite AI Study Companion for a {u['class']}th grade {u['subject']} CBSE student. "
            f"RESPOND IN PROFESSIONAL ENGLISH ONLY. "
            f"CRITICAL FORMATTING RULES:\n"
            f"1. ZERO FLUFF: Give direct, to-the-point answers. No long, cluttered paragraphs.\n"
            f"2. BULLET POINTS ONLY: Use the '•' symbol for all explanations.\n"
            f"3. SPACING (VITAL): You MUST add a double line break (blank line) between EVERY single bullet point to keep the UI spacious and clean.\n"
            f"4. MATH & FORMULAS: NEVER use programming symbols like '^', '*', or '/'. You MUST use real Unicode (e.g., ², ³, ⁻¹, ×, ÷). Write formulas cleanly on their own lines (e.g., F = m × a).\n"
            f"5. HEADINGS: Use **Bold Text** for headings. NEVER use Markdown headers like #, ##, or ###.\n"
            f"6. SUMMARY: Always end with a short '**💡 Quick Summary:**' section."
        )
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": message.text}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        
        raw_answer = chat_completion.choices[0].message.content
        
        # 🧹 CLEANUP: टेलीग्राम UI को खराब करने वाले सारे सिंबल्स को डिलीट करना
        # (हम ** को नहीं छेड़ रहे हैं ताकि बोल्ड टेक्स्ट काम करता रहे)
        clean_answer = raw_answer.replace("###", "").replace("##", "").replace("#", "").replace("`", "")
        
        # 🎬 YouTube Video Scraper Call
        search_query = f"{message.text} class {u['class']} CBSE {u['subject']} explanation -shorts -animation"
        youtube_link = await asyncio.to_thread(get_direct_video, search_query)
        
        # 🔘 Interactive Buttons
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Watch Best Video", url=youtube_link), InlineKeyboardButton("📥 Get PDF Notes", callback_data=f"gen_pdf_{message.id}")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data=f"back_to_menu_{message.id}")]
         ])
        
        
        
        # 📐 PERFECT LAYOUT: हेडर, बॉडी और फुटर एकदम सेट
        final_reply = (
            f"📖 **{u['subject'].upper()} STUDY GUIDE**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{clean_answer}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 *Engineered by Aditya*\n"
            f"📸 [Follow on Instagram](https://www.instagram.com/aadit_paswan.007)"
        )
        
        # 🚀 Send the message safely
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

# --- 5. ADVANCED VISION HANDLER (Clean UI Update) ---
@app.on_message(filters.photo)
async def vision_handler(client, message):
    msg = await message.reply_text("📸 *Processing image through Vision AI...* ⏳")
    image_path = None
    try:
        image_path = await message.download()
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        user_q = message.caption if message.caption else "Analyze this educational image and explain its core concepts."
        
        # 🌟 STRICT BULLET-POINT PROMPT FOR VISION 🌟
        ai_prompt = (
            f"You are an Elite AI Study Companion.\n"
            f"Analyze this image and answer the user's query: '{user_q}'.\n"
            f"CRITICAL FORMATTING RULES:\n"
            f"1. ZERO FLUFF: Answer directly using ONLY bullet points ('•'). No long paragraphs.\n"
            f"2. MATH FORMAT: NEVER use '^' or '*'. Use real Unicode (e.g., ², ³, ×, ÷).\n"
            f"3. SPACING: Add a blank line (double enter) between EVERY bullet point.\n"
            f"4. HEADINGS: Use **Bold Text**. NEVER use markdown headers like # or ##.\n"
            f"5. SUMMARY: End with a '**💡 Quick Summary:**' section."
        )
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": ai_prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model="meta-llama/llama-4-scout-17b-16e-instruct"
            
        )
        
        raw_answer = chat_completion.choices[0].message.content
        clean_answer = raw_answer.replace("###", "").replace("##", "").replace("#", "").replace("`", "")
        
        search_query = message.caption if message.caption else "Important educational concept"
        youtube_link = await asyncio.to_thread(get_direct_video, search_query)
        
        keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("▶️ Watch Best Video", url=youtube_link), InlineKeyboardButton("📥 Get PDF Notes", callback_data=f"gen_pdf_{message.id}")],
    [InlineKeyboardButton("🔙 Back to Main Menu", callback_data=f"back_to_menu_{message.id}")]
])
        
        
        final_reply = (
            f"📸 **VISUAL ANALYSIS REPORT**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{clean_answer}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 *Engineered by Aditya*\n"
            f"📸 [Follow on Instagram](https://www.instagram.com/aadit_paswan.007)"
        )
        
        await msg.edit_text(final_reply, reply_markup=keyboard, disable_web_page_preview=True)
        
    # यह वाला हिस्सा तुम्हारे कोड से गायब हो गया था, जिसे मैंने वापस लगा दिया है 👇
    except Exception as e:
        await msg.edit_text(f"⚠️ *Vision Error:* `{str(e)}`")
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
            

# --- 5. IMAGE QUIZ CALLBACK (With Insta Link) ---
@app.on_callback_query(filters.regex(r"^imgquiz_"))
async def imgquiz_callback(client, cb):
    await cb.answer("Synthesizing Quiz... 🧠")
    await cb.message.edit_text("⏳ *Extracting data to formulate a quiz...*")
    try:
        msg_id = int(cb.data.split("_")[1])
        orig_msg = await client.get_messages(cb.message.chat.id, msg_id)
        image_path = await orig_msg.download()
        
        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
            
        quiz_content = get_ai_generated_quiz_from_image(base64_image)
        
        final_reply = (
            f"🧠 **Interactive AI Quiz**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{quiz_content}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 *Engineered by Aditya*\n"
            f"📸 [Follow me on Instagram](https://www.instagram.com/aadit_paswan.007)"
        )
        await cb.message.edit_text(final_reply, disable_web_page_preview=True)
        if os.path.exists(image_path): os.remove(image_path)
    except Exception as e:
        await cb.message.edit_text(f"⚠️ *Quiz Engine Error:* `{str(e)}`")

# --- 6. VOICE PIPELINE (100% Old Strict Prompt Restored) ---
@app.on_message(filters.voice)
async def voice_handler(client, message):
    uid = message.from_user.id
    u = user_profiles.get(uid, {"class": "9", "subject": "Science"}) # User Profile Fetch
    
    msg = await message.reply_text("🎙️ *Audio received. Transcribing...* ⏳")
    audio_path = None
    try:
        audio_path = await message.download()
        with open(audio_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(audio_path, file.read()), model="whisper-large-v3"
            )
        
        user_question = transcription.text.strip()
        if not user_question:
            return await msg.edit_text("⚠️ *Transcription failed. Please speak clearly.*")
        
        await msg.edit_text(f"🎙️ *Transcribed:* {user_question}\n\n🧠 *Generating expert response...* ⏳")
        
        # 🌟 THE ULTIMATE STRICT PROMPT (Same as Text Solver) 🌟
        sys_prompt = (
            f"You are an Elite AI Study Companion for a {u['class']}th grade {u['subject']} CBSE student. "
            f"RESPOND IN PROFESSIONAL ENGLISH ONLY. "
            f"CRITICAL FORMATTING RULES:\n"
            f"1. ZERO FLUFF: Give direct, to-the-point answers. No long, cluttered paragraphs.\n"
            f"2. BULLET POINTS ONLY: Use the '•' symbol for all explanations.\n"
            f"3. SPACING (VITAL): You MUST add a double line break (blank line) between EVERY single bullet point to keep the UI spacious and clean.\n"
            f"4. MATH & FORMULAS: NEVER use programming symbols like '^', '*', or '/'. You MUST use real Unicode (e.g., ², ³, ⁻¹, ×, ÷). Write formulas cleanly on their own lines (e.g., F = m × a).\n"
            f"5. HEADINGS: Use **Bold Text** for headings. NEVER use Markdown headers like #, ##, or ###.\n"
            f"6. SUMMARY: Always end with a short '**💡 Quick Summary:**' section."
        )
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_question}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        
        raw_answer = chat_completion.choices[0].message.content
        clean_answer = raw_answer.replace("###", "").replace("##", "").replace("#", "").replace("`", "")
        
        youtube_link = await asyncio.to_thread(get_direct_video, user_question)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Watch Best Video", url=youtube_link), InlineKeyboardButton("📥 Get PDF Notes", callback_data=f"gen_pdf_{message.id}")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data=f"back_to_menu_{message.id}")]
        ])

        final_reply = (
            f"🎙️ **AUDIO QUERY ANSWERED**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"**Q:** *{user_question}*\n\n"
            f"{clean_answer}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 *Engineered by Aditya*\n"
            f"📸 [Follow on Instagram](https://www.instagram.com/aadit_paswan.007)"
        )
        
        await msg.edit_text(final_reply, reply_markup=keyboard, disable_web_page_preview=True)
        
    except Exception as e:
        await msg.edit_text(f"⚠️ *Audio Pipeline Error:* `{str(e)}`")
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        
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

# --- 9. AI-POWERED CBSE EXAM ENGINE (ULTIMATE UI & CLEAN MATH) ---

import asyncio

# ✨ एनिमेटेड ट्रांज़िशन (ऐप जैसा स्मूथ इफ़ेक्ट)
async def animate_transition(cb, text):
    try:
        await cb.message.edit_text(f"⏳ *{text}...*")
        await asyncio.sleep(0.3)
    except:
        pass

# 📍 लेवल 1: क्लास सिलेक्शन (मेन पैनल)
@app.on_callback_query(filters.regex(r"^exam_mode$"))
async def exam_root_panel(client, cb):
    await animate_transition(cb, "Opening Exam Center")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 9th Grade", callback_data="ex_cls_9"), InlineKeyboardButton("🎓 10th Grade", callback_data="ex_cls_10")],
        [InlineKeyboardButton("🎓 11th Grade", callback_data="ex_cls_11"), InlineKeyboardButton("🎓 12th Grade", callback_data="ex_cls_12")],
        [InlineKeyboardButton("🔙 Exit to Main Menu", callback_data="back_to_menu")]
    ])
    await cb.message.edit_text(
        "🎓 **UNIVERSAL CBSE EXAM CENTER**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Welcome to the advanced preparation portal.\n\n"
        "👇 **Select your target class:**",
        reply_markup=keyboard
    )

# 📍 लेवल 2: सब्जेक्ट सिलेक्शन (डायनामिक ग्रिड)
@app.on_callback_query(filters.regex(r"^ex_cls_(.*)$"))
async def exam_subject_panel(client, cb):
    grade = cb.matches[0].group(1)
    await animate_transition(cb, f"Loading {grade}th Subjects")

    if grade in ["9", "10"]:
        subs = [
            [InlineKeyboardButton("🧪 Science", callback_data=f"ex_act_{grade}_Science"), InlineKeyboardButton("📐 Maths", callback_data=f"ex_act_{grade}_Maths")],
            [InlineKeyboardButton("🌍 SST", callback_data=f"ex_act_{grade}_Social_Science"), InlineKeyboardButton("📝 English", callback_data=f"ex_act_{grade}_English")]
        ]
    else:
        subs = [
            [InlineKeyboardButton("⚡ Physics", callback_data=f"ex_act_{grade}_Physics"), InlineKeyboardButton("🧪 Chemistry", callback_data=f"ex_act_{grade}_Chemistry")],
            [InlineKeyboardButton("🧬 Biology", callback_data=f"ex_act_{grade}_Biology"), InlineKeyboardButton("📐 Maths", callback_data=f"ex_act_{grade}_Maths")]
        ]

    subs.append([InlineKeyboardButton("🔙 Back to Classes", callback_data="exam_mode")])
    
    await cb.message.edit_text(
        f"📚 **CLASS {grade}TH PORTAL**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Choose a subject to continue:\n",
        reply_markup=InlineKeyboardMarkup(subs)
    )

# 📍 लेवल 3: एक्शन सिलेक्शन (क्या करना है?)
@app.on_callback_query(filters.regex(r"^ex_act_(.*)_(.*)$"))
async def exam_action_panel(client, cb):
    grade = cb.matches[0].group(1)
    subj = cb.matches[0].group(2)
    await animate_transition(cb, f"Accessing {subj}")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 AI Important Questions", callback_data=f"ex_ask_{grade}_{subj}")],
        [InlineKeyboardButton("⏱️ Timed Mock Test", callback_data=f"ex_mock_{grade}_{subj}")],
        [InlineKeyboardButton(f"🔙 Back to {grade}th Subjects", callback_data=f"ex_cls_{grade}")]
    ])
    await cb.message.edit_text(
        f"🎯 **TARGET: {subj.upper()} ({grade}th)**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Select your preparation tool:\n",
        reply_markup=keyboard
    )

# 📍 लेवल 4: AI ट्रिगर (यूज़र से चैप्टर का नाम माँगना)
@app.on_callback_query(filters.regex(r"^ex_ask_(.*)_(.*)$"))
async def exam_ask_chapter(client, cb):
    grade = cb.matches[0].group(1)
    subj = cb.matches[0].group(2)
    await animate_transition(cb, "Initializing AI Engine")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔙 Cancel & Go Back", callback_data=f"ex_act_{grade}_{subj}")]
    ])
    await cb.message.edit_text(
        f"⚡ **AI ENGINE ACTIVATED** ⚡\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"**Target:** CBSE {grade}th {subj}\n\n"
        f"✏️ **How to use:**\n"
        f"To get the most important questions with a clean UI, type the command like this:\n\n"
        f"`/topic {grade} {subj} [Chapter Name]`\n\n"
        f"*(Example: /topic 9 Science Motion)*",
        reply_markup=keyboard
    )

# 📍 लेवल 5: स्मार्ट AI जेनरेटर (कबाड़ साफ़ करने वाला फ़िल्टर + तगड़ा UI)
@app.on_message(filters.command("topic"))
async def generate_exam_topic(client, message):
    try:
        # कमांड को तोड़कर क्लास, सब्जेक्ट और चैप्टर निकालना
        parts = message.text.split(" ", 3)
        if len(parts) < 4:
            return await message.reply("⚠️ **Format Error!** Please use: `/topic [Class] [Subject] [Chapter Name]`")
        
        grade, subj, chapter = parts[1], parts[2], parts[3]
        processing_msg = await message.reply("🔍 *Analyzing CBSE past papers and extracting top questions...* ⏳")

        # 🌟 द अल्टीमेट स्ट्रिक्ट प्रॉम्प्ट (For Clean UI & Math)
        sys_prompt = (
            f"You are an Elite CBSE Board Examiner for {grade}th grade {subj}. "
            f"Provide the 3 most important exam questions and their step-by-step solutions for the chapter: '{chapter}'. "
            f"CRITICAL FORMATTING RULES:\n"
            f"1. ZERO FLUFF: Answer directly. No introductory sentences.\n"
            f"2. BULLET POINTS ONLY: Use the '•' symbol. Add a blank line (double enter) between every point.\n"
            f"3. MATH FORMAT: NEVER use markdown code blocks (` or ```). NEVER use markdown headers (# or ##).\n"
            f"4. USE UNICODE: Use real Unicode for math/science (e.g., ², ³, ×, ÷, ⁻¹, °, √, H₂O, CO₂). Never use ^ or * for math.\n"
            f"5. STRUCTURE: Clearly label 'Q1:', 'Q2:', 'Q3:' and 'Solution:'."
        )
        
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"Generate important questions for chapter: {chapter}"}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2
        )
        
        raw_answer = response.choices[0].message.content
        
        # 🧹 कबाड़ साफ़ करने वाला फ़िल्टर (डबल प्रोटेक्शन)
        clean_answer = raw_answer.replace("###", "").replace("##", "").replace("#", "").replace("`", "")
        
        final_reply = (
            f"📖 **{chapter.upper()} - CBSE {grade}TH {subj.upper()}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{clean_answer}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎓 *Engineered by Aditya | Elite AI Companion*"
        )
        
        await processing_msg.edit_text(final_reply)

    except Exception as e:
        await message.reply(f"⚠️ **AI Generation Error:** `{str(e)}`")
    

@app.on_callback_query(filters.regex(r"^exam_"))
async def exam_callback(client, cb):
    if cb.data == "exam_imp":
        # ये फीचर सीधे उस चैप्टर के इंपॉर्टेंट पॉइंट्स और फॉर्मूले निकाल कर देगा
        await cb.message.edit_text("🔍 **Fetching Most Likely Exam Questions...**\n\n*Select a subject to start:*", 
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Physics", callback_data="get_imp_phys"), InlineKeyboardButton("Maths", callback_data="get_imp_math")]]))
    
    elif cb.data == "exam_mock":
        await cb.message.edit_text("⏱️ **Mock Test Engine**\n\n*Feature Under Construction. Coming in next update!*")

    elif cb.data == "exam_stats":
        await cb.message.edit_text("📊 **Performance Report**\n\n*You are doing great in Physics! Chemistry needs a bit more focus.*")
    
# --- MAIN RUNNER ---
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.init_db())
    print("🚀 Aditya's Elite AI Study Companion is LIVE on Secure Servers!")
    app.run()
        
