import os
import asyncio
import discord
from discord.ext import commands
import wavelink
from dotenv import load_dotenv
from typing import Optional

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))  # Your server ID (optional, for faster command sync)

# Setup intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# Create bot with command prefix
bot = commands.Bot(command_prefix="!", intents=intents)


async def setup_lavalink():
    """Setup Lavalink connection with multiple servers"""
    await bot.wait_until_ready()
    
    servers = [
        ("http://lavalink.uk:80", "youshallnotpass"),
        ("http://lavalink.us:80", "youshallnotpass"),
        ("https://lavalink.uk:2333", "youshallnotpass"),
    ]
    
    for uri, password in servers:
        try:
            print(f"[lavalink] Trying {uri}...")
            node = wavelink.Node(uri=uri, password=password)
            await wavelink.Pool.connect(bot=bot, nodes=[node])
            print(f"[lavalink] ✅ Connected to {uri}")
            return True
        except Exception as e:
            print(f"[lavalink] ⚠️  {uri} failed")
            continue
    
    print("[lavalink] ❌ All servers down - music commands won't work")
    return False


@bot.event
async def on_ready():
    print(f"\n{'='*60}")
    print(f"[bot] ✅ Logged in as {bot.user}")
    print(f"[bot] Command prefix: !")
    print(f"[bot] Usage: !play <youtube_url>")
    print(f"{'='*60}\n")
    
    # Try to connect to Lavalink
    asyncio.create_task(setup_lavalink())


@bot.hybrid_command(name="play", description="Play a YouTube video in voice channel")
async def play(ctx: commands.Context, url: str):
    """
    Play a YouTube video in your voice channel
    Usage: !play https://www.youtube.com/watch?v=...
    """
    
    # Check if user is in a voice channel
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ You must be in a voice channel to play music!")
        return
    
    await ctx.defer()
    
    channel = ctx.author.voice.channel
    
    try:
        # Check if bot is already in a voice channel in this server
        player: wavelink.Player = ctx.guild.voice_client
        
        # If not connected, connect to the user's channel
        if player is None:
            await ctx.send(f"🔗 Connecting to {channel.name}...")
            player = await channel.connect(cls=wavelink.Player)
            print(f"[voice] ✅ Joined {channel.name} in {ctx.guild.name}")
        
        # Search for the track
        await ctx.send(f"🔍 Searching: {url[:50]}...")
        
        tracks = await wavelink.Playable.search(url)
        
        if not tracks:
            await ctx.send("❌ No results found! Make sure the YouTube URL is valid and public.")
            return
        
        track = tracks[0]
        
        # Play the track
        await player.play(track)
        
        await ctx.send(f"🎵 Now playing: **{track.title}**\n⏱️ Duration: {int(track.length / 1000 // 60)}m {int(track.length / 1000 % 60)}s")
        print(f"[audio] ✅ Playing: {track.title}")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)[:100]}")
        print(f"[error] Play command failed: {e}")


@bot.hybrid_command(name="stop", description="Stop playing music and disconnect")
async def stop(ctx: commands.Context):
    """Stop the bot and disconnect from voice channel"""
    
    player: wavelink.Player = ctx.guild.voice_client
    
    if player is None:
        await ctx.send("❌ Bot is not in a voice channel!")
        return
    
    try:
        await player.disconnect()
        await ctx.send("⏹️ Stopped playing and disconnected")
        print(f"[voice] Bot disconnected from {player.channel.name}")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@bot.hybrid_command(name="pause", description="Pause the current song")
async def pause(ctx: commands.Context):
    """Pause the currently playing song"""
    
    player: wavelink.Player = ctx.guild.voice_client
    
    if player is None or not player.is_playing():
        await ctx.send("❌ Nothing is playing!")
        return
    
    try:
        await player.pause()
        await ctx.send("⏸️ Paused")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@bot.hybrid_command(name="resume", description="Resume the paused song")
async def resume(ctx: commands.Context):
    """Resume the paused song"""
    
    player: wavelink.Player = ctx.guild.voice_client
    
    if player is None or not player.is_paused():
        await ctx.send("❌ Nothing is paused!")
        return
    
    try:
        await player.resume()
        await ctx.send("▶️ Resumed")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@bot.hybrid_command(name="nowplaying", description="Show currently playing song")
async def nowplaying(ctx: commands.Context):
    """Show the currently playing song"""
    
    player: wavelink.Player = ctx.guild.voice_client
    
    if player is None or not player.is_playing():
        await ctx.send("❌ Nothing is currently playing!")
        return
    
    track = player.current
    position = int(player.position / 1000)
    duration = int(track.length / 1000)
    
    await ctx.send(
        f"🎵 **Now Playing:** {track.title}\n"
        f"⏱️ **Duration:** {position//60}m {position%60}s / {duration//60}m {duration%60}s"
    )


@bot.hybrid_command(name="help", description="Show all available commands")
async def help_command(ctx: commands.Context):
    """Show all available commands"""
    
    help_text = """
**🎵 Music Bot Commands**

`!play <url>` - Play a YouTube video
Example: `!play https://www.youtube.com/watch?v=dQw4w9WgXcQ`

`!stop` - Stop music and disconnect

`!pause` - Pause current song

`!resume` - Resume paused song

`!nowplaying` - Show current song info

`!help` - Show this help message

**Requirements:**
- You must be in a voice channel to use !play
- YouTube URL must be public and allow embedding
- Bot needs permission to join voice channels
"""
    
    await ctx.send(help_text)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Handle command errors"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument! Usage: `!play <youtube_url>`")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ Command not found! Use `!help` for available commands.")
    else:
        await ctx.send(f"❌ Error: {str(error)[:100]}")
        print(f"[error] Command error: {error}")


if __name__ == "__main__":
    missing = [
        name
        for name, val in [
            ("DISCORD_TOKEN", TOKEN),
        ]
        if not val
    ]
    if missing:
        print(f"❌ Missing: {', '.join(missing)}")
    else:
        print("🚀 Starting Discord Music Bot...\n")
        bot.run(TOKEN)
