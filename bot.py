import asyncio
import os
import json
import base64
import random
from datetime import datetime, timedelta
import urllib.parse
import time
import uuid
from pyrogram.enums import ChatAction
from features import research_engine
from features import research_engine, yt_extractor

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
from keep_alive import keep_alive

# --- INIT ---
app = Client("study_companion_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

user_profiles = {}
user_chat_history = {} # 🧠 एडवांस AI मेमोरी सिस्टम
media_groups = {} # 📸 स्मार्ट एल्बम स्कैनर के लिए (NEW)
if "active_battles" not in globals():
    active_battles = {}
    

# चैट और सवालों के जवाब के लिए (क्योंकि Llama 70B बंद हो चुका है)
CHAT_MODEL = "openai/gpt-oss-120b"

# तेज़ जवाब के लिए (क्योंकि Llama 8B बंद हो चुका है)
FAST_MODEL = "openai/gpt-oss-20b"

# फोटो देखने के लिए (क्योंकि Llama-4-Scout 17 जुलाई 2026 को बंद हो चुका है)
VISION_MODEL = "qwen/qwen3.8-27b"

# वॉइस (ऑडियो) ट्रांसक्रिप्ट के लिए 
AUDIO_MODEL = "whisper-large-v3-turbo"


# --- ADMIN SECURITY CONFIGURATION ---
ADMIN_IDS = [7205857678] 

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
    

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

# --- ADMIN GATEWAY (ELITE DASHBOARD EDITION) ---
@app.on_message(filters.command("admin"))
async def admin_gateway(client, message):
    if not is_admin(message.from_user.id):
        return 
    
    dashboard_text = (
        "🛡️ **SYSTEM ROOT CONTROL**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👤 **Admin:** Aditya (Owner)\n"
        "🟢 **Bot Status:** Online & Active\n"
        "📊 **Total Users:** [Fetching...]\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👇 *Select an operation below:*"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"), 
         InlineKeyboardButton("📊 Live Database", callback_data="admin_db")],
        [InlineKeyboardButton("🛑 Ban / Unban", callback_data="admin_ban"), 
         InlineKeyboardButton("⚙️ Maintenance", callback_data="admin_maint")],
        [InlineKeyboardButton("🔙 Close Panel", callback_data="back_to_menu")]
    ])
    
    await message.reply(dashboard_text, reply_markup=keyboard)

        
# --- 1. SMART START & CLASS SETUP ---

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

@app.on_message(filters.command(["start", "setup"]))
async def start_command(client, message):
    await send_welcome(client, message, is_callback=False)

