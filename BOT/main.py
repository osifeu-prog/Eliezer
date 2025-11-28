import os
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse
from starlette.routing import Route
from bot import create_application
from config import WEBHOOK_URL, PORT

# Create PTB application
application_bot = create_application()

async def telegram_webhook(request: Request) -> Response:
    """Handle incoming Telegram updates."""
    await application_bot.update_queue.put(
        Update.de_json(data=await request.json(), bot=application_bot.bot)
    )
    return Response()

async def health_check(_: Request) -> PlainTextResponse:
    """Health check endpoint."""
    return PlainTextResponse(content="Bot is running!")

# Create Starlette app
app = Starlette(routes=[
    Route("/telegram", telegram_webhook, methods=["POST"]),
    Route("/healthcheck", health_check, methods=["GET"]),
])

async def main():
    """Set up webhook and start server."""
    await application_bot.initialize()
    await application_bot.bot.set_webhook(url=WEBHOOK_URL)
    
    config = uvicorn.Config(
        app=app,
        port=PORT,
        host="0.0.0.0"
    )
    server = uvicorn.Server(config)
    
    async with application_bot:
        await application_bot.start()
        await server.serve()
        await application_bot.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
