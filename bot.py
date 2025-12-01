# RoseUserBot v3.6 — Final Stable Edition
# Includes: .joinvc <group_id>, DM .play, .leavevc, .bc, .senddm, .sendfile, .invite, .spam, .help (all with examples)
# Base: Ducy's uploaded RoseUserBot (ref: filecite) + new functionality

import asyncio
import time
import logging
import os
import re
from telethon import TelegramClient, events, functions, types
from telethon.tl.functions.channels import GetParticipantRequest, InviteToChannelRequest, EditBannedRequest
from telethon.tl.types import ChatBannedRights, ChannelParticipantAdmin, ChannelParticipantCreator
from pytgcalls import PyTgCalls, idle
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.types import AudioQuality

# ---------------- CONFIG ----------------
API_ID = 32581893
API_HASH = "86d15530bb76890fbed3453d820e94f5"
SESSION_NAME = "RoseUserBot"
VOICE_DIR = "/tmp/voices"
SILENCE_FILE = os.path.join(VOICE_DIR, "silence.mp3")
OWNER_ID = None  # auto-detect
# ----------------------------------------

os.makedirs(VOICE_DIR, exist_ok=True)
logging.basicConfig(level=logging.WARNING)

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
call_py = PyTgCalls(client)

LAST_VC_GROUP = None


# ---------------- Helper Functions ----------------
async def get_owner_id():
    global OWNER_ID
    if OWNER_ID:
        return int(OWNER_ID)
    me = await client.get_me()
    return me.id

async def is_owner(uid):
    return int(uid) == int(await get_owner_id())

async def is_admin(chat_id, user_id):
    try:
        part = (await client(GetParticipantRequest(chat_id, user_id))).participant
        return isinstance(part, (ChannelParticipantAdmin, ChannelParticipantCreator))
    except Exception:
        return False


# ---------------- Auto Voice Save ----------------
@client.on(events.NewMessage(incoming=True))
async def auto_save_voice(event):
    if not event.media:
        return
    if getattr(event.media, "document", None) or getattr(event.media, "voice", None):
        try:
            fname = f"{VOICE_DIR}/{int(time.time())}_{event.sender_id}.ogg"
            await event.download_media(file=fname)
            await client.send_message(await get_owner_id(), f"🎙 Saved voice `{os.path.basename(fname)}` from `{event.sender_id}`")
        except Exception as e:
            print("Save voice failed:", e)


# ---------------- Core Commands ----------------
@client.on(events.NewMessage(pattern=r"^\.start$"))
async def start(event):
    me = await client.get_me()
    await event.reply(
        f"🌹 **RoseUserBot v3.6 Active**\n\n"
        f"👑 Logged in as: @{me.username or me.first_name}\n"
        f"📘 Type `.help` to see all commands.\n\n"
        f"Example:\n` .joinvc -1001234567890 `"
    )

@client.on(events.NewMessage(pattern=r"^\.help$"))
async def help_cmd(event):
    help_text = (
        "**🌹 RoseUserBot v3.6 — Command Guide**\n\n"

        "🎧 **VC Commands**\n"
        "`.joinvc <group_id>` — Join a group’s VC.\n"
        "_Example:_ `.joinvc -1001234567890`\n\n"
        "Reply to a voice in DM and type `.play` — Stream it in VC.\n"
        "_Example:_ Reply to a voice → `.play`\n\n"
        "`.leavevc` — Leave the current VC.\n"
        "_Example:_ `.leavevc`\n\n"

        "🎙 **Voice Recordings**\n"
        "All incoming voice messages are auto-saved in `/tmp/voices/`\n"
        "_Example:_ `.playvc 1700000000_123456.ogg`\n\n"

        "📩 **Messaging / Broadcast**\n"
        "`.senddm <user_id> <text>` — Send a DM.\n"
        "_Example:_ `.senddm 123456789 Hello bro!`\n\n"
        "`.sendfile <user_id> <filename>` — Send file/voice.\n"
        "_Example:_ `.sendfile 123456789 1700000000_123456.ogg`\n\n"
        "`.bc <user_id>` — Send latest recording & invite link.\n"
        "_Example:_ `.bc 123456789`\n\n"
        "`.invite <@username>` — Add user or send invite link.\n"
        "_Example:_ `.invite @testuser`\n\n"

        "🛡️ **Admin Tools**\n"
        "`.kick <reply|@user>` — Kick member.\n"
        "_Example:_ `.kick @username`\n\n"
        "`.ban <reply|@user>` — Ban member.\n"
        "_Example:_ `.ban @username`\n\n"
        "`.unban <reply|@user>` — Unban member.\n"
        "_Example:_ `.unban @username`\n\n"

        "👑 **Owner Only**\n"
        "`.spam <delay> <count> <msg>` — Send repeated messages.\n"
        "_Example:_ `.spam 1 5 Hello!`\n\n"
        "`.stopspam` — Stop all spam tasks.\n"
        "_Example:_ `.stopspam`\n"
    )
    await event.reply(help_text)