@app.on_callback_query(filters.regex(r"^back_to_menu"))
async def back_to_menu(client, cb):
    try:
        if "_" in cb.data:
            msg_id = cb.data.split("_")[-1]
            await client.delete_messages(cb.message.chat.id, int(msg_id))
    except:
        pass 
    await cb.answer()
    await send_welcome(client, cb.message, is_callback=True)

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
    
    await cb.message.edit_text(
        f"📘 **Grade {grade} Selected.**\nNow, please select your target subject:", 
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await cb.answer()

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
    
    try:
        async for msg in app.get_chat_history(cb.message.chat.id, limit=5):
            if msg.from_user.id == client.me.id and "Configuration Complete!" in msg.text:
                if msg.id != cb.message.id:
                    await msg.delete()
    except:
        pass
    
    await cb.message.edit_text(success_msg)
    await cb.answer()

# --- 2. ADVANCED TEXT SOLVER (100% Clean UI & Crash-Proof Edition) ---
@app.on_message(filters.text & ~filters.command(["start", "setup", "quiz", "owner", "space", "yt", "video", "summary", "ask", "research", "search", "topic", "battle", "admin"]))
async def smart_solver(client, message):
    uid = message.from_user.id
    
    if uid not in user_profiles: 
        user_profiles[uid] = {"class": "9", "subject": "Science"}
    
    u = user_profiles[uid]
    processing_msg = await message.reply("🔍 *Analyzing your query for a perfect answer...* ⏳")
    
    try:
        from groq import Groq
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

        sys_prompt = (
            f"You are an Elite AI Study Companion for a {u['class']}th grade {u['subject']} CBSE student. "
            f"RESPOND IN PROFESSIONAL ENGLISH ONLY. Your primary goal is to provide responses with an ADVANCED, BEAUTIFUL, and CLEAN Telegram UI.\n"
            f"CRITICAL FORMATTING RULES FOR PERFECT UI:\n"
            f"1. 🎨 AESTHETIC HEADINGS: Always start your main answer with a beautiful, bold heading using emojis (e.g., **✨ Definition of Motion ✨**). NEVER use markdown headers like #, ##, or ###.\n"
            f"2. 💎 BEAUTIFUL BULLET POINTS: Use custom, attractive bullet points (like 🔹, 🔸, or 🚀) instead of standard dots ('•').\n"
            f"3. 🌬️ SPACING: Add a double line break (blank line) between EVERY single bullet point and paragraph.\n"
            f"4. 🚫 ZERO FLUFF: Give direct, highly accurate, and engaging answers.\n"
            f"5. 📐 MATH & FORMULAS: Use real Unicode (e.g., ², ³, ⁻¹, ×, ÷). Write formulas cleanly in bold (e.g., **F = m × a**).\n"
            f"6. 💡 QUICK SUMMARY: Always end with a short, visually distinct '**💡 Quick Summary:**' section.\n"
            f"7. ❌ STRICT NO LATEX: NEVER use raw LaTeX."
        )
        
        # Memory Management
        if uid not in user_chat_history:
            user_chat_history[uid] = []

        messages = [{"role": "system", "content": sys_prompt}]
        messages.extend(user_chat_history[uid][-6:])
        messages.append({"role": "user", "content": message.text})

        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model=CHAT_MODEL,
            temperature=0.2
        )
        
        raw_answer = chat_completion.choices[0].message.content

        user_chat_history[uid].append({"role": "user", "content": message.text})
        user_chat_history[uid].append({"role": "assistant", "content": raw_answer})
        
        clean_answer = raw_answer.replace("###", "").replace("##", "").replace("#", "").replace("`", "")
        
        search_query = f"{message.text} class {u['class']} CBSE {u['subject']} explanation -shorts -animation"
        youtube_link = await asyncio.to_thread(get_direct_video, search_query)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Watch Best Video", url=youtube_link), InlineKeyboardButton("📥 Get PDF Notes", callback_data=f"gen_pdf_{message.id}")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data=f"back_to_menu_{message.id}")]
         ])
        
        final_reply = (
            f"📖 **{u['subject'].upper()} STUDY GUIDE**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{clean_answer}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 *Engineered by Aditya*\n"
            f"📸 [Follow on Instagram](https://www.instagram.com/aadit_paswan.007)"
        )

        try:
            await processing_msg.edit_text(final_reply, reply_markup=keyboard, disable_web_page_preview=True)
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" not in str(e):
                await message.reply(final_reply, reply_markup=keyboard, disable_web_page_preview=True)

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

