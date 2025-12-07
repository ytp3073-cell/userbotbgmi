import os
from typing import Optional
from fastapi import FastAPI, Request
import httpx

# ---- Telegram Bot Token (directly in code, no .env) ----
TELEGRAM_BOT_TOKEN = "8101342124:AAGH6yaeUN20Nmiro0kENH6zkZ4f_6PxQjw"
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ---- Commands to Vercel APIs ----
OSINT_COMMANDS = {
    "/num": "https://zero-api-number-info.vercel.app/api?number={query}&key=zero",
    "/ifsc": "https://ab-ifscinfoapi.vercel.app/info?ifsc={query}",
    "/mail": "https://ab-mailinfoapi.vercel.app/info?mail={query}",
    "/numtoname": "https://ab-number-to-name.vercel.app/info?number={query}",
    "/numbasic": "https://ab-calltraceapi.vercel.app/info?number={query}"
}

app = FastAPI()


async def tg_send(method: str, payload: dict) -> dict:
    url = f"{TELEGRAM_API_BASE}/{method}"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, timeout=30.0)
        try:
            return r.json()
        except Exception:
            return {"ok": False, "status_code": r.status_code, "text": r.text}


async def handle_osint_search(chat_id: int, query: str, api_url: str, command: str):
    """Call OSINT API and send response in pretty format"""
    url = api_url.format(query=query)
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=20.0)
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text

            emoji_map = {
                "/num": "🇮🇳 IND Number Info",
                "/ifsc": "🏦 IFSC Bank Info",
                "/mail": "✉️ Mail Info",
                "/numtoname": "📝 Number → Name",
                "/numbasic": "🔢 Number → Basic Info"
            }
            title = emoji_map.get(command, "ℹ️ Result")

            formatted = (
                f"📌 {title}\n\n"
                f"```\u200b\n{data}\n```\n"
                f"⚡ by @abbas_tech_india | Contact: @codes_with_abbas"
            )
            await tg_send("sendMessage", {"chat_id": chat_id, "text": formatted, "parse_mode": "Markdown"})
        except Exception as e:
            await tg_send("sendMessage", {"chat_id": chat_id, "text": f"❌ Error: {e}"})


@app.post("/api/webhook")
async def webhook(request: Request):
    update = await request.json()
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True}

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    if not text:
        return {"ok": True}

    lc = text.lower()
    parts = lc.split()

    async def reply(msg: str):
        return await tg_send("sendMessage", {"chat_id": chat_id, "text": msg})

    # /start command
    if lc.startswith("/start"):
        usage = (
            "👋 Welcome to **ArC OSINT Bot**!\n\n"
            "📌 Commands:\n"
            "/num <number> → 🇮🇳 IND Number Info (Zero API)\n"
            "/ifsc <ifsc> → 🏦 IFSC Bank Info\n"
            "/mail <email> → ✉️ Mail Info\n"
            "/numtoname <number> → 📝 Number → Name Info\n"
            "/numbasic <number> → 🔢 Number → Basic Info (CallTrace API)\n\n"
            "Usage example:\n"
            "/num 919876543210\n\n"
            "⚡ by @abbas_tech_india | Contact: @codes_with_abbas\n"
            "✅ Works in groups and private chats!"
        )
        await reply(usage)
        return {"ok": True}

    # Handle OSINT commands
    command = parts[0]
    query = " ".join(parts[1:]).strip()
    if command in OSINT_COMMANDS:
        if not query:
            await reply(f"❌ Please provide a value for {command}. Example:\n{command} 919876543210")
        else:
            await handle_osint_search(chat_id, query, OSINT_COMMANDS[command], command)
        return {"ok": True}

    # Fallback
    await reply("❌ Unknown command. Use /start to see available commands.")
    return {"ok": True}