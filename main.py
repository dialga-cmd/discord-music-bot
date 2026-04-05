import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import subprocess
import re

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


def get_youtube_audio_url(youtube_url: str) -> str:
    """Extract audio stream URL from YouTube URL using yt-dlp"""
    try:
        cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "-g",
            youtube_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            audio_url = result.stdout.strip().split('\n')[0]
            print(f"[youtube] ✅ Got audio URL")
            return audio_url
        else:
            print(f"[youtube] ❌ yt-dlp error: {result.stderr}")
            return None
    except Exception as e:
        print(f"[youtube] ❌ Error: {e}")
        return None


@bot.event
async def on_ready():
    print(f"\n{'='*60}")
    print(f"[bot] ✅ Logged in as {bot.user}")
    print(f"[bot] Command prefix: !")
    print(f"[bot] Usage: !play <youtube_url>")
    print(f"{'='*60}\n")


@bot.hybrid_command(name="play", description="Play a YouTube video")
async def play(ctx: commands.Context, url: str):
    """
    Play a YouTube video in your voice channel
    Usage: !play https://www.youtube.com/watch?v=...
    """
    
    # Check if user is in voice channel
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ You must be in a voice channel!")
        return
    
    await ctx.defer()
    
    channel = ctx.author.voice.channel
    
    try:
        # Validate YouTube URL
        if "youtube.com" not in url and "youtu.be" not in url:
            await ctx.send("❌ That doesn't look like a YouTube URL!")
            return
        
        await ctx.send("🔄 Getting video info...")
        
        # Get audio URL from YouTube
        audio_url = await asyncio.to_thread(get_youtube_audio_url, url)
        
        if not audio_url:
            await ctx.send("❌ Couldn't get audio from that video. Make sure it's public and allows embedding.")
            return
        
        # Connect to voice channel
        player = ctx.guild.voice_client
        if player is None:
            player = await channel.connect()
            print(f"[voice] ✅ Joined {channel.name}")
        
        # Stop current playback if any
        if player.is_playing():
            player.stop()
        
        # Create audio source from URL
        audio_source = discord.FFmpegOpusAudio(
            audio_url,
            options="-vn -c:a copy"
        )
        
        # Play audio
        def after_playback(error):
            if error:
                print(f"[audio] ❌ Playback error: {error}")
            else:
                print(f"[audio] ✅ Track finished")
        
        player.play(audio_source, after=after_playback)
        
        await ctx.send(f"🎵 Now playing from: {url[:50]}...")
        print(f"[audio] ✅ Playing from YouTube")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)[:100]}")
        print(f"[error] Play command error: {e}")


@bot.hybrid_command(name="stop", description="Stop music and disconnect")
async def stop(ctx: commands.Context):
    """Stop and disconnect from voice"""
    
    player = ctx.guild.voice_client
    
    if player is None:
        await ctx.send("❌ Not in a voice channel!")
        return
    
    try:
        player.stop()
        await player.disconnect()
        await ctx.send("⏹️ Stopped and disconnected")
        print(f"[voice] Bot disconnected")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@bot.hybrid_command(name="pause", description="Pause the current song")
async def pause(ctx: commands.Context):
    """Pause current song"""
    
    player = ctx.guild.voice_client
    
    if player is None or not player.is_playing():
        await ctx.send("❌ Nothing is playing!")
        return
    
    try:
        player.pause()
        await ctx.send("⏸️ Paused")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@bot.hybrid_command(name="resume", description="Resume the paused song")
async def resume(ctx: commands.Context):
    """Resume paused song"""
    
    player = ctx.guild.voice_client
    
    if player is None or not player.is_paused():
        await ctx.send("❌ Nothing is paused!")
        return
    
    try:
        player.resume()
        await ctx.send("▶️ Resumed")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@bot.hybrid_command(name="help", description="Show all commands")
async def help_command(ctx: commands.Context):
    """Show all commands"""
    
    help_text = """
**🎵 Music Bot Commands**

`!play <url>` - Play a YouTube video
Example: `!play https://www.youtube.com/watch?v=dQw4w9WgXcQ`

`!stop` - Stop and disconnect

`!pause` - Pause current song

`!resume` - Resume paused song

`!help` - Show this message

**Requirements:**
- Must be in a voice channel to use !play
- YouTube URL must be public
- Bot needs Voice permissions
"""
    
    await ctx.send(help_text)


@bot.event
async def on_command_error(ctx: commands.Context, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Usage: `!play <youtube_url>`")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found! Use `!help`")
    else:
        await ctx.send(f"❌ Error: {str(error)[:100]}")


if __name__ == "__main__":
    if not TOKEN:
        print("❌ DISCORD_TOKEN not set!")
    else:
        print("🚀 Starting Music Bot...\n")
        bot.run(TOKEN)
