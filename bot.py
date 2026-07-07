import asyncio
import os
import json
import base64

from datetime import datetime, timedelta
from features import get_ai_generated_quiz
from features import get_ai_generated_quiz, client
from pyrogram import StopPropagation
from features import get_ai_generated_quiz_from_image

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
@app.on_message(filters.command("start"))
async def start_command(client_bot, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Ask a Doubt", callback_data="help_doubt"), 
         InlineKeyboardButton("🧠 Take a Quiz", callback_data="show_classes")]
    ])
    await message.reply_text("👋 Welcome to AI Study Bot!\n\nChoose what you want to do:", reply_markup=keyboard)

@app.on_callback_query(filters.regex("help_doubt"))
async def help_doubt_handler(client_bot, callback_query):
    await callback_query.message.edit_text("💡 *Ask your doubt!*\n\nJust type a `` before your question.\nExample: ` What is motion`")


    
    await callback_query.message.edit_text("Select your class for the Quiz:", reply_markup=keyboard)
                              
# --- 2. BUTTON CLICK HANDLER FOR IMAGE QUIZ ---
@app.on_callback_query(filters.regex(r"^imgquiz_"))
async def imgquiz_callback(client_bot, callback_query):
    # बटन दबाते ही लोडिंग मैसेज
    await callback_query.answer("Generating Quiz... Please wait! 🧠")
    await callback_query.message.edit_text("⏳ *Creating Quiz from your Image...*")
    
    try:
        # बटन के छिपे हुए डेटा से पुरानी फोटो की ID निकालना
        msg_id = int(callback_query.data.split("_")[1])
        
        # टेलीग्राम से वो पुरानी फोटो वापस मंगाना
        orig_msg = await client_bot.get_messages(callback_query.message.chat.id, msg_id)
        
        image_path = await orig_msg.download()
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
        # तुम्हारा features.py वाला क्विज़ जनरेटर फंक्शन कॉल करना
        quiz_content = get_ai_generated_quiz_from_image(base64_image)
        
        final_reply = (
            f"🧠 **Image-Based AI Quiz**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{quiz_content}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 *Developed by Aditya*"
        )
        
        # पुराना मैसेज हटाकर नया क्विज़ दिखा देना
        await callback_query.message.edit_text(final_reply)
        
        if os.path.exists(image_path):
            os.remove(image_path)
            
    except Exception as e:
        await callback_query.message.edit_text(f"⚠️ *Quiz Error:* `{str(e)}`")

    

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

    await db.create_or_update_user(user_id, callback_query.from_user.username, student_class=selected_class)

    board_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("CBSE Board", callback_data=f"set_board_{selected_class}_CBSE")],
        [InlineKeyboardButton("State Board / Other", callback_data=f"set_board_{selected_class}_State")]
    ])

    await callback_query.message.edit_text(
        f"🎯 Excellent! Selected **Class {selected_class[:-2]}**.\nNow select your educational board:",
        reply_markup=board_keyboard
    )
    

        
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


    processing_msg = await message.reply_text("🤔”„ *Thinking... Aapke liye detail answer ready ho raha hai...*")

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
@app.on_message(filters.voice)
async def voice_handler(client_bot, message):
    msg = await message.reply_text("🎧 तुम्हारी आवाज़ सुन रहा हूँ... ⏳")
    audio_path = None
    
    try:
        # 1. Telegram से ऑडियो फाइल डाउनलोड करना
        audio_path = await message.download()
        
        # 2. Groq Whisper API से आवाज़ को टेक्स्ट में बदलना
        with open(audio_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
              file=(audio_path, file.read()), # फाइल को रीड करके भेजना
              model="whisper-large-v3",       # Groq का ऑडियो मॉडल
              response_format="text"
            )
        
        user_question = transcription.strip()
        
        # अगर आवाज़ खाली हो या शोर हो
        if not user_question:
            await msg.edit_text("⚠️ मुझे कुछ सुनाई नहीं दिया। कृपया थोड़ा तेज़ बोलें!")
            return

        await msg.edit_text(f"🗣️ *तुम्हारा सवाल:* {user_question}\n\n🧠 जवाब ढूँढ रहा हूँ...")
        
        # 3. LLaMA मॉडल से जवाब मंगाना (तुम्हारे डेवलपर टैग के साथ)
        system_instruction = (
            "You are a highly advanced AI Study Companion. "
            "You were created and developed by a brilliant developer named Aditya."
        )
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_question}
            ],
            model="llama-3.1-8b-instant",
        )
        answer = chat_completion.choices[0].message.content
        
        # 4. फाइनल शानदार रिप्लाई
        advanced_reply = (
            f"🗣️ *सवाल:* {user_question}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{answer}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 *Developed by Aditya*"
        )
        
        await msg.edit_text(advanced_reply)
        
    except Exception as e:
        # असली एरर देखने के लिए
        await msg.edit_text(f"⚠️ Audio Error: `{str(e)}`")
        
    finally:
        # 5. मेमोरी बचाने के लिए ऑडियो फाइल को सर्वर से डिलीट करना
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
    
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
            f"✅ *Quiz Complete!* \nYour Final Score: **{final_score}/3**\n"
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

