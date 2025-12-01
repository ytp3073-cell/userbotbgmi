# RoseUserBot v6.0 — Replit Final Build (Full Fix)
# ✅ VC join/play (DM reply)
# ✅ YouTube audio: .playlink / .queue / .skip / .pause / .resume / .stop / .loop
# ✅ .spam, .senddm, .sendfile, .bc, .kick, .ban, .unban, .invite, .start, .help, .pink
# ❌ No auto-save, no automatic media downloads except for playlink temp files
# 🔧 Auto-installs required libs on start

import os, sys, subprocess, asyncio, time, logging

# ---------------- AUTO INSTALL ----------------
REQUIRED = [
    "telethon",
    "pytgcalls==3.0.0",
    "yt-dlp",
    "ffmpeg-python",
    "aiohttp",
]

for pkg in REQUIRED:
    name = pkg.split("==")[0]
    try:
        __import__(name)
    except ImportError:
        print(f"📦 Installing {pkg} ...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

# ---------------- IMPORTS ----------------
from telethon import TelegramClient, events, functions
from telethon.tl.functions.channels import GetParticipantRequest, InviteToChannelRequest, EditBannedRequest
from telethon.tl.types import ChatBannedRights, ChannelParticipantAdmin, ChannelParticipantCreator

from pytgcalls import PyTgCalls, idle
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.types import AudioQuality

import yt_dlp

# ---------------- CONFIG ----------------
API_ID = 32581893   # apna API_ID agar change karna ho to idhar
API_HASH = "86d15530bb76890fbed3453d820e94f5"  # apna API_HASH
SESSION_NAME = "RoseUserBot"

BASE_DIR = "/tmp/rose_v6"
VOICE_DIR = os.path.join(BASE_DIR, "tracks")
VC_FILE = os.path.join(BASE_DIR, "last_vc.txt")
SILENCE_FILE = os.path.join(BASE_DIR, "silence.mp3")

os.makedirs(VOICE_DIR, exist_ok=True)
logging.basicConfig(level=logging.WARNING)

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
call_py = PyTgCalls(client)

OWNER_ID = None
LAST_VC = None

# ------------- MUSIC STATE -------------
play_queue = asyncio.Queue()      # queued tracks (dict)
current_track = None              # currently playing dict
playing = False
paused = False
loop_current = False
skip_flag = False
playback_task = None

# ---------------- HELPERS ----------------
async def get_owner_id():
    global OWNER_ID
    if OWNER_ID:
        return OWNER_ID
    me = await client.get_me()
    OWNER_ID = me.id
    return OWNER_ID

async def is_owner(uid):
    return uid == await get_owner_id()

async def is_admin(chat_id, uid):
    try:
        part = (await client(GetParticipantRequest(chat_id, uid))).participant
        return isinstance(part, (ChannelParticipantAdmin, ChannelParticipantCreator))
    except Exception:
        return False

def save_vc(gid: int):
    with open(VC_FILE, "w") as f:
        f.write(str(gid))

def load_vc():
    if os.path.exists(VC_FILE):
        try:
            with open(VC_FILE) as f:
                return int(f.read().strip() or 0)
        except Exception:
            return None
    return None

def ensure_silence():
    if not os.path.exists(SILENCE_FILE):
        print("🎧 Generating silence.mp3 ...")
        subprocess.run(
            [
                "ffmpeg",
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=mono",
                "-t", "1",
                SILENCE_FILE,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

def cleanup_file(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

ensure_silence()

# ---------------- YT AUDIO DOWNLOAD ----------------
def download_audio_from_youtube(url: str):
    ts = int(time.time() * 1000)
    out_template = os.path.join(VOICE_DIR, f"yt_{ts}.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "geo_bypass": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    # filename resolution
    path = None
    for f in os.listdir(VOICE_DIR):
        if f.startswith(f"yt_{ts}") and f.endswith(".mp3"):
            path = os.path.join(VOICE_DIR, f)
            break
    if not path:
        raise RuntimeError("Downloaded file not found.")
    title = info.get("title", "Unknown Title")
    duration = int(info.get("duration") or 0)
    return {
        "title": title,
        "path": path,
        "duration": duration if duration > 0 else 60,
        "source": url,
    }

# ---------------- PLAYBACK LOOP ----------------
async def playback_loop():
    global current_track, playing, paused, loop_current, skip_flag
    while True:
        track = await play_queue.get()  # wait for next track
        current_track = track
        try:
            if not LAST_VC:
                # not in VC: useless track, clean & continue
                cleanup_file(track.get("path"))
                current_track = None
                continue

            await call_py.change_stream(
                LAST_VC,
                AudioPiped(track["path"], audio_parameters=AudioQuality.STANDARD)
            )
            playing = True
            paused = False
            skip_flag = False

            duration = int(track.get("duration") or 60)
            elapsed = 0
            while elapsed < duration:
                await asyncio.sleep(1)
                elapsed += 1
                if skip_flag:
                    skip_flag = False
                    break
            # after playback finish (or skip), either loop or clean
            if loop_current and not skip_flag:
                # re-add same track at front by putting again
                await play_queue.put(track)
            else:
                cleanup_file(track.get("path"))
        except Exception as e:
            print("Playback error:", e)
            cleanup_file(track.get("path"))
        finally:
            current_track = None
            playing = False
            paused = False

# ---------------- BASIC / INFO COMMANDS ----------------
@client.on(events.NewMessage(pattern=r"^\.start$"))
async def cmd_start(ev):
    me = await client.get_me()
    await ev.reply(
        f"🌹 **RoseUserBot v6.0 (Replit)**\n"
        f"👑 Logged in as: @{me.username or me.first_name}\n"
        f"📘 Use `.help` to see all commands."
    )

@client.on(events.NewMessage(pattern=r"^\.pink$"))
async def cmd_pink(ev):
    await ev.reply("💖 RoseUserBot is online & ready.")

@client.on(events.NewMessage(pattern=r"^\.help$"))
async def cmd_help(ev):
    await ev.reply(
        "**RoseUserBot v6.0 — Command List**\n\n"
        "🎧 **VC / Music**\n"
        "`.joinvc <group_id>` — Join VC\n"
        "Reply to voice + `.play` — Play that voice in VC\n"
        "`.playlink <YouTube_URL>` — Download & queue audio\n"
        "`.queue` — Show queue\n"
        "`.skip` — Skip current track\n"
        "`.pause` / `.resume` — Pause or resume\n"
        "`.stop` — Stop & clear queue\n"
        "`.loop on|off` — Loop current track\n"
        "`.leavevc` — Leave VC\n\n"
        "📩 **Messaging**\n"
        "`.senddm <user_id> <text>`\n"
        "`.sendfile <user_id> <filename>` (from tracks folder)\n"
        "`.bc <user_id>` — Latest track + group invite\n\n"
        "🛡️ **Admin**\n"
        "`.kick @user` | `.ban @user` | `.unban @user` | `.invite @username`\n\n"
        "🔥 **Spam**\n"
        "`.spam <delay> <count> <msg>`\n"
        "`.stopspam`\n"
    )

# ---------------- VC JOIN / LEAVE / DM PLAY ----------------
@client.on(events.NewMessage(pattern=r"^\.joinvc(?:\s+(-?\d+))?$"))
async def cmd_joinvc(ev):
    global LAST_VC
    if not await is_owner(ev.sender_id):
        return await ev.reply("❌ Only owner can use this.")
    gid = ev.pattern_match.group(1)
    if not gid:
        return await ev.reply("Usage: `.joinvc <group_id>`")
    gid = int(gid)
    ensure_silence()
    try:
        await call_py.join_group_call(
            gid,
            AudioPiped(SILENCE_FILE, audio_parameters=AudioQuality.STANDARD)
        )
        LAST_VC = gid
        save_vc(gid)
        await ev.reply(
            f"✅ Joined VC `{gid}`.\n"
            f"• DM me a voice → reply with `.play` to play in VC.\n"
            f"• Or use `.playlink <YouTube_URL>` for music."
        )
    except Exception as e:
        await ev.reply(f"❌ Join VC failed: `{e}`")

@client.on(events.NewMessage(pattern=r"^\.leavevc$"))
async def cmd_leavevc(ev):
    global LAST_VC
    if not await is_owner(ev.sender_id):
        return await ev.reply("❌ Only owner.")
    if not LAST_VC:
        LAST_VC = load_vc()
    if not LAST_VC:
        return await ev.reply("⚠️ Not in VC.")
    try:
        await call_py.leave_group_call(LAST_VC)
    except Exception:
        pass
    LAST_VC = None
    open(VC_FILE, "w").close()
    await ev.reply("👋 Left VC.")

@client.on(events.NewMessage(pattern=r"^\.play$"))
async def cmd_play(ev):
    global LAST_VC
    if not await is_owner(ev.sender_id):
        return await ev.reply("❌ Only owner.")
    if not LAST_VC:
        LAST_VC = load_vc()
    if not LAST_VC:
        return await ev.reply("⚠️ Use `.joinvc <group_id>` first.")
    reply = await ev.get_reply_message()
    if not reply or not reply.media:
        return await ev.reply("❌ Reply to a voice message first.")
    tmp_path = os.path.join(VOICE_DIR, f"dm_{int(time.time())}.ogg")
    await reply.download_media(file=tmp_path)
    try:
        await call_py.change_stream(
            LAST_VC,
            AudioPiped(tmp_path, audio_parameters=AudioQuality.STANDARD)
        )
        await ev.reply("🎵 Playing replied voice in VC.")
    except Exception as e:
        cleanup_file(tmp_path)
        await ev.reply(f"❌ Play failed: `{e}`")

# ---------------- MUSIC: PLAYLINK / QUEUE / CONTROLS ----------------
@client.on(events.NewMessage(pattern=r"^\.playlink\s+(.+)$"))
async def cmd_playlink(ev):
    global playback_task
    if not await is_owner(ev.sender_id):
        return await ev.reply("❌ Only owner.")
    if not LAST_VC:
        return await ev.reply("⚠️ Join VC first with `.joinvc <group_id>`.")
    url = ev.pattern_match.group(1).strip()
    msg = await ev.reply("🔎 Downloading audio from YouTube...")
    loop = asyncio.get_event_loop()
    try:
        track = await loop.run_in_executor(None, download_audio_from_youtube, url)
    except Exception as e:
        return await msg.edit(f"❌ Download failed: `{e}`")
    await play_queue.put(track)
    await msg.edit(f"✅ Queued: **{track['title']}** ({track['duration']}s)")
    if playback_task is None or playback_task.done():
        playback_task = asyncio.create_task(playback_loop())

@client.on(events.NewMessage(pattern=r"^\.queue$"))
async def cmd_queue(ev):
    lines = []
    if current_track:
        lines.append(f"▶️ Now: **{current_track.get('title')}** ({current_track.get('duration',0)}s)")
    qlist = list(play_queue._queue)
    if qlist:
        for i, t in enumerate(qlist, start=1):
            lines.append(f"{i}. {t.get('title')} ({t.get('duration',0)}s)")
    if not lines:
        return await ev.reply("📭 Queue empty.")
    await ev.reply("**Queue:**\n" + "\n".join(lines))

@client.on(events.NewMessage(pattern=r"^\.skip$"))
async def cmd_skip(ev):
    global skip_flag
    if not await is_owner(ev.sender_id):
        return await ev.reply("❌ Only owner.")
    if not current_track:
        return await ev.reply("⚠️ Nothing is playing.")
    skip_flag = True
    try:
        await call_py.change_stream(
            LAST_VC,
            AudioPiped(SILENCE_FILE, audio_parameters=AudioQuality.STANDARD)
        )
    except Exception:
        pass
    await ev.reply("⏭ Skipped current track.")

@client.on(events.NewMessage(pattern=r"^\.pause$"))
async def cmd_pause(ev):
    global paused
    if not await is_owner(ev.sender_id):
        return await ev.reply("❌ Only owner.")
    if not current_track or not playing:
        return await ev.reply("⚠️ Nothing to pause.")
    try:
        await call_py.change_stream(
            LAST_VC,
            AudioPiped(SILENCE_FILE, audio_parameters=AudioQuality.STANDARD)
        )
        paused = True
        await ev.reply("⏸ Paused.")
    except Exception as e:
        await ev.reply(f"❌ Pause failed: `{e}`")

@client.on(events.NewMessage(pattern=r"^\.resume$"))
async def cmd_resume(ev):
    global paused
    if not await is_owner(ev.sender_id):
        return await ev.reply("❌ Only owner.")
    if not current_track or not paused:
        return await ev.reply("⚠️ Nothing to resume.")
    try:
        await call_py.change_stream(
            LAST_VC,
            AudioPiped(current_track["path"], audio_parameters=AudioQuality.STANDARD)
        )
        paused = False
        await ev.reply("▶️ Resumed.")
    except Exception as e:
        await ev.reply(f"❌ Resume failed: `{e}`")

@client.on(events.NewMessage(pattern=r"^\.stop$"))
async def cmd_stop(ev):
    global current_track, playing, loop_current
    if not await is_owner(ev.sender_id):
        return await ev.reply("❌ Only owner.")
    # clear queue
    while not play_queue.empty():
        t = await play_queue.get()
        cleanup_file(t.get("path"))
    # stop current
    if current_track:
        cleanup_file(current_track.get("path"))
    current_track = None
    playing = False
    loop_current = False
    try:
        await call_py.change_stream(
            LAST_VC,
            AudioPiped(SILENCE_FILE, audio_parameters=AudioQuality.STANDARD)
        )
    except Exception:
        pass
    await ev.reply("⏹ Stopped and cleared queue.")

@client.on(events.NewMessage(pattern=r"^\.loop\s+(on|off)$"))
async def cmd_loop(ev):
    global loop_current
    if not await is_owner(ev.sender_id):
        return await ev.reply("❌ Only owner.")
    val = ev.pattern_match.group(1).lower()
    loop_current = (val == "on")
    await ev.reply(f"🔁 Loop is now **{val}**.")

# ---------------- SPAM ----------------
SPAM_TASKS = []

async def spammer(chat_id, delay, count, text):
    for _ in range(count):
        await client.send_message(chat_id, text)
        await asyncio.sleep(delay)

@client.on(events.NewMessage(pattern=r"^\.spam\s+([\d.]+)\s+(\d+)\s+(.+)$"))
async def cmd_spam(ev):
    if not await is_owner(ev.sender_id):
        return await ev.reply("❌ Only owner.")
    delay = float(ev.pattern_match.group(1))
    count = int(ev.pattern_match.group(2))
    text = ev.pattern_match.group(3)
    task = asyncio.create_task(spammer(ev.chat_id, delay, count, text))
    SPAM_TASKS.append(task)
    await ev.reply(f"✅ Spamming '{text}' every {delay}s × {count}")

@client.on(events.NewMessage(pattern=r"^\.stopspam$"))
async def cmd_stopspam(ev):
    for t in SPAM_TASKS:
        t.cancel()
    SPAM_TASKS.clear()
    await ev.reply("🛑 Spam stopped.")

# ---------------- DM / FILE / BC ----------------
@client.on(events.NewMessage(pattern=r"^\.senddm\s+(\d+)\s+(.+)$"))
async def cmd_senddm(ev):
    if not await is_owner(ev.sender_id):
        return
    uid = int(ev.pattern_match.group(1))
    text = ev.pattern_match.group(2)
    await client.send_message(uid, text)
    await ev.reply(f"✅ DM sent to `{uid}`")

@client.on(events.NewMessage(pattern=r"^\.sendfile\s+(\d+)\s+(.+)$"))
async def cmd_sendfile(ev):
    if not await is_owner(ev.sender_id):
        return
    uid = int(ev.pattern_match.group(1))
    name = ev.pattern_match.group(2)
    if not os.path.isabs(name):
        name = os.path.join(VOICE_DIR, name)
    if not os.path.exists(name):
        return await ev.reply(f"❌ File not found: `{name}`")
    await client.send_file(uid, name)
    await ev.reply("✅ File sent.")

@client.on(events.NewMessage(pattern=r"^\.bc\s+(\d+)$"))
async def cmd_bc(ev):
    if not await is_owner(ev.sender_id):
        return
    uid = int(ev.pattern_match.group(1))
    files = sorted(
        [f for f in os.listdir(VOICE_DIR) if os.path.isfile(os.path.join(VOICE_DIR, f))],
        reverse=True
    )
    latest = os.path.join(VOICE_DIR, files[0]) if files else None
    invite = None
    try:
        link = await client(functions.messages.ExportChatInviteRequest(ev.chat_id))
        invite = link.link
    except Exception:
        pass
    if latest:
        await client.send_file(uid, latest, caption="🎙 Latest Track")
    if invite:
        await client.send_message(uid, f"Join group: {invite}")
    await ev.reply(f"✅ Broadcast sent to `{uid}`")

# ---------------- ADMIN ----------------
@client.on(events.NewMessage(pattern=r"^\.kick\s+@?(\w+)$"))
async def cmd_kick(ev):
    if not await is_admin(ev.chat_id, ev.sender_id):
        return await ev.reply("❌ Admin only.")
    user = ev.pattern_match.group(1)
    try:
        entity = await client.get_entity(user)
        await client.kick_participant(ev.chat_id, entity.id)
        await ev.reply(f"👢 Kicked {user}")
    except Exception as e:
        await ev.reply(f"❌ Kick failed: `{e}`")

@client.on(events.NewMessage(pattern=r"^\.ban\s+@?(\w+)$"))
async def cmd_ban(ev):
    if not await is_admin(ev.chat_id, ev.sender_id):
        return await ev.reply("❌ Admin only.")
    user = ev.pattern_match.group(1)
    try:
        entity = await client.get_entity(user)
        rights = ChatBannedRights(until_date=None, view_messages=True)
        await client(EditBannedRequest(ev.chat_id, entity.id, rights))
        await ev.reply(f"🚫 Banned {user}")
    except Exception as e:
        await ev.reply(f"❌ Ban failed: `{e}`")

@client.on(events.NewMessage(pattern=r"^\.unban\s+@?(\w+)$"))
async def cmd_unban(ev):
    if not await is_admin(ev.chat_id, ev.sender_id):
        return await ev.reply("❌ Admin only.")
    user = ev.pattern_match.group(1)
    try:
        entity = await client.get_entity(user)
        rights = ChatBannedRights(until_date=None, view_messages=False)
        await client(EditBannedRequest(ev.chat_id, entity.id, rights))
        await ev.reply(f"✅ Unbanned {user}")
    except Exception as e:
        await ev.reply(f"❌ Unban failed: `{e}`")

@client.on(events.NewMessage(pattern=r"^\.invite\s+@?(\w+)$"))
async def cmd_invite(ev):
    if not await is_admin(ev.chat_id, ev.sender_id):
        return await ev.reply("❌ Admin only.")
    arg = ev.pattern_match.group(1)
    try:
        user = await client.get_entity(arg)
        try:
            await client(InviteToChannelRequest(ev.chat_id, [user]))
            await ev.reply(f"✅ Invited {arg}")
        except Exception:
            link = await client(functions.messages.ExportChatInviteRequest(ev.chat_id))
            await client.send_message(user.id, f"Join group: {link.link}")
            await ev.reply(f"✅ Sent invite link to {arg}")
    except Exception as e:
        await ev.reply(f"❌ Invite failed: `{e}`")

# ---------------- RUN ----------------
async def main():
    global LAST_VC, playback_task
    await client.start()
    await call_py.start()
    LAST_VC = load_vc()
    playback_task = asyncio.create_task(playback_loop())
    me = await client.get_me()
    print(f"✅ Logged in as {me.first_name} (@{me.username})")
    print("🌹 RoseUserBot v6.0 running on Replit.")
    await idle()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("❌ Stopped manually.")