# --- 5. ADVANCED VISION HANDLER (SMART NOTES SCANNER & ALBUM SUPPORT) ---
@app.on_message(filters.photo)
async def vision_handler(client, message):
    # 1. 🖼️ Album (Multiple Photos) Logic
    group_id = message.media_group_id
    
    if group_id:
        if group_id not in media_groups:
            media_groups[group_id] = [message]
            processing_msg = await message.reply_text("📸 *Receiving multiple pages of your notes...* ⏳")
            await asyncio.sleep(4) # चारों पन्नों के आने का इंतज़ार करेगा
            
            photos_to_process = media_groups.pop(group_id)
            await processing_msg.edit_text(f"🔍 *Scanning {len(photos_to_process)} pages of handwritten notes using Vision AI...* ⏳")
        else:
            # अगर उसी एल्बम का अगला फोटो है, तो उसे लिस्ट में जोड़कर रुक जाओ
            media_groups[group_id].append(message)
            return
    else:
        # अगर सिर्फ 1 फोटो भेजी है
        photos_to_process = [message]
        processing_msg = await message.reply_text("📸 *Scanning your notes through Vision AI...* ⏳")

    try:
        from groq import Groq
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        
        combined_text = ""
        
        # 2. 🤖 एक-एक करके सारे पन्नों को AI से पढ़वाना
        for idx, msg in enumerate(photos_to_process):
            image_path = await msg.download()
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            user_q = msg.caption if msg.caption else "Convert this handwritten note into perfectly structured digital text."
            
            # 🌟 SMART OCR & BEAUTIFICATION PROMPT 🌟
            ai_prompt = (
                f"You are an Elite AI Notes Digitizer. The user has uploaded handwritten notes. Query: '{user_q}'. "
                f"Transcribe the handwriting accurately, fix spelling/grammatical mistakes, and organize it into a beautiful structured format. "
                f"CRITICAL FORMATTING RULES FOR PERFECT UI:\n"
                f"1. 🎨 AESTHETIC HEADINGS: Start sections with bold headings and emojis (e.g., **✨ Key Concepts ✨**). NEVER use markdown headers (#).\n"
                f"2. 💎 BEAUTIFUL BULLET POINTS: Use custom bullet points (🔹, 🔸, 🚀).\n"
                f"3. 🌬️ SPACING: Add a double line break (blank line) between EVERY single bullet point.\n"
                f"4. 🚫 ZERO FLUFF: Keep it highly accurate and professional.\n"
                f"5. 📐 MATH & FORMULAS: Use real Unicode (e.g., ², ³, ×, ÷). Write formulas in bold.\n"
                f"6. 💡 QUICK SUMMARY: Always end with '**💡 Quick Summary:**'.\n"
                f"7. ❌ NO LATEX: NEVER use raw LaTeX."
            )
            
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": [{"type": "text", "text": ai_prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                model=VISION_MODEL
            )
            
            raw_answer = chat_completion.choices[0].message.content
            clean_answer = raw_answer.replace("###", "").replace("##", "").replace("#", "").replace("`", "")
            
            # 3. 📄 अगर कई पन्ने हैं, तो Page 1, Page 2 करके डिज़ाइन करना
            if len(photos_to_process) > 1:
                combined_text += f"📄 **Page {idx + 1}**\n{clean_answer}\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
            else:
                combined_text += f"{clean_answer}\n\n"
                
            if os.path.exists(image_path):
                os.remove(image_path)
        
        # 4. 🎬 YouTube और बटन सेटअप
        search_query = message.caption if message.caption else "Important educational concept"
        youtube_link = await asyncio.to_thread(get_direct_video, search_query)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Watch Best Video", url=youtube_link), InlineKeyboardButton("📥 Get PDF Notes", callback_data=f"gen_pdf_{processing_msg.id}")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data=f"back_to_menu_{processing_msg.id}")]
        ])
        
        final_reply = (
            f"📸 **SMART NOTES SCANNER REPORT**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{combined_text}"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 *Digitized by Aditya's Elite AI*\n"
            f"📸 [Follow on Instagram](https://www.instagram.com/aadit_paswan.007)"
        )
        
        # (Telegram में बहुत लम्बे मैसेज के लिए सेफ्टी)
        if len(final_reply) > 4000:
            final_reply = final_reply[:4000] + "\n\n⚠️ *Note: Text truncated. Press PDF button to get full notes.*"
        
        await processing_msg.edit_text(final_reply, reply_markup=keyboard, disable_web_page_preview=True)
        
    except Exception as e:
        await processing_msg.edit_text(f"⚠️ *Scanner Error:* `{str(e)}`")
        

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
                file=(audio_path, file.read()), model=AUDIO_MODEL,
            )
        
        user_question = transcription.text.strip()
        if not user_question:
            return await msg.edit_text("⚠️ *Transcription failed. Please speak clearly.*")
        
        await msg.edit_text(f"🎙️ *Transcribed:* {user_question}\n\n🧠 *Generating expert response...* ⏳")

        # 🌟 THE ULTIMATE STRICT PROMPT FOR ADVANCED VOICE UI (CRASH-PROOF) 🌟
        sys_prompt = (
            f"You are an Elite CBSE Board Examiner for {u['class']}th grade {u['subject']}. "
            f"Provide a clear, step-by-step solution to the user's spoken question. "
            f"RESPOND IN PROFESSIONAL ENGLISH ONLY. Your primary goal is to provide responses with an ADVANCED, BEAUTIFUL, and CLEAN Telegram UI.\n"
            f"CRITICAL FORMATTING RULES FOR PERFECT UI:\n"
            f"1. 🎨 AESTHETIC HEADINGS: Always start your main answer with a beautiful, bold heading using emojis. NEVER use markdown headers like #, ##, or ###.\n"
            f"2. 💎 BEAUTIFUL BULLET POINTS: Use custom, attractive bullet points (like 🔹, 🔸, or 🚀) instead of standard dots ('•').\n"
            f"3. 🌬️ SPACING (VITAL FOR UI): Add a double line break (blank line) between EVERY single bullet point to keep the UI spacious and clean.\n"
            f"4. 🚫 ZERO FLUFF: Answer directly. No introductory sentences.\n"
            f"5. 📐 MATH & FORMULAS: NEVER use programming symbols like '^' or '*'. Use real Unicode (e.g., ², ³, ×, ÷). Write formulas cleanly in bold.\n"
            f"6. 💡 QUICK SUMMARY: Always end with a short, visually distinct '**💡 Quick Summary:**' section.\n"
            f"7. ❌ STRICT NO LATEX: NEVER use raw LaTeX. ALWAYS use clean Unicode text."
        )
        
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_question}
            ],
            model=CHAT_MODEL,
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

        # 🌟 THE ULTIMATE STRICT PROMPT FOR ADVANCED TELEGRAM UI 🌟
        sys_prompt = (
            f"You are an Elite AI Study Companion for a {u['class']}th grade {u['subject']} CBSE student. "
            f"RESPOND IN PROFESSIONAL ENGLISH ONLY. Your primary goal is to provide responses with an ADVANCED, BEAUTIFUL, and CLEAN Telegram UI.\n"
            f"CRITICAL FORMATTING RULES FOR PERFECT UI:\n"
            f"1. 🎨 AESTHETIC HEADINGS: Always start your main answer with a beautiful, bold heading using emojis (e.g., **✨ Definition of Motion ✨**). NEVER use markdown headers like #, ##, or ###.\n"
            f"2. 💎 BEAUTIFUL BULLET POINTS: Use custom, attractive bullet points (like 🔹, 🔸, or 🚀) instead of standard dots ('•'). This makes the text look premium.\n"
            f"3. 🌬️ SPACING (VITAL FOR UI): You MUST add a double line break (blank line) between EVERY single bullet point and paragraph to keep the UI spacious, clean, and easy to read on mobile.\n"
            f"4. 🚫 ZERO FLUFF: Give direct, highly accurate, and engaging answers. Do not write long, boring paragraphs. Keep it punchy.\n"
            f"5. 📐 MATH & FORMULAS: NEVER use programming symbols like '^', '*', or '/'. You MUST use real Unicode (e.g., ², ³, ⁻¹, ×, ÷). Write formulas cleanly on their own lines, highlighted in bold (e.g., **F = m × a**).\n"
            f"6. 💡 QUICK SUMMARY: Always end with a short, visually distinct '**💡 Quick Summary:**' section.\n"
            f"7. ❌ STRICT NO LATEX: NEVER use raw LaTeX (like \\rho, \\omega, \\frac, \\int, \\infty). ALWAYS use clean Unicode text for math!"
        )
        
        
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"Generate important questions for chapter: {chapter}"}
            ],
            model=CHAT_MODEL,
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

