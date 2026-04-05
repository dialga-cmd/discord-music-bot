import os
import asyncio
import discord
import wavelink
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("VOICE_CHANNEL_ID")
AUDIO_URL = os.getenv("AUDIO_URL")

if CHANNEL_ID is not None:
    try:
        CHANNEL_ID = int(CHANNEL_ID)
    except ValueError:
        CHANNEL_ID = None

intents = discord.Intents(
    guilds=True,
    voice_states=True,
    guild_messages=True,
)

client = discord.Client(intents=intents)


async def setup_lavalink():
    """Connect to Lavalink server with multiple fallbacks"""
    try:
        await client.wait_until_ready()
        
        # List of working Lavalink servers
        servers = [
            ("http://lavalink.uk:80", "youshallnotpass"),
            ("http://lavalink.us:80", "youshallnotpass"),
            ("https://lavalink.uk:2333", "youshallnotpass"),
            ("http://185.255.8.64:80", "youshallnotpass"),
        ]
        
        for uri, password in servers:
            try:
                print(f"[lavalink] Trying {uri}...")
                node = wavelink.Node(uri=uri, password=password)
                await wavelink.Pool.connect(client=client, nodes=[node])
                print(f"[lavalink] ✅ Connected to {uri}")
                return True
            except Exception as e:
                print(f"[lavalink] ⚠️  Failed {uri}: {str(e)[:50]}")
                continue
        
        print("[lavalink] ❌ Could not connect to any Lavalink server")
        print("[lavalink] All servers are down. Try again in a few minutes.")
        return False
        
    except Exception as e:
        print(f"[lavalink] ❌ Error: {e}")
        return False


async def play_audio():
    """Play audio/video in voice channel"""
    await client.wait_until_ready()
    
    duration_minutes = int(os.getenv("DURATION_MINUTES", "60"))
    print(f"\n{'='*60}")
    print(f"[bot] ✅ Bot logged in as {client.user}")
    print(f"[bot] Duration: {duration_minutes} minutes")
    print(f"[bot] Channel ID: {CHANNEL_ID}")
    if AUDIO_URL:
        print(f"[bot] Audio URL: {AUDIO_URL}")
    print(f"{'='*60}\n")

    await asyncio.sleep(5)  # Wait for Lavalink to connect
    
    start_time = asyncio.get_event_loop().time()
    timeout_seconds = duration_minutes * 60
    
    while not client.is_closed():
        try:
            elapsed = asyncio.get_event_loop().time() - start_time
            
            if elapsed > timeout_seconds:
                print(f"\n[bot] ⏰ Duration limit reached")
                for vc in client.voice_clients:
                    await vc.disconnect()
                break
            
            remaining = timeout_seconds - elapsed
            print(f"[loop] ⏱️  Time remaining: {int(remaining/60)}m {int(remaining%60)}s")
            
            if CHANNEL_ID is None:
                print("[voice] VOICE_CHANNEL_ID not set")
                await asyncio.sleep(10)
                continue
            
            channel = client.get_channel(CHANNEL_ID)
            if channel is None:
                print(f"[voice] Channel {CHANNEL_ID} not found")
                await asyncio.sleep(10)
                continue
            
            player: wavelink.Player = channel.guild.voice_client
            
            if player is None:
                try:
                    print(f"[voice] Connecting to {channel.name}...")
                    player = await channel.connect(cls=wavelink.Player)
                    print(f"[voice] ✅ Connected")
                except Exception as e:
                    print(f"[voice] ❌ Connection failed: {e}")
                    await asyncio.sleep(10)
                    continue
            
            if not player.is_playing():
                try:
                    if not AUDIO_URL:
                        print("[audio] ❌ AUDIO_URL not set")
                        await asyncio.sleep(10)
                        continue
                    
                    print(f"[audio] Searching: {AUDIO_URL[:50]}...")
                    tracks = await wavelink.Playable.search(AUDIO_URL)
                    
                    if not tracks:
                        print(f"[audio] ❌ No tracks found")
                        await asyncio.sleep(10)
                        continue
                    
                    track = tracks[0]
                    print(f"[audio] ✅ Now playing: {track.title}")
                    await player.play(track)
                    
                except Exception as e:
                    print(f"[audio] ❌ Error: {e}")
                    await asyncio.sleep(10)
                    continue
            
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"[error] {e}")
            await asyncio.sleep(10)


@client.event
async def on_ready():
    print(f"[bot] 🤖 Logged in as {client.user}")
    asyncio.create_task(setup_lavalink())
    asyncio.create_task(play_audio())


if __name__ == "__main__":
    missing = [
        name
        for name, val in [
            ("DISCORD_TOKEN", TOKEN),
            ("VOICE_CHANNEL_ID", CHANNEL_ID),
            ("AUDIO_URL", AUDIO_URL),
        ]
        if not val
    ]
    if missing:
        print(f"❌ Missing: {', '.join(missing)}")
    else:
        print(f"🚀 Starting bot...\n")
        client.run(TOKEN)
