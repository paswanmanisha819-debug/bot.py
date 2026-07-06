import asyncio
import os
import json
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait
from pyrogram.enums import ParseMode  # यह लाइन पक्का सुनिश्चित करें[span_2](start_span)[span_2](end_span)

from groq import Groq

from config import API_ID, API_HASH, BOT_TOKEN, GEMINI_API_KEY, SYSTEM_PROMPT, QUIZ_PROMPT, TEMP_DIR
import database as db
from utils import generate_study_notes_pdf, safe_cleanup

# Initialize Google Gemini Configuration
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# Active Bot Session Client
app = Client("study_companion_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# In-Memory Cache for Active Quizzes and Simple Rate Limiting Tracking
ACTIVE_QUIZZES = {}
USER_COOLDOWNS = {}

# ----------------- MIDDLEWARES / DECORATORS -----------------
def rate_limiter():
    async def f(_, cb, update):
        user_id = update.from_user.id
        now = datetime.now()
        if user_id in USER_COOLDOWNS:
            if now < USER_COOLDOWNS[user_id]:
                if isinstance(update, Message):
                    await update.reply_text("âš ï¸ *Oye! Chill karo.* Please wait a few seconds before asking the next question.")
                return False
        USER_COOLDOWNS[user_id] = now + timedelta(seconds=2)
        return True
    return filters.create(f)

# ----------------- BASE HANDLERS & ONBOARDING -----------------
# ----------------- BASE HANDLERS & ONBOARDING -----------------
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Student"

    await db.create_or_update_user(user_id, username)

    welcome_text = (
        f"👋 *Namaste {username}!* Welcome to your personal **Local AI Study Companion**! 🚀\n\n"
        "Main aapka personal digital tutor hoon for Classes 9th-12th. I can solve tough Math proofs, "
        "explain deep Science concepts, take interactive tests, and create PDF notes dynamically.\n\n"
        "Chalo, first let me know your **Class** standard 👇"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Class 9", callback_data="set_class_9th"), InlineKeyboardButton("Class 10", callback_data="set_class_10th")],
        [InlineKeyboardButton("Class 11", callback_data="set_class_11th"), InlineKeyboardButton("Class 12", callback_data="set_class_12th")]
    ])

    await message.reply_text(welcome_text, reply_markup=keyboard)
    