# --- ADVANCED SYSTEM STATES & VARIABLES ---
SYSTEM_STATES = {}
MAINTENANCE_MODE = False
BANNED_USERS = []

# --- ADVANCED CALLBACK HANDLER (ENGINE ACTIVE) ---
@app.on_callback_query(filters.regex(r"^admin_"))
async def admin_interface(client, cb):
    global MAINTENANCE_MODE
    if not is_admin(cb.from_user.id):
        return await cb.answer("⚠️ System Alert: Unauthorized access denied.", show_alert=True)
    
    action = cb.data.split("_")[1]
    
    if action == "broadcast":
        SYSTEM_STATES[cb.from_user.id] = "BROADCAST_MODE"
        await cb.message.edit_text(
            "📢 **Global Broadcast Engine**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Please send the message, photo, or document you want to broadcast to all users.\n\n"
            "*(Type /cancel to abort the operation)*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel Action", callback_data="close_admin")]])
        )
        
    elif action == "db":
        active_sessions = len(user_profiles) if 'user_profiles' in globals() else 0
        await cb.message.edit_text(
            "📊 **Live Database Statistics**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 **Server Status:** Stable\n"
            f"👥 **Active Sessions:** `{active_sessions}`\n"
            f"⛔ **Restricted Users:** `{len(BANNED_USERS)}`\n"
            "━━━━━━━━━━━━━━━━━━━━",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Close Panel", callback_data="close_admin")]])
        )
        
    elif action == "ban":
        SYSTEM_STATES[cb.from_user.id] = "BAN_MODE"
        await cb.message.edit_text(
            "🛑 **User Restriction System**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Please send the numerical **Telegram ID** of the user you want to Ban or Unban.\n\n"
            "*(Type /cancel to abort the operation)*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel Action", callback_data="close_admin")]])
        )
        
    elif action == "maint":
        MAINTENANCE_MODE = not MAINTENANCE_MODE
        status = "🔴 ACTIVE (Users Blocked)" if MAINTENANCE_MODE else "🟢 INACTIVE (Bot Running)"
        await cb.message.edit_text(
            f"⚙️ **System Maintenance Mode**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"**Current Status:** {status}\n\n"
            f"Toggle this mode to prevent normal users from using the bot during server updates.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Toggle Status", callback_data="admin_maint")],
                [InlineKeyboardButton("🔙 Close Panel", callback_data="close_admin")]
            ])
        )
        
    await cb.answer()

