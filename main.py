import os
import asyncio
import discord
from dotenv import load_dotenv
from datetime import datetime, time


# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("VOICE_CHANNEL_ID")
AUDIO_FILE = os.getenv("AUDIO_FILE", "audio_final.opus")

if CHANNEL_ID is not None:
    try:
        CHANNEL_ID = int(CHANNEL_ID)
    except ValueError:
        CHANNEL_ID = None


# Minimal intents: only what we need for voice
intents = discord.Intents(
    guilds=True,
    voice_states=True,
)

client = discord.Client(intents=intents)

voice_client: discord.VoiceClient | None = None
_track_ended = asyncio.Event()


def get_audio_source() -> discord.AudioSource:
    """
    CPU-optimal path: the file is already Opus-encoded, so we tell FFmpeg
    to copy the stream directly (-c:a copy) with no transcoding whatsoever.
    This keeps FFmpeg CPU usage near zero.
    """
    return discord.FFmpegOpusAudio(
        AUDIO_FILE,
        # -vn: ignore any video stream
        # -c:a copy: pass audio through without re-encoding (zero CPU cost)
        options="-vn -c:a copy",
    )


def _is_connected() -> bool:
    return voice_client is not None and voice_client.is_connected()


async def connect_to_voice() -> discord.VoiceClient | None:
    global voice_client

    if _is_connected():
        return voice_client

    if CHANNEL_ID is None:
        print("[voice] VOICE_CHANNEL_ID is not set or invalid.")
        return None

    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"[voice] Could not find voice channel with ID {CHANNEL_ID}")
        return None

    # Clean up any stale connection first
    if voice_client is not None:
        try:
            await voice_client.disconnect(force=True)
        except Exception:
            pass
        voice_client = None

    try:
        vc = await channel.connect(reconnect=True)
        voice_client = vc
        print(f"[voice] Joined '{channel.name}'")
    except discord.ClientException as e:
        if "Already connected to a voice channel" in str(e):
            for vc in client.voice_clients:
                if vc.channel and vc.channel.id == CHANNEL_ID and vc.is_connected():
                    voice_client = vc
                    print(f"[voice] Re-adopted existing connection in '{vc.channel.name}'")
                    break
        else:
            print(f"[voice] Failed to join: {e}")

    return voice_client


async def start_playback(vc: discord.VoiceClient) -> bool:
    """Play the local audio file. Returns True on success."""
    if not os.path.isfile(AUDIO_FILE):
        print(f"[audio] File not found: '{AUDIO_FILE}' — make sure it's in the repo")
        return False

    print(f"[audio] Playing: {AUDIO_FILE}")

    def _after(err: Exception | None):
        if err:
            print(f"[audio] Playback error: {err}")
        else:
            print("[audio] Track finished — restarting")
        asyncio.run_coroutine_threadsafe(_signal_track_ended(), client.loop)

    vc.play(get_audio_source(), after=_after)
    return True


async def _signal_track_ended():
    _track_ended.set()


async def music_loop():
    """Loop the audio file for the specified duration."""
    await client.wait_until_ready()
    
    duration_minutes = int(os.getenv("DURATION_MINUTES", "60"))
    print(f"[bot] Music loop started. Will play for {duration_minutes} minutes")
    print(f"[bot] Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = asyncio.get_event_loop().time()
    timeout_seconds = duration_minutes * 60

    while not client.is_closed():
        try:
            # Check if we've exceeded the duration
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_seconds:
                print(f"[bot] Duration limit reached ({duration_minutes} minutes). Disconnecting...")
                if _is_connected():
                    try:
                        await voice_client.disconnect(force=True)
                    except Exception:
                        pass
                break

            vc = await connect_to_voice()
            if vc is None:
                print("[loop] Cannot connect — retrying in 15 s")
                await asyncio.sleep(15)
                continue

            if not vc.is_playing() and not vc.is_paused():
                success = await start_playback(vc)
                if not success:
                    await asyncio.sleep(15)
                    continue
                _track_ended.clear()

            # Sleep until the _after callback wakes us — no polling at all.
            try:
                await asyncio.wait_for(_track_ended.wait(), timeout=300)  # 5 min timeout
            except asyncio.TimeoutError:
                print("[loop] Timeout — restarting track")
            finally:
                _track_ended.clear()

        except Exception as e:
            print(f"[loop] Unexpected error: {e}")
            await asyncio.sleep(10)


@client.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
):
    """Reconnect automatically if the bot gets kicked from the channel."""
    global voice_client
    if member.id != client.user.id:
        return
    if before.channel is not None and after.channel is None:
        print("[voice] Bot was disconnected")
        voice_client = None
        _track_ended.set()


@client.event
async def on_ready():
    print(f"[bot] Logged in as {client.user} (ID: {client.user.id})")
    print("------")
    asyncio.get_event_loop().create_task(music_loop())


if __name__ == "__main__":
    missing = [
        name
        for name, val in [
            ("DISCORD_TOKEN", TOKEN),
            ("VOICE_CHANNEL_ID", CHANNEL_ID),
        ]
        if not val
    ]
    if missing:
        print(f"Error: missing required env variables: {', '.join(missing)}")
    else:
        client.run(TOKEN)
