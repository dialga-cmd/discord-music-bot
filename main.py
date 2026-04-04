import os
import asyncio
import discord
from dotenv import load_dotenv
from datetime import datetime


# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("VOICE_CHANNEL_ID")
AUDIO_FILE = os.getenv("AUDIO_FILE", "audio_final.opus")
AUDIO_URL = os.getenv("AUDIO_URL")  # Optional: URL to audio file

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
    Get audio source from URL or local file.
    URL is preferred because it doesn't require uploading large files to GitHub.
    """
    
    # Try URL first if provided
    if AUDIO_URL:
        print(f"[audio] Using URL: {AUDIO_URL}")
        return discord.FFmpegOpusAudio(
            AUDIO_URL,
            options="-vn -c:a copy",
        )
    
    # Fall back to local file
    if os.path.isfile(AUDIO_FILE):
        print(f"[audio] Using local file: {AUDIO_FILE}")
        return discord.FFmpegOpusAudio(
            AUDIO_FILE,
            options="-vn -c:a copy",
        )
    
    # If neither works, we have a problem
    raise FileNotFoundError(f"Audio file '{AUDIO_FILE}' not found and no AUDIO_URL provided")


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
        except Exception as e:
            print(f"[voice] Error disconnecting: {e}")
        voice_client = None

    try:
        vc = await channel.connect(reconnect=True)
        voice_client = vc
        print(f"[voice] ✅ Successfully joined '{channel.name}'")
        return vc
    except discord.ClientException as e:
        print(f"[voice] ❌ Failed to join: {e}")
        
        # Try to adopt existing connection
        if "Already connected" in str(e):
            for vc in client.voice_clients:
                if vc.channel and vc.channel.id == CHANNEL_ID and vc.is_connected():
                    voice_client = vc
                    print(f"[voice] ✅ Re-adopted existing connection")
                    return vc
        
        return None
    except Exception as e:
        print(f"[voice] ❌ Unexpected error: {e}")
        return None


async def start_playback(vc: discord.VoiceClient) -> bool:
    """Play the audio file or URL. Returns True on success."""
    try:
        print(f"[audio] Attempting to play audio...")
        source = get_audio_source()

        def _after(err: Exception | None):
            if err:
                print(f"[audio] ❌ Playback error: {err}")
            else:
                print("[audio] Track finished — restarting in 2 seconds")
            asyncio.run_coroutine_threadsafe(_signal_track_ended(), client.loop)

        vc.play(source, after=_after)
        print(f"[audio] ✅ Now playing audio")
        return True

    except FileNotFoundError as e:
        print(f"[audio] ❌ {e}")
        return False
    except Exception as e:
        print(f"[audio] ❌ Error starting playback: {e}")
        return False


async def _signal_track_ended():
    await asyncio.sleep(2)  # 2 second delay before restarting
    _track_ended.set()


async def music_loop():
    """Loop the audio file for the specified duration."""
    await client.wait_until_ready()
    
    duration_minutes = int(os.getenv("DURATION_MINUTES", "60"))
    print(f"\n{'='*60}")
    print(f"[bot] ✅ Bot is ready!")
    print(f"[bot] Duration: {duration_minutes} minutes")
    print(f"[bot] Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    start_time = asyncio.get_event_loop().time()
    timeout_seconds = duration_minutes * 60
    reconnect_attempts = 0
    max_attempts = 5

    while not client.is_closed():
        try:
            # Check if we've exceeded the duration
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining = timeout_seconds - elapsed
            
            if elapsed > timeout_seconds:
                print(f"\n[bot] ⏰ Duration limit reached ({duration_minutes} minutes)")
                if _is_connected():
                    print(f"[bot] Disconnecting from voice channel...")
                    try:
                        await voice_client.disconnect(force=True)
                    except Exception:
                        pass
                break

            print(f"[loop] ⏱️  Time remaining: {int(remaining/60)} minutes {int(remaining%60)} seconds")

            # Try to connect
            vc = await connect_to_voice()
            if vc is None:
                reconnect_attempts += 1
                print(f"[loop] ❌ Cannot connect (attempt {reconnect_attempts}/{max_attempts})")
                if reconnect_attempts >= max_attempts:
                    print(f"[loop] ❌ Max reconnection attempts reached. Stopping.")
                    break
                await asyncio.sleep(10)
                continue
            
            reconnect_attempts = 0  # Reset on successful connection

            # Check if we need to start playing
            if not vc.is_playing() and not vc.is_paused():
                success = await start_playback(vc)
                if not success:
                    print(f"[loop] Retrying in 10 seconds...")
                    await asyncio.sleep(10)
                    continue
                _track_ended.clear()

            # Wait for track to end
            try:
                await asyncio.wait_for(_track_ended.wait(), timeout=30)
            except asyncio.TimeoutError:
                # Track is still playing, check again in 30 seconds
                pass
            finally:
                _track_ended.clear()

        except Exception as e:
            print(f"[loop] ❌ Unexpected error: {e}")
            await asyncio.sleep(10)


@client.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
):
    """Detect if bot was kicked from channel."""
    global voice_client
    if member.id != client.user.id:
        return
    if before.channel is not None and after.channel is None:
        print("[voice] ⚠️  Bot was disconnected from voice channel")
        voice_client = None
        _track_ended.set()


@client.event
async def on_ready():
    print(f"\n[bot] 🤖 Logged in as {client.user} (ID: {client.user.id})")
    print(f"[bot] Using Channel ID: {CHANNEL_ID}")
    if AUDIO_URL:
        print(f"[bot] Audio source: URL")
    else:
        print(f"[bot] Audio source: Local file ({AUDIO_FILE})")
    print("------\n")
    asyncio.get_event_loop().create_task(music_loop())


@client.event
async def on_error(event, *args, **kwargs):
    """Log any errors"""
    print(f"[error] Error in {event}: {asyncio.get_event_loop().get_debug()}")
    import traceback
    traceback.print_exc()


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
        print(f"❌ Error: missing required env variables: {', '.join(missing)}")
    else:
        print(f"🚀 Starting Discord bot...\n")
        client.run(TOKEN)