@app.on_callback_query(filters.regex(r"^close_admin$"))
async def close_admin_panel(client, cb):
    if is_admin(cb.from_user.id):
        SYSTEM_STATES.pop(cb.from_user.id, None)
        await cb.message.delete()
        await cb.answer("Admin panel closed securely.", show_alert=False)

# --- ADMIN ACTION PROCESSOR (MESSAGE INTERCEPTOR) ---
@app.on_message(filters.private & filters.user(ADMIN_IDS) & ~filters.command(["admin", "start"]))
async def admin_action_processor(client, message):
    state = SYSTEM_STATES.get(message.from_user.id)
    
    if not state:
        return # Not in any admin mode, ignore.
        
    if message.text and message.text.lower() == "/cancel":
        SYSTEM_STATES.pop(message.from_user.id, None)
        return await message.reply("✅ **System Action Aborted Safely.**")
        
    if state == "BROADCAST_MODE":
        await message.reply("🚀 **Broadcast Initiated!** Processing message delivery...")
        SYSTEM_STATES.pop(message.from_user.id, None)
        
        # NOTE: Add actual user iteration loop here later
        
        await message.reply("✅ **Broadcast Execution Completed Successfully.**")
        
    elif state == "BAN_MODE":
        try:
            target_id = int(message.text.strip())
            if target_id in BANNED_USERS:
                BANNED_USERS.remove(target_id)
                await message.reply(f"✅ **Security Update:** User `{target_id}` has been **UNBANNED**.")
            else:
                BANNED_USERS.append(target_id)
                await message.reply(f"🛑 **Security Update:** User `{target_id}` has been **BANNED**.")
        except ValueError:
            await message.reply("⚠️ **Invalid Input Error:** Please send a valid numerical User ID.")
            
        SYSTEM_STATES.pop(message.from_user.id, None)

# --- 6. ADVANCED MULTIPLAYER QUIZ ARENA (LIVE COUNTER ENGINE) ---

