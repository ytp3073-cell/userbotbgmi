# RoseUserBot v2.1 - Username Support + .spam Owner Command
# ✅ Admin detection works in all group types

import asyncio
import time
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetParticipantRequest, EditBannedRequest
from telethon.tl.types import ChatBannedRights, ChannelParticipantAdmin, ChannelParticipantCreator

# ---------------- CONFIG ----------------
API_ID = 32581893
API_HASH = '86d15530bb76890fbed3453d820e94f5'
SESSION_NAME = "RoseUserBot"

MIN_INTERVAL = 0.1
MAX_INTERVAL = 600.0
MAX_COUNT = 10000

logging.basicConfig(level=logging.WARNING)
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

GROUP_RULES = {}
SCHEDULES = {}

# ---------------- ROLE HELPERS ----------------
async def is_owner(user_id):
    me = await client.get_me()
    return user_id == me.id

async def is_admin(chat_id, user_id):
    try:
        participant = await client(GetParticipantRequest(chat_id, user_id))
        part = participant.participant
        if isinstance(part, (ChannelParticipantAdmin, ChannelParticipantCreator)):
            return True
        if hasattr(part, "admin_rights") and part.admin_rights:
            if getattr(part.admin_rights, "ban_users", False) or getattr(part.admin_rights, "delete_messages", False):
                return True
        return False
    except Exception:
        try:
            perms = await client.get_permissions(chat_id, user_id)
            return perms.is_admin or perms.is_creator
        except:
            me = await client.get_me()
            return user_id == me.id

# ---------------- USER HELPER ----------------
async def get_user_from_event(event, arg=None):
    """Get user id from reply or username."""
    if event.is_reply:
        reply = await event.get_reply_message()
        return reply.sender_id, reply.sender.first_name
    elif arg:
        try:
            user = await client.get_entity(arg)
            return user.id, user.first_name
        except Exception:
            return None, None
    return None, None

# ---------------- PUBLIC COMMANDS ----------------
@client.on(events.NewMessage(pattern=r'^\.start$', outgoing=True, incoming=True))
async def start_cmd(event):
    me = await client.get_me()
    uname = f"@{me.username}" if me.username else me.first_name
    await event.reply(
        f"🌹 **Welcome!**\n\n"
        f"🤖 RoseUserBot active.\n"
        f"💠 Logged in as: {uname}\n"
        f"Use `.help` to view commands."
    )

@client.on(events.NewMessage(pattern=r'^\.help$', outgoing=True, incoming=True))
async def help_cmd(event):
    text = (
        "🌹 **ROSE USERBOT — COMMANDS**\n\n"
        "✨ **Public Commands**\n"
        "• .start — Bot info\n"
        "• .help — This help\n"
        "• .ping — Ping test\n"
        "• .rules — Show group rules\n\n"
        "🛡️ **Admin Commands**\n"
        "• .setrules <text> — Set group rules\n"
        "• .kick — Reply to kick user\n"
        "• .ban @username — Ban user (or reply)\n"
        "• .unban @username — Unban user\n"
        "• .mute @username 1h — Mute user for time\n"
        "• .unmute @username — Unmute user\n\n"
        "👑 **Owner Commands**\n"
        "• .spam <interval> <count> <msg>\n"
        "   Example: `.spam 2 5 Hello group!`\n"
        "• .unschedule — Stop spam\n"
        "• .startpreset — Start sample spam preset\n\n"
        "🧪 Debug:\n"
        "• .checkadmin — Check your admin status"
    )
    await event.reply(text)

@client.on(events.NewMessage(pattern=r'^\.ping$', outgoing=True, incoming=True))
async def ping_cmd(event):
    start = time.time()
    msg = await event.reply("🏓 Testing...")
    end = time.time()
    await msg.edit(f"🏓 Pong! `{(end - start)*1000:.2f} ms`")

@client.on(events.NewMessage(pattern=r'^\.rules$', outgoing=True, incoming=True))
async def rules_cmd(event):
    text = GROUP_RULES.get(event.chat_id, "No rules set yet.")
    await event.reply(f"📜 **Group Rules:**\n{text}")