# ----------------- OWNER INFO COMMAND -----------------
@app.on_message(filters.command("owner") & filters.private)
async def owner_info(client: Client, message: Message):
    owner_text = (
        "👤 **Developer Info**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎓 **Name:** Aditya (Adit Kumar)\n"
        "💻 **Role:** Software Developer & AI Enthusiast\n"
        "🚀 **Project:** Local AI Study Companion\n\n"
        "✨ *This bot is proudly developed by Aditya to help students excel in their studies.*"
    )
                                                            
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Follow me on Instagram", url="https://www.instagram.com/aadit_paswan.007?igsh=MW93ZGJvaGVwNGNlNg==")],
        [InlineKeyboardButton("💬 Message me on Telegram", url="https://t.me/your_telegram_username")]
    ])

                                                                                        
    await message.reply_text(owner_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    
    

@app.on_callback_query(filters.regex(r"^set_class_"))
async def set_class_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    selected_class = callback_query.data.split("_")[2]

    await db.create_or_update_user(user_id, username)

    welcome_text = (
        f"👋 *Namaste {username}!* Welcome to your personal **Local AI Study Companion**! 🚀\n\n"
        "Main aapka personal digital tutor hoon for Classes 9th-12th. I can solve tough Math proofs, "
        "explain deep Science concepts, take interactive tests, and create PDF notes dynamically.\n\n"
        "Chalo, first let me know your **Class** standard 👇"
    )

    keyboard = InlineKeyboardMarkup([
        
    await callback_query.message.edit_text(
        f"🎯 Excellent! Selected **Class {selected_class[:-2]}**.\nNow select your educational board:",
        reply_markup=board_keyboard
        )

@app.on_callback_query(filters.regex(r"^set_board_"))
async def set_board_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    parts = callback_query.data.split("_")
    selected_class = parts[2]
    selected_board = parts[3]

    await db.create_or_update_user(user_id, callback_query.from_user.username, board=selected_board)

        await callback_query.message.edit_text(
        f"✅ Setup Complete!\n\n🎓 *Class:* {selected_class[:-2]}th\n🏛️ *Board:* {selected_board}\n\n"
        "Ab aap ready hain! Mujhse koi bhi question pucho: \n"
        "• Type text doubts directly.\n"
        "• Send a **Photo** of a diagram or numerical question.\n"
        "• Send a **Voice Note** explaining your question!\n\n"
        "Try calling `/quiz` to take a quick multi-choice mock evaluation!"
        )


# ----------------- CORE AI CORE EXECUTION -----------------
@app.on_message(filters.text & filters.private & rate_limiter())
async def handle_text_doubt(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)

    if not user_data or not user_data.student_class:
        return await message.reply_text("âš ï¸ Please run `/start` first to complete your class setup configuration.")

    processing_msg = await message.reply_text("ðŸ”„ *Thinking... Aapke liye detail answer ready ho raha hai...*")

    # Extract Conversation Logs
    context_history = await db.get_recent_context(user_id, limit=6)

    # Inject current parameters dynamically
    current_prompt = f"[Context: Student in Class {user_data.student_class}, Board: {user_data.board}]\nQuestion: {message.text}"
    context_history.append({"role": "user", "parts": [current_prompt]})
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": current_prompt}
            ],
            model="openai/gpt-oss-120b",
        )
        ai_response = chat_completion.choices[0].message.content
            

        # Save structural states to DB
        await db.log_conversation(user_id, "user", message.text)
        await db.log_conversation(user_id, "model", ai_response)

        # Actionable inline buttons
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("ðŸ“¥ Download Notes as PDF", callback_data=f"gen_pdf_{message.id}")]
        ])

        await processing_msg.delete()
        await message.reply_text(ai_response, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
    except Exception as e:
        await processing_msg.edit_text("âŒ Sorry, standard query channels are busy right now. Please try again in a few minutes.")
      
        print(f"असली एरर यह है: {e}")
        await processing_msg.edit_text(f"❌ Error: {str(e)}")

# ----------------- MULTIMODAL INPUTS HANDLING -----------------
@app.on_message(filters.photo & filters.private & rate_limiter())
async def handle_photo_doubt(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)

    processing_msg = await message.reply_text("🔍¸*Scanning Image via Vision Engine... Step-by-step resolution ready ho rahi hai.*")

    # Download Photo safely
    local_img_path = await message.download(file_name=os.path.join(TEMP_DIR, f"img_{user_id}.jpg"))

    try:
        from PIL import Image
        img = Image.open(local_img_path)

        caption = message.caption or "Explain this problem or diagram cleanly."
        composed_query = [
            f"You are tutoring a Class {user_data.student_class} ({user_data.board} Board) student. Detail out everything inside this image: {caption}",
            img
        ]

        # Employing Gemini 1.5 Pro for rich multi-modal spatial reasoning
        response = await asyncio.to_thread(pro_model.generate_content, composed_query)
        ai_response = response.text

        await db.log_conversation(user_id, "user", f"[Sent Photo] {caption}")
        await db.log_conversation(user_id, "model", ai_response)

                # Actionable inline buttons
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Download Notes as PDF", callback_data=f"gen_pdf_{message.id}")]
        ])


        await processing_msg.delete()
        await message.reply_text(ai_response, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


    except Exception as e:
        await processing_msg.edit_text("âŒ Image analysis failed. Ensure the text/diagram is clear and well-lit.")
    finally:
        safe_cleanup(local_img_path)

# ----------------- VOICE PIPELINE HANDLING -----------------
@app.on_message(filters.voice & filters.private & rate_limiter())
async def handle_voice_doubt(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)

    processing_msg = await message.reply_text("ðŸŽ™ï¸ *Listening closely... Transcribing and formulating solution.*")

    # Download voice path (.ogg format standard across telegram architecture)
    local_voice_path = await message.download(file_name=os.path.join(TEMP_DIR, f"voice_{user_id}.ogg"))

    try:
        # Gemini 1.5 natively supports direct parsing of audio data
        uploaded_audio = await asyncio.to_thread(genai.upload_file, path=local_voice_path, mime_type="audio/ogg")

        composed_query = [
            f"Listen to this student's query. They are in Class {user_data.student_class} ({user_data.board} Board). Provide a fully structured breakdown.",
            uploaded_audio
        ]

        response = await asyncio.to_thread(flash_model.generate_content, composed_query)
        ai_response = response.text

        await db.log_conversation(user_id, "user", "[Sent Voice Doubt]")
        await db.log_conversation(user_id, "model", ai_response)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("ðŸ“¥ Download Notes as PDF", callback_data=f"gen_pdf_{message.id}")]
        ])

        await processing_msg.delete()
        await message.reply_text(ai_response, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


        # Clean up Gemini system file manager cloud storage record
        await asyncio.to_thread(uploaded_audio.delete)

    except Exception as e:
        await processing_msg.edit_text("âŒ Audio processing failed. Please talk clearly or type out your doubt instead.")
    finally:
        safe_cleanup(local_voice_path)

# ----------------- DYNAMIC QUIZ GENERATOR -----------------
@app.on_message(filters.command("quiz") & filters.private)
async def generate_quiz_command(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)

    subject = "Science/Math"
    if len(message.command) > 1:
        subject = " ".join(message.command[1:])

    processing_msg = await message.reply_text(f"ðŸ“ *Generating a customized 3-Question Quiz on '{subject}'...*")

    formatted_prompt = QUIZ_PROMPT.format(student_class=user_data.student_class, board=user_data.board)
    full_query = f"{formatted_prompt}\nTopic requested by user: {subject}"

    try:
        response = await asyncio.to_thread(flash_model.generate_content, full_query)
        raw_json = response.text.strip().replace("```json", "").replace("```", "")
        quiz_data = json.loads(raw_json)

        # Save metadata to track active question state metrics
        ACTIVE_QUIZZES[user_id] = {
            "questions": quiz_data["questions"],
            "current_index": 0,
            "score": 0,
            "subject": subject
        }

        await processing_msg.delete()
        await send_next_quiz_question(client, user_id, message.chat.id)

    except Exception as e:
        await processing_msg.edit_text("âŒ AI Quiz execution dropped due to a structural rendering mismatch. Try again via `/quiz Physics` style.")

async def send_next_quiz_question(client: Client, user_id: int, chat_id: int):
    quiz = ACTIVE_QUIZZES.get(user_id)
    idx = quiz["current_index"]
    q_data = quiz["questions"][idx]

    text = f"ðŸ“Š *Question {idx + 1}/3:*\n\n{q_data['question']}"

    buttons = []
    for o_idx, option in enumerate(q_data["options"]):
        buttons.append([InlineKeyboardButton(option, callback_data=f"quiz_ans_{o_idx}")])

    keyboard = InlineKeyboardMarkup(buttons)
    await app.send_message(chat_id, text, reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"^quiz_ans_"))