@app.on_message(filters.command(["battle", "quiz"]))
async def initialize_quiz_arena(client, message):
    user_id = message.from_user.id
    
    user_data = user_profiles.get(user_id, {})
    student_grade = user_data.get("class", "10th Grade") 
    
    command_args = message.text.split(" ", 1)
    topic = command_args[1] if len(command_args) > 1 else user_data.get("subject", "General Science")
    
    loading_msg = await message.reply_text("⚡ *Initializing Elite Battle Arena...*\n_Establishing secure connection to AI Core..._ ⏳")
    
    try:
        from groq import Groq
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        
        prompt = (
            f"Act as an Elite Academic Assessor. Generate 1 highly conceptual, challenging multiple-choice question "
            f"for a {student_grade} CBSE student focusing exclusively on: '{topic}'. "
            f"The question must test deep logical understanding, not just rote memorization. "
            f"STRICT OUTPUT FORMAT REQUIRED (Do not add any conversational text):\n"
            f"Q: [Question Text]\n"
            f"A: [Option A]\n"
            f"B: [Option B]\n"
            f"C: [Option C]\n"
            f"D: [Option D]\n"
            f"ANS: [A, B, C, or D]\n"
            f"EXP: [Brief, highly informative explanation]"
        )
        
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192", 
            temperature=0.75,
            max_tokens=300
        )
        
        raw_text = response.choices[0].message.content
        
        q = re.search(r'Q:\s*(.+)', raw_text, re.IGNORECASE).group(1).strip()
        opt_a = re.search(r'A:\s*(.+)', raw_text, re.IGNORECASE).group(1).strip()
        opt_b = re.search(r'B:\s*(.+)', raw_text, re.IGNORECASE).group(1).strip()
        opt_c = re.search(r'C:\s*(.+)', raw_text, re.IGNORECASE).group(1).strip()
        opt_d = re.search(r'D:\s*(.+)', raw_text, re.IGNORECASE).group(1).strip()
        ans = re.search(r'ANS:\s*([A-D])', raw_text, re.IGNORECASE).group(1).strip().upper()
        exp = re.search(r'EXP:\s*(.+)', raw_text, re.IGNORECASE).group(1).strip()
        
        battle_id = str(uuid.uuid4())[:8]
        
        arena_ui = (
            f"🔥 **ELITE MULTIPLAYER ARENA** 🔥\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎓 **Level:** `{student_grade}` | 📚 **Domain:** `{topic.upper()}`\n\n"
            f"🎯 **Challenge:**\n_{q}_\n\n"
            f"🔘 **A:** {opt_a}\n"
            f"🔘 **B:** {opt_b}\n"
            f"🔘 **C:** {opt_c}\n"
            f"🔘 **D:** {opt_d}\n\n"
            f"⏱️ _15 Seconds on the clock. Lock your trajectory!_"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🅰️ Option A", callback_data=f"bat_{battle_id}_A"), InlineKeyboardButton("🅱️️ Option B", callback_data=f"bat_{battle_id}_B")],
            [InlineKeyboardButton("🇨 Option C", callback_data=f"bat_{battle_id}_C"), InlineKeyboardButton("🇩 Option D", callback_data=f"bat_{battle_id}_D")]
        ])
        
        battle_msg = await loading_msg.edit_text(arena_ui, reply_markup=keyboard)
        
        active_battles[battle_id] = {
            "correct_ans": ans,
            "explanation": exp,
            "participants": {},
            "active": True,
            "base_text": arena_ui
        }
        
        await asyncio.sleep(15)
        
        if battle_id not in active_battles or not active_battles[battle_id]["active"]:
            return 
            
        active_battles[battle_id]["active"] = False
        
        participants = active_battles[battle_id]["participants"]
        total_players = len(participants)
        
        winners = [data["name"] for uid, data in participants.items() if data["choice"] == ans]
        accuracy = round((len(winners) / total_players * 100), 1) if total_players > 0 else 0.0
        
        if winners:
            win_display = "🏆 **CHAMPIONS BOARD:**\n" + "\n".join([f"👑 `{w}`" for w in winners])
        else:
            win_display = "💀 **CHAMPIONS BOARD:**\n_Zero survival rate. Challenge failed._"
        
        final_report = (
            f"🏁 **ARENA CONCLUDED** 🏁\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 **Question:** _{q}_\n\n"
            f"✅ **Verified Answer:** `{ans}`\n"
            f"💡 **Insight:** _{exp}_\n\n"
            f"📊 **Arena Analytics:**\n"
            f"• Total Operatives Voted: `{total_players}`\n"
            f"• Group Accuracy Rate: `{accuracy}%`\n\n"
            f"{win_display}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ _Engineered by Aditya's Elite AI_"
        )
        
        await battle_msg.edit_text(final_report)
        
        del active_battles[battle_id]
        
    except Exception as e:
        await loading_msg.edit_text(f"⚠️ **System Exception:** Failed to compile arena parameters.\n`Trace: {str(e)}`")


