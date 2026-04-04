import os
import asyncio
import discord
import wavelink
from dotenv import load_dotenv


# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("VOICE_CHANNEL_ID")
AUDIO_FILE = os.getenv("AUDIO_FILE", "audio_final.opus")
LAVALINK_HOST = os.getenv("LAVALINK_HOST", "lavalink.lavalink.rest")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", "80"))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")

if CHANNEL_ID is not None:
    try:
        CHANNEL_ID = int(CHANNEL_ID)
    except ValueError:
        CHANNEL_ID = None


# Minimal intents
intents = discord.Intents(
    guilds=True,
    voice_states=True,
)

client = discord.Client(intents=intents)
_track_ended = asyncio.Event()


async def connect_to_lavalink():
    """Connect to Lavalink server"""
    try:
        await client.wait_until_ready()
        
        node: wavelink.Node = wavelink.Node(
            uri=f"http://{LAVALINK_HOST}:{LAVALINK_PORT}",
            password=LAVALINK_PASSWORD,
        )
        await wavelink.Pool.connect(client=client, nodes=[node])
        print("[lavalink] Connected to Lavalink server")
    except Exception as e:
        print(f"[lavalink] Failed to connect: {e}")
        await asyncio.sleep(10)
        await connect_to_lavalink()


async def music_loop():
    """Loop the audio file forever"""
    await client.wait_until_ready()
    print("[loop] Music loop started")

    while not client.is_closed():
        try:
            if CHANNEL_ID is None:
                print("[voice] VOICE_CHANNEL_ID is not set or invalid.")
                await asyncio.sleep(15)
                continue

            channel = client.get_channel(CHANNEL_ID)
            if channel is None:
                print(f"[voice] Could not find voice channel with ID {CHANNEL_ID}")
                await asyncio.sleep(15)
                continue

            # Check if already connected
            player: wavelink.Player = channel.guild.voice_client
            if player is not None and player.is_connected():
                if not player.is_playing():
                    # Play the audio file
                    try:
                        tracks = await wavelink.Playable.search(AUDIO_FILE)
                        if not tracks:
                            print(f"[audio] Could not find track: {AUDIO_FILE}")
                            await asyncio.sleep(15)
                            continue
                        
                        await player.play(tracks[0])
                        print(f"[audio] Now playing: {AUDIO_FILE}")
                    except Exception as e:
                        print(f"[audio] Playback error: {e}")
                        await asyncio.sleep(15)
                        continue
                
                # Wait before checking again
                await asyncio.sleep(5)
            else:
                # Connect to voice channel
                try:
                    player = await channel.connect(cls=wavelink.Player)
                    print(f"[voice] Joined '{channel.name}'")
                except Exception as e:
                    print(f"[voice] Failed to join: {e}")
                    await asyncio.sleep(15)

        except Exception as e:
            print(f"[loop] Unexpected error: {e}")
            await asyncio.sleep(10)


@client.event
async def on_ready():
    print(f"[bot] Logged in as {client.user} (ID: {client.user.id})")
    print("------")
    asyncio.get_event_loop().create_task(connect_to_lavalink())
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
