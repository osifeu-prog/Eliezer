import os
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse
from starlette.routing import Route
from telegram import Update
from bot import create_application
from config import WEBHOOK_URL, PORT

# Create PTB application
application_bot = create_application()

async def telegram_webhook(request: Request) -> Response:
    """Handle incoming Telegram updates."""
    try:
        # Parse the update from Telegram
        update = Update.de_json(data=await request.json(), bot=application_bot.bot)
        await application_bot.process_update(update)
        return Response()
    except Exception as e:
        print(f"Error processing update: {e}")
        return Response(status_code=500)

async def health_check(_: Request) -> PlainTextResponse:
    """Health check endpoint."""
    return PlainTextResponse(content="Bot is running!")

# Create Starlette app
app = Starlette(routes=[
    Route("/telegram", telegram_webhook, methods=["POST"]),
    Route("/healthcheck", health_check, methods=["GET"]),
])

async def setup_webhook():
    """Set up the webhook."""
    await application_bot.bot.set_webhook(url=WEBHOOK_URL)
    print(f"Webhook set to: {WEBHOOK_URL}")

if __name__ == "__main__":
    import asyncio
    
    async def main():
        await setup_webhook()
        config = uvicorn.Config(
            app=app,
            port=PORT,
            host="0.0.0.0"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    asyncio.run(main())