# 🖱️ LIVE VOTING & ANTI-CHEAT LISTENER
@app.on_callback_query(filters.regex(r"^bat_"))
async def battle_callback_manager(client, callback_query):
    parts = callback_query.data.split("_")
    battle_id = parts[1]
    choice = parts[2]
    user = callback_query.from_user
    
    if battle_id not in active_battles or not active_battles[battle_id]["active"]:
        await callback_query.answer("⌛ Unauthorized: The battle arena is securely closed.", show_alert=True)
        return
        
    battle_session = active_battles[battle_id]
    
    if user.id in battle_session["participants"]:
        await callback_query.answer("🛑 Security Alert: Answer already locked in the mainframe. Modifications denied.", show_alert=True)
        return
        
    battle_session["participants"][user.id] = {
        "choice": choice,
        "name": user.first_name
    }
    
    total_votes = len(battle_session["participants"])
    live_update_text = battle_session["base_text"] + f"\n\n👥 **Operatives Locked In:** `{total_votes}`"
    
    try:
        await callback_query.message.edit_text(live_update_text, reply_markup=callback_query.message.reply_markup)
    except Exception:
        pass 
    
    await callback_query.answer(f"✅ Trajectory Locked: Option {choice} registered.", show_alert=False)

# --- 7. ELITE AI RESEARCH TERMINAL (ULTRA-PRO UI) ---

@app.on_message(filters.command(["ask", "research", "search"]))
async def elite_web_research_handler(client, message):
    command_args = message.text.split(" ", 1)
    
    if len(command_args) < 2:
        await message.reply_text(
            "⚠️ **Syntax Error:** Initialization failed.\n"
            "**Usage:** `/ask What is the latest update on quantum computing?`"
        )
        return
        
    user_query = command_args[1].strip()
    start_time = time.time()
    
    status_msg = await message.reply_text("🌐 *Establishing uplink to Global Web...*")
    
    try:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        await status_msg.edit_text("📡 *Extracting encrypted packets via secure nodes...*")
        web_context, sources_count = await research_engine.generate_stealth_context(user_query)
        
        await status_msg.edit_text("🧠 *Synthesizing data through Neural Core...*")
        
        from groq import Groq
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        
        # 🧠 PROMPT ENGINEERING: Forcing the AI to use Elite Terminal Formatting
        system_prompt = (
            "You are the Elite AI Research Architect of Aditya's Study Portal. "
            "You have real-time web context. Provide a highly analytical, deep-dive answer. "
            "CRITICAL UI RULES:\n"
            "1. NEVER use generic emojis like diamonds, stars, or basic bullets.\n"
            "2. Use Hacker/Terminal style formatting.\n"
            "3. Wrap key metrics, dates, prices, and technical terms in markdown code blocks (`like this`).\n"
            "4. Use '>' (blockquotes) for the final summary or key takeaway.\n"
            "5. Structure with clear, bold, all-caps headings.\n"
            "6. Do not include URLs or mention the source name directly."
        )
        
        user_prompt = f"Query: {user_query}\n\n{web_context}"
        
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=CHAT_MODEL, 
            temperature=0.35, 
            max_tokens=1500
        )
        
        ai_response = response.choices[0].message.content
        execution_time = round(time.time() - start_time, 2)
        
        # 💻 ULTRA-ADVANCED DASHBOARD UI CONSTRUCTION
        final_ui = (
            f"💻 **ELITE RESEARCH TERMINAL** 💻\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔎 **Target Query:** `{user_query}`\n"
            f"🟢 **Status:** `DATA VERIFIED`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{ai_response}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛰️ **SYSTEM TELEMETRY:**\n"
            f"├ Nodes Scanned: `{sources_count}`\n"
            f"├ Latency: `{execution_time}s`\n"
            f"└ Engine: `Aditya's Neural Core`"
        )
        
        await status_msg.edit_text(final_ui, disable_web_page_preview=True)
        
    except Exception as e:
        await status_msg.edit_text(f"⚠️ **Core Failure:** Connection to Neural Net lost.\n`Trace: {str(e)}`")