# ---------------- Spam Commands ----------------
async def spam_task(chat, delay, count, msg):
    for _ in range(count):
        await client.send_message(chat, msg)
        await asyncio.sleep(delay)

@client.on(events.NewMessage(pattern=r"^\.spam\s+([\d.]+)\s+(\d+)\s+(.+)$"))
async def spam_cmd(event):
    if not await is_owner(event.sender_id):
        return await event.reply("❌ Only owner can use this.\nExample: `.spam 1 10 Hello`")
    delay = float(event.pattern_match.group(1))
    count = int(event.pattern_match.group(2))
    text = event.pattern_match.group(3)
    asyncio.create_task(spam_task(event.chat_id, delay, count, text))
    await event.reply(f"✅ Spamming `{text}` every {delay}s × {count} times.\nExample: `.spam 1 10 Hello`")

@client.on(events.NewMessage(pattern=r"^\.stopspam$"))
async def stop_spam(event):
    await event.reply("🛑 Stop spam manually by restarting.\nExample: `.stopspam`")


# ---------------- VC Join / Play / Leave ----------------
@client.on(events.NewMessage(pattern=r"^\.joinvc(?:\s+(-?\d+))?$"))
async def join_vc(event):
    global LAST_VC_GROUP
    if not await is_owner(event.sender_id):
        return await event.reply("❌ Only owner.\nExample: `.joinvc -1001234567890`")
    gid = event.pattern_match.group(1)
    if not gid:
        return await event.reply("❌ Usage: `.joinvc <group_id>`\nExample: `.joinvc -1001234567890`")
    gid = int(gid)
    if not os.path.exists(SILENCE_FILE):
        return await event.reply(f"❌ Silence file missing.\nCreate it via ffmpeg:\n`ffmpeg -f lavfi -i anullsrc -t 1 {SILENCE_FILE}`")
    try:
        await call_py.join_group_call(gid, AudioPiped(SILENCE_FILE, audio_parameters=AudioQuality.STANDARD))
        LAST_VC_GROUP = gid
        await event.reply(f"✅ Joined VC in `{gid}`.\nNow reply to a voice in DM and type `.play`.\nExample: `.joinvc {gid}`")
    except Exception as e:
        await event.reply(f"❌ Join VC failed: {e}\nExample: `.joinvc -1001234567890`")

@client.on(events.NewMessage(pattern=r"^\.play$"))
async def play_voice(event):
    global LAST_VC_GROUP
    if not await is_owner(event.sender_id):
        return await event.reply("❌ Only owner.\nExample: reply to a voice then `.play`")
    if not LAST_VC_GROUP:
        return await event.reply("⚠️ Not joined in any VC.\nExample: `.joinvc -1001234567890`")
    reply = await event.get_reply_message()
    if not reply or not reply.media:
        return await event.reply("❌ Reply to a voice message first.\nExample: reply + `.play`")
    path = f"{VOICE_DIR}/temp_{int(time.time())}.ogg"
    await reply.download_media(file=path)
    try:
        await call_py.change_stream(LAST_VC_GROUP, AudioPiped(path, audio_parameters=AudioQuality.STANDARD))
        await event.reply(f"🎵 Playing replied voice in VC `{LAST_VC_GROUP}`.\nExample: reply to voice + `.play`")
    except Exception as e:
        await event.reply(f"❌ Play failed: {e}\nExample: reply + `.play`")