# ---------------- ADMIN COMMANDS ----------------
@client.on(events.NewMessage(pattern=r'^\.setrules (.+)$', outgoing=True, incoming=True))
async def set_rules(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return await event.reply("❌ Only admins can set rules.")
    text = event.pattern_match.group(1)
    GROUP_RULES[event.chat_id] = text
    await event.reply("✅ Rules updated successfully.")

@client.on(events.NewMessage(pattern=r'^\.kick(?:\s+(@\w+))?$', outgoing=True, incoming=True))
async def kick_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return await event.reply("❌ Only admins can kick users.")
    arg = event.pattern_match.group(1)
    uid, name = await get_user_from_event(event, arg)
    if not uid:
        return await event.reply("❌ Reply or mention a user to kick.")
    try:
        await client.kick_participant(event.chat_id, uid)
        await event.reply(f"✅ Kicked [{name}](tg://user?id={uid})")
    except Exception as e:
        await event.reply(f"❌ Kick failed: {e}")

@client.on(events.NewMessage(pattern=r'^\.ban(?:\s+(@\w+))?$', outgoing=True, incoming=True))
async def ban_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return await event.reply("❌ Only admins can ban users.")
    arg = event.pattern_match.group(1)
    uid, name = await get_user_from_event(event, arg)
    if not uid:
        return await event.reply("❌ Reply or mention a user to ban.")
    rights = ChatBannedRights(until_date=None, view_messages=True)
    try:
        await client(EditBannedRequest(event.chat_id, uid, rights))
        await event.reply(f"🚫 Banned [{name}](tg://user?id={uid})")
    except Exception as e:
        await event.reply(f"❌ Ban failed: {e}")

@client.on(events.NewMessage(pattern=r'^\.unban(?:\s+(@\w+))?$', outgoing=True, incoming=True))
async def unban_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return await event.reply("❌ Only admins can unban users.")
    arg = event.pattern_match.group(1)
    uid, name = await get_user_from_event(event, arg)
    if not uid:
        return await event.reply("❌ Reply or mention a user to unban.")
    rights = ChatBannedRights(until_date=None, view_messages=False)
    try:
        await client(EditBannedRequest(event.chat_id, uid, rights))
        await event.reply(f"✅ Unbanned [{name}](tg://user?id={uid})")
    except Exception as e:
        await event.reply(f"❌ Unban failed: {e}")

@client.on(events.NewMessage(pattern=r'^\.mute(?:\s+(@\w+))?(?:\s+(\d+)([mhd]))?$', outgoing=True, incoming=True))
async def mute_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return await event.reply("❌ Only admins can mute users.")
    arg, val, unit = event.pattern_match.groups()
    uid, name = await get_user_from_event(event, arg)
    if not uid:
        return await event.reply("❌ Reply or mention a user to mute.")
    until_dt = None
    if val and unit:
        val = int(val)
        if unit == "m":
            until_dt = datetime.utcnow() + timedelta(minutes=val)
        elif unit == "h":
            until_dt = datetime.utcnow() + timedelta(hours=val)
        elif unit == "d":
            until_dt = datetime.utcnow() + timedelta(days=val)
    rights = ChatBannedRights(until_date=until_dt, send_messages=True)
    try:
        await client(EditBannedRequest(event.chat_id, uid, rights))
        await event.reply(f"🔇 Muted [{name}](tg://user?id={uid})")
    except Exception as e:
        await event.reply(f"❌ Mute failed: {e}")

@client.on(events.NewMessage(pattern=r'^\.unmute(?:\s+(@\w+))?$', outgoing=True, incoming=True))
async def unmute_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return await event.reply("❌ Only admins can unmute users.")
    arg = event.pattern_match.group(1)
    uid, name = await get_user_from_event(event, arg)
    if not uid:
        return await event.reply("❌ Reply or mention a user to unmute.")
    rights = ChatBannedRights(until_date=None, send_messages=False)
    try:
        await client(EditBannedRequest(event.chat_id, uid, rights))
        await event.reply(f"🎙️ Unmuted [{name}](tg://user?id={uid})")
    except Exception as e:
        await event.reply(f"❌ Unmute failed: {e}")

# ---------------- OWNER COMMANDS ----------------
async def _spam_runner(chat_id: int, interval: float, message: str, total_count: int):
    sent = 0
    try:
        while sent < total_count:
            await client.send_message(chat_id, message)
            sent += 1
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass
    finally:
        if chat_id in SCHEDULES:
            del SCHEDULES[chat_id]

@client.on(events.NewMessage(pattern=r'^\.spam\s+([\d.]+)\s+(\d+)\s+(.+)$', outgoing=True, incoming=True))
async def spam_cmd(event):
    if not await is_owner(event.sender_id):
        return await event.reply("❌ Only bot owner can use .spam.")
    interval = float(event.pattern_match.group(1))
    count = int(event.pattern_match.group(2))
    msg = event.pattern_match.group(3)
    if interval < MIN_INTERVAL:
        return await event.reply(f"❌ Minimum {MIN_INTERVAL}s interval.")
    chat_id = event.chat_id
    if chat_id in SCHEDULES:
        SCHEDULES[chat_id]['task'].cancel()
    task = asyncio.create_task(_spam_runner(chat_id, interval, msg, count))
    SCHEDULES[chat_id] = {"task": task, "interval": interval, "message": msg, "remaining": count}
    await event.reply(f"✅ Spamming `{msg}` every {interval}s × {count}")

@client.on(events.NewMessage(pattern=r'^\.unschedule$', outgoing=True, incoming=True))
async def unschedule_cmd(event):
    if not await is_owner(event.sender_id):
        return await event.reply("❌ Owner only.")
    chat_id = event.chat_id
    if chat_id in SCHEDULES:
        SCHEDULES[chat_id]['task'].cancel()
        del SCHEDULES[chat_id]
        await event.reply("🛑 Spam stopped.")
    else:
        await event.reply("⚠️ No active spam running.")

@client.on(events.NewMessage(pattern=r'^\.startpreset$', outgoing=True, incoming=True))
async def preset_cmd(event):
    if not await is_owner(event.sender_id):
        return await event.reply("❌ Owner only.")
    chat_id = event.chat_id
    msg = "Hello again"
    interval, count = 2.0, 10
    if chat_id in SCHEDULES:
        SCHEDULES[chat_id]['task'].cancel()
    task = asyncio.create_task(_spam_runner(chat_id, interval, msg, count))
    SCHEDULES[chat_id] = {"task": task, "interval": interval, "message": msg, "remaining": count}
    await event.reply(f"✅ Preset started: '{msg}' every {interval}s × {count}.")

# ---------------- DEBUG COMMAND ----------------
@client.on(events.NewMessage(pattern=r'^\.checkadmin$', outgoing=True, incoming=True))
async def check_admin_test(event):
    result = await is_admin(event.chat_id, event.sender_id)
    await event.reply(f"👑 Admin status: {result}")

# ---------------- MAIN ----------------
async def main():
    await client.start()
    me = await client.get_me()
    print(f"✅ Logged in as {me.first_name} (@{me.username})")
    print("🌹 RoseUserBot v2.1 running with username & owner spam support.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())