import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import asyncio

# ===== CONFIGURATION =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== ENVIRONMENT VARIABLES =====
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
RAILWAY_URL = os.getenv("RAILWAY_URL", "https://fun-production-8132.up.railway.app")
WEBHOOK_URL = f"{RAILWAY_URL}{WEBHOOK_PATH}"
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Validate required environment variables
if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN environment variable is required")
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

if not RAILWAY_URL:
    logger.error("❌ RAILWAY_URL environment variable is required")
    raise ValueError("RAILWAY_URL environment variable is required")

logger.info("✅ Environment variables loaded successfully")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# In-memory storage (use a real database in production)
leads = []
active_users = set()

class CRMStates(StatesGroup):
    waiting_for_lead_name = State()
    waiting_for_lead_phone = State()

# ===== LIFESPAN MANAGER =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("🚀 Starting Telegram CRM Bot...")
    
    try:
        # Delete any existing webhook
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Existing webhook deleted")
        
        # Set new webhook
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        logger.info(f"✅ Webhook set to: {WEBHOOK_URL}")
        
        # Verify webhook
        webhook_info = await bot.get_webhook_info()
        logger.info(f"📋 Webhook info: {webhook_info.url}")
        logger.info(f"📊 Pending updates: {webhook_info.pending_update_count}")
        
        # Verify bot
        bot_info = await bot.get_me()
        logger.info(f"🤖 Bot info: @{bot_info.username}")
        
        logger.info("🎉 Bot startup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down bot...")
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

# ===== UTILITY FUNCTIONS =====
async def safe_send_message(chat_id: int, text: str, **kwargs):
    """Send message with error handling"""
    try:
        await bot.send_message(chat_id, text, **kwargs)
        return True
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        return False