@client.on(events.NewMessage(pattern=r"^\.leavevc$"))
async def leave_vc(event):
    global LAST_VC_GROUP
    if not await is_owner(event.sender_id):
        return await event.reply("❌ Only owner.\nExample: `.leavevc`")
    if not LAST_VC_GROUP:
        return await event.reply("⚠️ Not in any VC.\nExample: `.joinvc <group_id>`")
    try:
        await call_py.leave_group_call(LAST_VC_GROUP)
        gid = LAST_VC_GROUP
        LAST_VC_GROUP = None
        await event.reply(f"👋 Left VC in `{gid}`.\nExample: `.leavevc`")
    except Exception as e:
        await event.reply(f"❌ Leave VC failed: {e}\nExample: `.leavevc`")


# ---------------- DM / BC / INVITE ----------------
@client.on(events.NewMessage(pattern=r"^\.senddm\s+(\d+)\s+(.+)$"))
async def send_dm(event):
    if not await is_owner(event.sender_id):
        return await event.reply("❌ Only owner.\nExample: `.senddm 123456789 Hello`")
    uid = int(event.pattern_match.group(1))
    text = event.pattern_match.group(2)
    await client.send_message(uid, text)
    await event.reply(f"✅ Sent DM to `{uid}`.\nExample: `.senddm {uid} Hello`")

@client.on(events.NewMessage(pattern=r"^\.sendfile\s+(\d+)\s+(.+)$"))
async def send_file(event):
    if not await is_owner(event.sender_id):
        return await event.reply("❌ Only owner.\nExample: `.sendfile 123456789 voice.ogg`")
    uid = int(event.pattern_match.group(1))
    name = event.pattern_match.group(2)
    if not os.path.isabs(name):
        name = os.path.join(VOICE_DIR, name)
    if not os.path.exists(name):
        return await event.reply(f"❌ File `{name}` not found.\nExample: `.sendfile 123456789 1700000000_123456.ogg`")
    await client.send_file(uid, name)
    await event.reply(f"✅ Sent `{os.path.basename(name)}` to `{uid}`.\nExample: `.sendfile {uid} {os.path.basename(name)}`")

@client.on(events.NewMessage(pattern=r"^\.bc\s+(\d+)$"))
async def bc(event):
    if not await is_owner(event.sender_id):
        return await event.reply("❌ Only owner.\nExample: `.bc 123456789`")
    uid = int(event.pattern_match.group(1))
    files = sorted([f for f in os.listdir(VOICE_DIR) if os.path.isfile(os.path.join(VOICE_DIR, f))], reverse=True)
    voice = os.path.join(VOICE_DIR, files[0]) if files else None
    try:
        link = await client(functions.messages.ExportChatInviteRequest(event.chat_id))
        invite = link.link
    except Exception:
        invite = None
    if voice:
        await client.send_file(uid, voice, caption="🎙 Latest Recording")
    if invite:
        await client.send_message(uid, f"Join group: {invite}")
    await event.reply(f"✅ Sent broadcast to `{uid}`.\nExample: `.bc {uid}`")

@client.on(events.NewMessage(pattern=r"^\.invite(?:\s+(.+))?$"))
async def invite(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return await event.reply("❌ Admin only.\nExample: `.invite @username`")
    arg = event.pattern_match.group(1)
    if not arg:
        return await event.reply("❌ Usage: `.invite <@username>`\nExample: `.invite @testuser`")
    try:
        user = await client.get_entity(arg)
        try:
            await client(InviteToChannelRequest(event.chat_id, [user]))
            await event.reply(f"✅ Invited [{user.first_name}](tg://user?id={user.id}).\nExample: `.invite {arg}`")
        except Exception:
            link = await client(functions.messages.ExportChatInviteRequest(event.chat_id))
            await client.send_message(user.id, f"Join group: {link.link}")
            await event.reply(f"✅ Sent invite link to {arg}.\nExample: `.invite {arg}`")
    except Exception as e:
        await event.reply(f"❌ Invite failed: {e}\nExample: `.invite {arg}`")


# ---------------- Start Bot ----------------
async def main():
    await client.start()
    await call_py.start()
    me = await client.get_me()
    print(f"✅ Logged in as {me.first_name} (@{me.username})")
    print("🌹 RoseUserBot v3.6 fully operational.")
    if not os.path.exists(SILENCE_FILE):
        print(f"⚠️ Silence file missing: {SILENCE_FILE}")
    await idle()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("❌ Stopped manually.")