@app.on_callback_query(filters.regex(r"^quiz_"))
async def quiz_handler(client, callback_query):
    student_class = callback_query.data.split("_")[1]
    await callback_query.answer("Generating AI Question...")
    question = get_ai_generated_quiz(student_class)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 New Question", callback_data=f"quiz_{student_class}")]
    ])
    await callback_query.message.edit_text(f"🧠 *AI Quiz ({student_class})*\n\n{question}", reply_markup=keyboard)
# पुराने हैंडलर में बस 'group=1' जोड़ दो
@app.on_message(filters.text & ~filters.command(["start", "quiz", "owner", "ask"]))
async def advanced_question_handler(client_bot, message):
    question = message.text.strip()
    
    # 1. एडवांस 'Thinking' मैसेज
    msg = await message.reply_text("🔍 *Scanning Knowledge Base... Please wait!* ⏳")
    
    # 2. AI को बताना कि उसका मालिक (Owner) कौन है!
    system_instruction = (
        "You are a highly advanced AI Study Companion. "
        "You were created and developed by a brilliant developer named Aditya. "
        "If anyone asks who made you, created you, or who your owner is, answer with pride that Aditya made you. "
        "Keep your educational answers well-formatted, professional, and easy for students to understand."
    )
    
    try:
        # AI को System Instruction और User Question दोनों भेज रहे हैं
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": question}
            ],
            model="llama-3.2-11b-vision-preview",
            
        )
        answer = chat_completion.choices[0].message.content
        
        # 3. प्रीमियम और एडवांस UI डिज़ाइन
        advanced_reply = (
            f"🎓 **AI Study Companion**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{answer}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 *Developed by Aadit*"
        )
        
        await msg.edit_text(advanced_reply)
        
    except Exception as e:
        await msg.edit_text(f"⚠️ *API Error (Screenshot भेजो):*\n`{str(e)}`")



# --- 1. SMART IMAGE VISION HANDLER (Premium UI) ---
@app.on_message(filters.photo)
async def vision_handler(client_bot, message):
    user_question = message.caption if message.caption else "Explain this image/diagram clearly for a 9th grade student."
    
    msg = await message.reply_text("🔍 *Scanning Image & Finding Answer...* ⏳")
    image_path = None
    
    try:
        image_path = await message.download()
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        # 🌟 प्रॉम्प्ट अपडेट: AI को बताया कि UI के लिए # का इस्तेमाल न करे
        ai_prompt = (
            f"Answer concisely. IMPORTANT FOR TELEGRAM UI: Do NOT use markdown headers like #, ##, or ###. "
            f"Use **bold text** for headings and standard bullet points. Question: {user_question}"
        )

        chat_completion = client.chat.completions.create(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": ai_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )
        answer = chat_completion.choices[0].message.content
        
        # 🌟 Python Magic: बचे-खुचे कचरे (###) को सुंदर डिज़ाइन में बदलना
        answer = answer.replace("### ", "🔹 ").replace("## ", "🔸 ").replace("# ", "🎯 ")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🧠 Generate Quiz from this Image", callback_data=f"imgquiz_{message.id}")]
        ])
        
        advanced_reply = (
            f"🖼️ **Image Analysis**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{answer}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 *Developed by Aditya*"
        )
        
        await msg.edit_text(advanced_reply, reply_markup=keyboard)
        
    except Exception as e:
        await msg.edit_text(f"⚠️ *Vision Error:* `{str(e)}`")
        
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)

# --- नया स्मार्ट प्रोफाइल सेटअप (इसे यहाँ पेस्ट करें) ---
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

user_profiles = {}

@app.on_message(filters.command("setup") | filters.command("start"))
async def setup_profile(client_bot, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("9th Class", callback_data="setclass_9"), InlineKeyboardButton("10th Class", callback_data="setclass_10")],
        [InlineKeyboardButton("11th Class", callback_data="setclass_11"), InlineKeyboardButton("12th Class", callback_data="setclass_12")]
    ])
    await message.reply_text("🎓 **Welcome to AI Study Bot!**\n\nसबसे पहले अपनी क्लास सिलेक्ट करो:", reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"^setclass_"))
async def select_subject_for_profile(client_bot, callback_query):
    grade = callback_query.data.split("_")[1]
    subjects = {
        "9": ["Science", "Maths", "English"],
        "10": ["Science", "Maths", "SST"],
        "11": ["Physics", "Chemistry", "Biology", "Maths"],
        "12": ["Physics", "Chemistry", "Biology", "Maths"]
    }
    buttons = []
    row = []
    for sub in subjects.get(grade, []):
        row.append(InlineKeyboardButton(sub, callback_data=f"setsub_{grade}_{sub}"))
        if len(row) == 2:
            buttons.append(row); row = []
    if row: buttons.append(row)
    await callback_query.message.edit_text(f"📚 **Class {grade}th** - अब अपना सब्जेक्ट चुनो:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^setsub_"))