# ===== TELEGRAM HANDLERS =====
@dp.message(CommandStart())
async def handle_start(message: Message):
    """Handle /start command"""
    try:
        user_id = message.from_user.id
        active_users.add(user_id)
        
        logger.info(f"👤 User {user_id} started the bot")
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 View Leads", callback_data="view_leads")],
            [InlineKeyboardButton(text="📈 Statistics", callback_data="view_stats")],
            [InlineKeyboardButton(text="👥 Add Lead", callback_data="add_lead")],
            [InlineKeyboardButton(text="🔧 System Info", callback_data="system_info")]
        ])
        
        welcome_text = (
            f"👋 Hello {message.from_user.first_name}!\n\n"
            "🤖 **CRM Bot for Advertising Agency**\n\n"
            "✅ **System is active and ready!**\n"
            "📞 Automatic lead management from website\n"
            "📈 Real-time statistics tracking\n"
            "🔔 Instant notifications for new leads\n\n"
            "**Choose an action:**"
        )
        
        await message.answer(welcome_text, reply_markup=keyboard)
        logger.info(f"✅ Welcome message sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer("❌ An error occurred. Please try again.")

@dp.message(Command("help"))
async def handle_help(message: Message):
    """Handle /help command"""
    help_text = (
        "🤖 **CRM Bot - Help Guide**\n\n"
        "**Available commands:**\n"
        "/start - Main menu\n"
        "/leads - Show recent leads\n"
        "/stats - Show statistics\n"
        "/help - This guide\n\n"
        "**Website integration:**\n"
        "The bot receives leads automatically via webhook at:\n"
        "`POST /webhook/lead`\n\n"
        "**Support:**\n"
        "For technical issues, contact the administrator."
    )
    
    await message.answer(help_text)

@dp.message(Command("leads"))
async def handle_leads(message: Message):
    """Handle /leads command"""
    try:
        if not leads:
            await message.answer("📝 No leads available.")
            return
        
        leads_text = "📋 **Recent Leads:**\n\n"
        for i, lead in enumerate(leads[-5:], 1):
            leads_text += f"{i}. **{lead['name']}**\n"
            leads_text += f"   📞 {lead['phone']}\n"
            leads_text += f"   📅 {lead['date']}\n"
            if lead.get('source'):
                leads_text += f"   🌐 {lead['source']}\n"
            leads_text += "─" * 20 + "\n"
        
        await message.answer(leads_text)
        
    except Exception as e:
        logger.error(f"Error showing leads: {e}")
        await message.answer("❌ Error displaying leads.")

@dp.message(Command("stats"))
async def handle_stats(message: Message):
    """Handle /stats command"""
    try:
        total_leads = len(leads)
        today = datetime.now().strftime('%d/%m/%Y')
        today_leads = len([lead for lead in leads if lead['date'].startswith(today)])
        
        stats_text = (
            "📊 **CRM Statistics:**\n\n"
            f"👥 **Total Leads:** {total_leads}\n"
            f"📈 **Leads Today:** {today_leads}\n"
            f"👤 **Active Users:** {len(active_users)}\n"
            f"🟢 **System:** Active\n"
            f"🌐 **Webhook:** Configured\n"
        )
        
        await message.answer(stats_text)
        
    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        await message.answer("❌ Error displaying statistics.")

@dp.callback_query(F.data == "view_leads")
async def handle_view_leads(callback: types.CallbackQuery):
    """Handle view leads button"""
    try:
        if not leads:
            await callback.message.edit_text("📝 No leads available.")
            await callback.answer()
            return
        
        leads_text = "📋 **Recent Leads:**\n\n"
        for i, lead in enumerate(leads[-3:], 1):
            leads_text += f"{i}. **{lead['name']}** - {lead['phone']}\n"
        
        await callback.message.edit_text(leads_text)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in view_leads callback: {e}")
        await callback.answer("❌ Error displaying leads", show_alert=True)

@dp.callback_query(F.data == "view_stats")
async def handle_view_stats(callback: types.CallbackQuery):
    """Handle view stats button"""
    try:
        total_leads = len(leads)
        today = datetime.now().strftime('%d/%m/%Y')
        today_leads = len([lead for lead in leads if lead['date'].startswith(today)])
        
        stats_text = (
            "📊 **Statistics:**\n\n"
            f"📋 Total Leads: {total_leads}\n"
            f"📈 Today: {today_leads}\n"
            f"👥 Users: {len(active_users)}\n"
            f"🟢 Status: Active\n"
        )
        
        await callback.message.edit_text(stats_text)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in view_stats callback: {e}")
        await callback.answer("❌ Error displaying statistics", show_alert=True)

@dp.callback_query(F.data == "add_lead")
async def handle_add_lead(callback: types.CallbackQuery, state: FSMContext):
    """Handle add lead button"""
    try:
        await callback.message.edit_text("👤 Please enter the customer's name:")
        await state.set_state(CRMStates.waiting_for_lead_name)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in add_lead callback: {e}")
        await callback.answer("❌ Error adding lead", show_alert=True)

@dp.callback_query(F.data == "system_info")
async def handle_system_info(callback: types.CallbackQuery):
    """Handle system info button"""
    try:
        webhook_info = await bot.get_webhook_info()
        
        info_text = (
            "🔧 **System Information:**\n\n"
            f"🤖 **Bot:** Active\n"
            f"🌐 **Webhook:** {webhook_info.url or 'Not set'}\n"
            f"⏳ **Pending Updates:** {webhook_info.pending_update_count}\n"
            f"👥 **Active Users:** {len(active_users)}\n"
            f"📋 **Total Leads:** {len(leads)}\n"
            f"🟢 **Status:** Operational\n"
        )
        
        await callback.message.edit_text(info_text)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in system_info callback: {e}")
        await callback.answer("❌ Error getting system info", show_alert=True)

@dp.message(CRMStates.waiting_for_lead_name)
async def handle_lead_name(message: Message, state: FSMContext):
    """Handle lead name input"""
    try:
        await state.update_data(lead_name=message.text)
        await message.answer("📞 Please enter the customer's phone number:")
        await state.set_state(CRMStates.waiting_for_lead_phone)
        
    except Exception as e:
        logger.error(f"Error handling lead name: {e}")
        await message.answer("❌ Error saving name. Please try again:")

@dp.message(CRMStates.waiting_for_lead_phone)
async def handle_lead_phone(message: Message, state: FSMContext):
    """Handle lead phone input"""
    try:
        data = await state.get_data()
        lead_name = data.get('lead_name')
        lead_phone = message.text
        
        # Create new lead
        new_lead = {
            'name': lead_name,
            'phone': lead_phone,
            'date': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'source': 'telegram_bot'
        }
        leads.append(new_lead)
        
        # Send confirmation
        await message.answer(
            f"✅ **Lead added successfully!**\n\n"
            f"**Name:** {lead_name}\n"
            f"**Phone:** {lead_phone}\n"
            f"**Date:** {new_lead['date']}"
        )
        
        # Notify other users
        notification_text = (
            f"👤 **New Lead Added!**\n\n"
            f"**Name:** {lead_name}\n"
            f"**Phone:** {lead_phone}\n"
            f"**Added by:** {message.from_user.first_name}\n"
            f"**Date:** {new_lead['date']}"
        )
        
        # Send to all active users except the one who added
        for user_id in active_users:
            if user_id != message.from_user.id:
                await safe_send_message(user_id, notification_text)
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error handling lead phone: {e}")
        await message.answer("❌ Error saving lead. Please try again.")
        await state.clear()

@dp.message()
async def handle_other_messages(message: Message):
    """Handle all other messages"""
    if message.text and not message.text.startswith('/'):
        await message.answer(
            "🤖 **CRM Bot for Advertising Agency**\n\n"
            "I'm here to help you manage leads and contacts.\n\n"
            "Use /start for the main menu\n"
            "or /help for a detailed guide."
        )

# ===== FASTAPI ENDPOINTS =====
@app.post(WEBHOOK_PATH)
async def handle_telegram_webhook(request: Request):
    """Handle Telegram webhook updates"""
    try:
        update_data = await request.json()
        logger.info("📨 Received Telegram update")
        
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        
        return {"status": "ok", "message": "Update processed"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@app.post("/webhook/lead")
async def handle_website_lead(request: Request):
    """Handle leads from website"""
    try:
        data = await request.json()
        logger.info(f"🌐 Received lead from website: {data}")
        
        # Validation
        if not data.get('name') or not data.get('phone'):
            raise HTTPException(
                status_code=400, 
                detail="Missing required fields: name, phone"
            )
        
        # Create lead
        new_lead = {
            'name': data['name'],
            'phone': data['phone'],
            'email': data.get('email', ''),
            'source': data.get('source', 'website'),
            'notes': data.get('notes', ''),
            'date': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        leads.append(new_lead)
        
        # Notify users
        lead_message = (
            f"🎯 **New Lead from Website!**\n\n"
            f"**Name:** {new_lead['name']}\n"
            f"**Phone:** {new_lead['phone']}\n"
            f"**Email:** {new_lead['email'] or 'Not specified'}\n"
            f"**Source:** {new_lead['source']}\n"
            f"**Notes:** {new_lead['notes'] or 'None'}\n"
            f"**Date:** {new_lead['date']}"
        )
        
        # Send to all active users
        sent_count = 0
        for user_id in active_users:
            if await safe_send_message(user_id, lead_message):
                sent_count += 1
        
        logger.info(f"📤 Website lead notification sent to {sent_count} users")
        
        return {
            "status": "success",
            "message": "Lead added successfully",
            "lead_id": len(leads),
            "notifications_sent": sent_count
        }
        
    except Exception as e:
        logger.error(f"Error handling website lead: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        webhook_info = await bot.get_webhook_info()
        return {
            "status": "healthy",
            "service": "Telegram CRM Bot",
            "webhook_url": webhook_info.url,
            "webhook_pending_updates": webhook_info.pending_update_count,
            "active_users": len(active_users),
            "total_leads": len(leads),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "🤖 Telegram CRM Bot is Running!",
        "status": "active",
        "endpoints": {
            "health": "GET /health",
            "webhook_lead": "POST /webhook/lead",
            "telegram_webhook": f"POST {WEBHOOK_PATH}"
        },
        "usage": "Send /start to your bot on Telegram"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