async def handle_quiz_answer(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    quiz = ACTIVE_QUIZZES.get(user_id)

    if not quiz:
        return await callback_query.answer("No active session found.", show_alert=True)

    selected_idx = int(callback_query.data.split("_")[2])
    idx = quiz["current_index"]
    correct_idx = quiz["questions"][idx]["correct_index"]

    if selected_idx == correct_idx:
        quiz["score"] += 1
        feedback = "âœ… *Sahi Jawaab! Brilliant.*"
    else:
        actual_ans = quiz["questions"][idx]["options"][correct_idx]
        feedback = f"âŒ *Galat Answer.* Correct option was: **{actual_ans}**"

    await callback_query.message.edit_text(f"{callback_query.message.text}\n\n{feedback}")

    quiz["current_index"] += 1
    if quiz["current_index"] < 3:
        await send_next_quiz_question(app, user_id, callback_query.message.chat.id)
    else:
        # Out of bounds - End evaluation telemetry reporting
        final_score = quiz["score"]
        await db.save_quiz_stat(user_id, quiz["subject"], final_score)
        await app.send_message(
            callback_query.message.chat.id,
            f"ðŸ *Quiz Complete!* \nYour Final Score: **{final_score}/3**\n"
            f"{'Excellent preparation! Keep it up!' if final_score >= 2 else 'Koi baat nahi! Dubara padhein aur try karein.'}"
        )
        del ACTIVE_QUIZZES[user_id]

# ----------------- PDF CONVERSION CALL PIPELINE -----------------
@app.on_callback_query(filters.regex(r"^gen_pdf_"))
async def handle_pdf_generation(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    await callback_query.answer("Generating PDF... Please wait.")

    # Retrieve the text description immediately contextually above the clicked button layout
    text_content = callback_query.message.text
    topic_header = text_content[:30] + "..." if len(text_content) > 30 else text_content

    pdf_path = None
    try:
        # Run CPU heavy operations thread safe without blocking main execution
        pdf_path = await asyncio.to_thread(generate_study_notes_pdf, user_id, topic_header, text_content)

        await app.send_document (
            chat_id=callback_query.message.chat.id,
            document=pdf_path,
            caption="ðŸ“š Here are your formatted compilation notes. All the best for your preparation!"
        )
    except Exception as e:
        await app.send_message(callback_query.message.chat.id, "âŒ Verification failed while packing the document layout engine.")
    finally:
        if pdf_path:
            safe_cleanup(pdf_path)

# ----------------- MAIN APP RUNNER -----------------
if __name__ == "__main__":
    # Initialize connection pooling and migrate SQLite tables
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.init_db())

    print("ðŸ¤– Local AI Study Companion bot is live and running...")
    app.run()
