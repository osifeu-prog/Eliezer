from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS, LOG_GROUP_ID, SUPPORT_GROUP_ID
from crm_manager import crm
from ai_service import ai_service
from qr_generator import generate_user_qr

# --- פונקציות עזר ---
async def notify_log_group(context, message):
    if LOG_GROUP_ID:
        try:
            await context.bot.send_message(chat_id=LOG_GROUP_ID, text=message)
        except Exception as e:
            print(f"Failed to log: {e}")

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = int(args[0]) if args and args[0].isdigit() else None
    
    # רישום ל-DB
    await crm.add_user(user.id, user.username, user.first_name, referred_by=referrer_id)
    
    # עדכון קבוצת לוגים
    log_msg = f"🔔 **משתמש חדש הצטרף!**\nשם: {user.first_name}\nID: {user.id}"
    if referrer_id:
        log_msg += f"\nהגיע דרך: {referrer_id}"
    await notify_log_group(context, log_msg)

    # תפריט ראשי
    keyboard = [
        [InlineKeyboardButton("🤖 צור QR שיתוף אישי", callback_data="get_qr")],
        [InlineKeyboardButton("💬 פנה לתמיכה", callback_data="support_req")],
        [InlineKeyboardButton("ℹ️ הסטטוס שלי", callback_data="my_status")]
    ]
    if user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🔒 פאנל ניהול", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"שלום {user.first_name}! אני הבוט החכם שלך.\nאני מחובר למערכת AI ומסוגל לעזור לך.",
        reply_markup=reply_markup
    )

async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # אם המשתמש במצב "תמיכה" (אפשר לשמור state ב-DB), נשלח לקבוצת תמיכה.
    # כרגע, נעשה ברירת מחדל: הודעות רגילות הולכות ל-AI.
    
    # שמירה ב-CRM
    await crm.log_interaction(user_id, user_text, source="user_msg")
    
    # קבלת תשובה מ-AI
    await update.message.reply_chat_action("typing")
    ai_response = await ai_service.get_response(user_text)
    
    await update.message.reply_text(ai_response)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data == "get_qr":
        # יצירת QR
        bot_username = context.bot.username
        qr_bio = generate_user_qr(bot_username, user.id)
        await query.message.reply_photo(photo=qr_bio, caption="זה קוד ה-QR האישי שלך!\nכל מי שיסרוק אותו יירשם תחתיך.")
    
    elif data == "support_req":
        text = f"🆘 **בקשת תמיכה חדשה**\nמאת: {user.first_name} ({user.id})\nיוזר: @{user.username}"
        if SUPPORT_GROUP_ID:
            await context.bot.send_message(chat_id=SUPPORT_GROUP_ID, text=text)
            await query.edit_message_text("הבקשה נשלחה לצוות התמיכה. ניצור איתך קשר בהקדם.")
        else:
            await query.edit_message_text("מערכת התמיכה אינה מוגדרת כרגע.")

    elif data == "my_status":
        count = await crm.get_referral_count(user.id)
        await query.edit_message_text(f"📊 הסטטוס שלך:\nאנשים שהצטרפו דרכך: {count}")

    elif data == "admin_panel":
        if user.id not in ADMIN_IDS:
            await query.edit_message_text("אין לך גישה.")
            return
        stats = await crm.get_referral_count(user.id) # סתם דוגמה, אפשר לשים סטטיסטיקות כלליות
        await query.edit_message_text(f"ברוך הבא אדמין.\nהבוט רץ ומחובר ל-DB.")

def create_bot_application():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # הודעות טקסט רגילות הולכות ל-AI (אלא אם זה בקבוצה והבוט לא תוייג, תלוי בהגדרות פרטיות)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_message))
    
    return application