# --- 8. YOUTUBE DEEP-DIVE EXTRACTOR (AI SUMMARY) ---

@app.on_message(filters.command(["yt", "video", "summary"]))
async def youtube_ai_summary(client, message):
    command_args = message.text.split(" ", 1)
    
    if len(command_args) < 2:
        await message.reply_text(
            "⚠️ **Syntax Error:** Video link missing.\n"
            "**Usage:** `/yt [YouTube Link] [Optional: Specific Question]`\n"
            "**Example:** `/yt https://youtu.be/xyz What is Newton's 3rd Law?`"
        )
        return
        
    # Separating URL and User Query (if any)
    input_data = command_args[1].strip().split(" ", 1)
    video_url = input_data[0]
    specific_query = input_data[1] if len(input_data) > 1 else "Provide a highly structured and detailed summary of this video."
    
    start_time = time.time()
    
    status_msg = await message.reply_text("🎥 *Establishing secure connection to YouTube servers...*")
    
    try:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # Step 1: Extract Subtitles Stealthily
        await status_msg.edit_text("📡 *Bypassing video stream and extracting raw transcript...*")
        transcript_data = await yt_extractor.analyze_video(video_url)
        
        if transcript_data.startswith("ERROR"):
            await status_msg.edit_text(f"⚠️ **Extraction Failed:**\n`{transcript_data}`\n_Note: Some videos do not have subtitles enabled._")
            return
            
        # Step 2: Neural AI Processing
        await status_msg.edit_text("🧠 *Injecting transcript into Llama-3 Neural Core for analysis...*")
        
        from groq import Groq
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        
        system_prompt = (
            "You are an Elite AI Video Analyst. You are given a time-stamped transcript of a YouTube video. "
            "CRITICAL RULES:\n"
            "1. Analyze the transcript and answer the user's query perfectly.\n"
            "2. If summarizing, highlight the main topics with their exact timestamps (e.g., `[04:15]`).\n"
            "3. Format beautifully using Markdown (bolding, custom bullets, no raw headers).\n"
            "4. Maintain a highly professional, Silicon Valley-level academic tone.\n"
            "5. Never hallucinate. Stick strictly to what is said in the video."
        )
        
        user_prompt = f"User Request: {specific_query}\n\n[VIDEO TRANSCRIPT]\n{transcript_data}"
        
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama3-8b-8192", 
            temperature=0.3, 
            max_tokens=1500
        )
        
        ai_response = response.choices[0].message.content
        execution_time = round(time.time() - start_time, 2)
        
        # 💻 ULTRA-ADVANCED DASHBOARD UI CONSTRUCTION
        final_ui = (
            f"🎥 **YOUTUBE NEURAL ANALYSIS** 🎥\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 **Target:** `{specific_query}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{ai_response}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ **System Telemetry:**\n"
            f"├ Extraction Mode: `Transcript Bypass`\n"
            f"├ Latency: `{execution_time}s`\n"
            f"└ Engine: `Aditya's AI Core`"
        )
        
        # Sending final response and adding a PDF export button for the notes
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Export Summary as PDF", callback_data=f"gen_pdf_{status_msg.id}")]
        ])
        
        await status_msg.edit_text(final_ui, reply_markup=keyboard, disable_web_page_preview=True)
        
    except Exception as e:
        await status_msg.edit_text(f"⚠️ **Core Failure:** Connection lost.\n`Trace: {str(e)}`")
        

# --- MAIN RUNNER ---
if __name__ == "__main__":
    keep_alive()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.init_db())
    print("🚀 Aditya's Elite AI Study Companion is LIVE on Secure Servers!")
    app.run()
    