async def save_profile(client_bot, callback_query):
    data = callback_query.data.split("_")
    user_profiles[callback_query.from_user.id] = {"class": data[1], "subject": data[2]}
    await callback_query.message.edit_text(f"✅ **Setup Complete!**\n\nप्रोफ़ाइल **Class {data[1]}th - {data[2]}** सेट हो गई है।")

@app.on_message(filters.text & ~filters.command(["start", "setup", "owner"]))
async def smart_doubt_solver(client_bot, message):
    user_id = message.from_user.id
    if user_id not in user_profiles:
        await message.reply_text("⚠️ प्लीज़ पहले `/setup` दबाकर अपनी क्लास और सब्जेक्ट चुनो!"); return
    
    u = user_profiles[user_id]
    msg = await message.reply_text(f"🔍 *Searching for {u['class']}th {u['subject']}...*")
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": f"Answer for {u['class']}th {u['subject']}: {message.text}"}],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )
        await msg.edit_text(f"🎓 **{u['class']}th {u['subject']}**\n\n{chat_completion.choices[0].message.content}")
    except Exception as e:
        await msg.edit_text(f"⚠️ *Error:* `{str(e)}`")
                              
        
    

# --- यहाँ से नया "स्मार्ट प्रोफाइल सेटअप" कोड पेस्ट करें ---
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

user_profiles = {}

@app.on_message(filters.command("setup") | filters.command("start"))
async def setup_profile(client_bot, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("9th Class", callback_data="setclass_9"), InlineKeyboardButton("10th Class", callback_data="setclass_10")],
        [InlineKeyboardButton("11th Class", callback_data="setclass_11"), InlineKeyboardButton("12th Class", callback_data="setclass_12")]
    ])
    await message.reply_text("🎓 **Welcome to AI Study Bot!**\n\nसबसे पहले अपनी क्लास सिलेक्ट करो:", reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"^setclass_"))
async def select_subject_for_profile(client_bot, callback_query):
    grade = callback_query.data.split("_")[1]
    subjects = {
        "9": ["Science", "Maths", "English"],
        "10": ["Science", "Maths", "SST"],
        "11": ["Physics", "Chemistry", "Biology", "Maths"],
        "12": ["Physics", "Chemistry", "Biology", "Maths"]
    }
    buttons = []
    row = []
    for sub in subjects.get(grade, []):
        row.append(InlineKeyboardButton(sub, callback_data=f"setsub_{grade}_{sub}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    await callback_query.message.edit_text(f"📚 **Class {grade}th** - अब अपना सब्जेक्ट चुनो:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^setsub_"))
async def save_profile(client_bot, callback_query):
    data = callback_query.data.split("_")
    user_profiles[callback_query.from_user.id] = {"class": data[1], "subject": data[2]}
    await callback_query.message.edit_text(f"✅ **Setup Complete!**\n\nप्रोफ़ाइल **Class {data[1]}th - {data[2]}** सेट हो गई है। अब कोई भी सवाल पूछो!")

@app.on_message(filters.text & ~filters.command(["start", "setup", "owner"]))
async def smart_doubt_solver(client_bot, message):
    user_id = message.from_user.id
    if user_id not in user_profiles:
        await message.reply_text("⚠️ प्लीज़ पहले `/setup` दबाकर अपनी क्लास और सब्जेक्ट चुनो!")
        return
    
    # [बाकी का AI Logic यहाँ पेस्ट करें जो मैंने पिछली बार बताया था]
        
        

# --- 2. VOICE NOTE (वॉइस टू टेक्स्ट) ---
@app.on_message(filters.voice)
async def voice_handler(client_bot, message):
    msg = await message.reply_text("🎧 Listening to your voice...")
    try:
        file = await message.download()
        # यहाँ Groq 'whisper' मॉडल का इस्तेमाल करके ऑडियो को टेक्स्ट में बदलेंगे
        await msg.edit_text("✅ *Audio Transcribed!* (वॉइस फीचर एक्टिवेट हो गया है)")
    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {str(e)}")

# --- 3. EASTER EGG (/space कमांड) ---
@app.on_message(filters.command("space"))
async def space_handler(client_bot, message):
    space_facts = [
        "Did you know? A day on Venus is longer than a year on Venus! 🪐",
        "Space is completely silent, there's no atmosphere to carry sound. 🌌",
        "There are more stars in the universe than grains of sand on all Earth's beaches. ✨"
    ]
    await message.reply_text(random.choice(space_facts))
           


# ----------------- MAIN APP RUNNER -----------------
if __name__ == "__main__":
    # Initialize connection pooling and migrate SQLite tables
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.init_db())

    print("😊– Local AI Study Companion bot is live and running...")
    app.run()
