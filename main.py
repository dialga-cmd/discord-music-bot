import os
import asyncio
import discord
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
from datetime import datetime

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("VOICE_CHANNEL_ID")
AUDIO_FILE = os.getenv("AUDIO_FILE", "audio_final.opus")

if CHANNEL_ID is not None:
    try:
        CHANNEL_ID = int(CHANNEL_ID)
    except ValueError:
        CHANNEL_ID = None

intents = discord.Intents(guilds=True, voice_states=True)
client = discord.Client(intents=intents)
voice_client = None
_track_ended = asyncio.Event()

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot alive!", 200

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False)

def get_audio_source():
    return discord.FFmpegOpusAudio(AUDIO_FILE, options="-vn -c:a copy")

def _is_connected():
    return voice_client is not None and voice_client.is_connected()

async def connect_to_voice():
    global voice_client
    if _is_connected():
        return voice_client
    if CHANNEL_ID is None:
        print("[voice] VOICE_CHANNEL_ID not set")
        return None
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"[voice] Channel {CHANNEL_ID} not found")
        return None
    if voice_client is not None:
        try:
            await voice_client.disconnect(force=True)
        except:
            pass
        voice_client = None
    try:
        vc = await channel.connect(reconnect=True)
        voice_client = vc
        print(f"[voice] ✅ Joined '{channel.name}'")
        return vc
    except Exception as e:
        print(f"[voice] ❌ Failed: {e}")
        return None

async def start_playback(vc):
    if not os.path.isfile(AUDIO_FILE):
        print(f"[audio] ❌ File not found: {AUDIO_FILE}")
        return False
    print(f"[audio] Playing: {AUDIO_FILE}")
    def _after(err):
        if err:
            print(f"[audio] ❌ Error: {err}")
        else:
            print("[audio] Track finished")
        asyncio.run_coroutine_threadsafe(_signal_track_ended(), client.loop)
    vc.play(get_audio_source(), after=_after)
    return True

async def _signal_track_ended():
    _track_ended.set()

async def music_loop():
    await client.wait_until_ready()
    duration_minutes = int(os.getenv("DURATION_MINUTES", "60"))
    print(f"\n{'='*60}")
    print(f"[bot] ✅ Logged in as {client.user}")
    print(f"[bot] Duration: {duration_minutes} minutes")
    print(f"{'='*60}\n")
    start_time = asyncio.get_event_loop().time()
    timeout_seconds = duration_minutes * 60
    while not client.is_closed():
        try:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_seconds:
                print(f"\n[bot] ⏰ Duration reached")
                if _is_connected():
                    try:
                        await voice_client.disconnect(force=True)
                    except:
                        pass
                break
            remaining = timeout_seconds - elapsed
            print(f"[loop] ⏱️  Time left: {int(remaining/60)}m {int(remaining%60)}s")
            vc = await connect_to_voice()
            if vc is None:
                print("[loop] Cannot connect — retrying in 15s")
                await asyncio.sleep(15)
                continue
            if not vc.is_playing() and not vc.is_paused():
                success = await start_playback(vc)
                if not success:
                    await asyncio.sleep(15)
                    continue
                _track_ended.clear()
            try:
                await asyncio.wait_for(_track_ended.wait(), timeout=7200)
            except asyncio.TimeoutError:
                print("[loop] 2-hour timeout")
            finally:
                _track_ended.clear()
        except Exception as e:
            print(f"[loop] ❌ Error: {e}")
            await asyncio.sleep(10)

@client.event
async def on_voice_state_update(member, before, after):
    global voice_client
    if member.id != client.user.id:
        return
    if before.channel is not None and after.channel is None:
        print("[voice] Bot disconnected")
        voice_client = None
        _track_ended.set()

@client.event
async def on_ready():
    print(f"[bot] 🤖 Logged in as {client.user}")
    asyncio.get_event_loop().create_task(music_loop())

if __name__ == "__main__":
    missing = [name for name, val in [("DISCORD_TOKEN", TOKEN), ("VOICE_CHANNEL_ID", CHANNEL_ID)] if not val]
    if missing:
        print(f"❌ Missing: {', '.join(missing)}")
    else:
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
        print("[flask] Keep-alive server started\n")
        print("🚀 Starting bot...\n")
        client.run(TOKEN)
