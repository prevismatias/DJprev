import discord
from discord.ext import commands
import requests
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
import random

load_dotenv()

bot_token = os.getenv('BOT_TOKEN')
soundcloud_clientid = os.getenv('SOUNDCLOUD_CLIENT_ID')
soundcloud_oauth = os.getenv('SOUNDCLOUD_OAUTH')
songqueue = {}

intents = discord.Intents.default()
intents.message_content = True
Client = commands.Bot(command_prefix='!', intents=intents)
Client.remove_command('help')

FFMPEG_EXECUTABLE = os.getenv('FFMPEG')

def get_queue(guild_id):
    if guild_id not in songqueue:
        songqueue[guild_id] = []
    return songqueue[guild_id]


def randUseragent():
    with open('UserAgents.txt', 'r') as f:
        useragents = [line.strip() for line in f if line.strip()]
        return random.choice(useragents)

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -protocol_whitelist file,http,https,tcp,tls,crypto',
    'options': '-vn'
}

def get_soundcloud_headers():
    return {
        'Authorization': f'OAuth {soundcloud_oauth}',
        'User-Agent': randUseragent(),
        'Origin': 'https://soundcloud.com',
        'Referer': 'https://soundcloud.com/'
    }

def get_audio_url(permalink_url):
    try:
        r = requests.get(
            f'https://api-v2.soundcloud.com/resolve?url={permalink_url}&client_id={soundcloud_clientid}',
            headers=get_soundcloud_headers(),
            timeout=10
        )
        data = r.json()
        track_auth = data.get('track_authorization', '')

        allowed_protocols = ['progressive', 'hls']

        for t in data['media']['transcodings']:
            protocol = t['format']['protocol']
            if protocol not in allowed_protocols:
                continue
            stream_r = requests.get(
                f"{t['url']}?client_id={soundcloud_clientid}&track_authorization={track_auth}",
                headers=get_soundcloud_headers(),
                timeout=10
            )
            if stream_r.status_code == 200:
                url = stream_r.json().get('url')
                if url:
                    print(f"Got stream: {protocol} {t['format']['mime_type']}")
                    return url

        print("No unencrypted stream found")
        return None

    except Exception as e:
        print(f"Failed to get audio URL: {e}")
        return None

def get_youtube_url(title, artist):
    try:
        ytdl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'socket_timeout': 8,
        }
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{artist} {title}", download=False)
            return info['entries'][0]['url']
    except Exception as e:
        print(f"YouTube fallback failed: {e}")
        return None

async def play_next(voice_client, guild_id):
    queue = get_queue(guild_id)

    if not queue:
        await voice_client.disconnect()
        return

    song = queue.pop(0)
    audio_url = song.get("audio_url")

    if not audio_url:
        print(f"Skipping {song['title']} — no audio source found")
        await play_next(voice_client, guild_id)
        return

    def after_playing(error):
        if error:
            print(f"Player error: {error}")
        asyncio.run_coroutine_threadsafe(
            play_next(voice_client, guild_id),
            Client.loop
        )

    voice_client.play(
        discord.FFmpegPCMAudio(audio_url, executable=FFMPEG_EXECUTABLE, **FFMPEG_OPTIONS),
        after=after_playing
    )

def APIRequest(query: str = None):
    APIheaders = {
        'User-Agent': randUseragent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/json'
    }
    response = requests.get(
        f'https://api-v2.soundcloud.com/search?q={query}&client_id={soundcloud_clientid}&limit=14',
        headers=APIheaders,
        timeout=10
    )
    return response

def getsongs(search_query: str = None):
    response = APIRequest(search_query)
    if response.status_code != 200:
        print(f"Status {response.status_code}: offline or ratelimited")
        return None
    data = response.json()
    count = 1
    result = {
        "data": {
            "query": search_query,
            "songs": {}
        }
    }
    for node in data["collection"]:
        if node["kind"] == "track":
            result["data"]["songs"][str(count)] = {
                "title": node.get("title", "Unknown Title"),
                "artist": (node.get("publisher_metadata") or {}).get("artist", "Unknown Artist"),
                "permalink": node.get("permalink_url", ""),
                "coverlink": node.get("artwork_url", "")
            }
            count += 1
            if count > 5:
                break
    return result

def song_embed(index: int, songinfo):
    song = songinfo[str(index)]
    embed = discord.Embed(title=":musical_note: Playing/Queuing:", color=discord.Color.blurple())
    embed.add_field(name="Title", value=song["title"], inline=True)
    embed.add_field(name="Artist", value=song["artist"], inline=True)
    artwork = song.get("coverlink") or "https://images.steamusercontent.com/ugc/885384897182110030/F095539864AC9E94AE5236E04C8CA7C2725BCEFF/"
    embed.set_thumbnail(url=artwork)
    embed.add_field(name="Link", value=f"[soundcloud]({song['permalink']})", inline=False)
    return embed

class OptionButtons(discord.ui.View):
    def __init__(self, songinfo):
        self.songinfo = songinfo
        super().__init__(timeout=180)

    async def handle_selection(self, interaction: discord.Interaction, index: int):
        await interaction.response.defer()
        self.clear_items()
        await interaction.edit_original_response(view=self)

        song = self.songinfo[str(index)]
        guild_id = interaction.guild.id
        queue = get_queue(guild_id)

        voice_client = interaction.guild.voice_client
        if not voice_client:
            if interaction.user.voice:
                voice_client = await interaction.user.voice.channel.connect()
            else:
                await interaction.followup.send("Join a voice channel first!")
                return


        loop = asyncio.get_event_loop()
        audio_url = await loop.run_in_executor(None, get_audio_url, song["permalink"])

        if not audio_url:
            errornoti = discord.Embed(title=":warning: DRM protected song, streaming from YouTube", color=discord.Color.yellow())
            await interaction.edit_original_response(embed=errornoti)
            audio_url = await loop.run_in_executor(None, get_youtube_url, song["title"], song["artist"])

        queue.append({
            "title": song["title"],
            "artist": song["artist"],
            "permalink": song["permalink"],
            "audio_url": audio_url
        })

        if not voice_client.is_playing():
            await play_next(voice_client, guild_id)

        await interaction.edit_original_response(embed=song_embed(index, self.songinfo), view=self)

    @discord.ui.button(label="1", style=discord.ButtonStyle.primary)
    async def button_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_selection(interaction, 1)

    @discord.ui.button(label="2", style=discord.ButtonStyle.secondary)
    async def button_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_selection(interaction, 2)

    @discord.ui.button(label="3", style=discord.ButtonStyle.secondary)
    async def button_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_selection(interaction, 3)

    @discord.ui.button(label="4", style=discord.ButtonStyle.secondary)
    async def button_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_selection(interaction, 4)

    @discord.ui.button(label="5", style=discord.ButtonStyle.secondary)
    async def button_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_selection(interaction, 5)

@Client.event
async def on_ready():
    print("Ready")
    activity = discord.Game(name='Call of Candy: Trap Ops Zombies')
    await Client.change_presence(status=discord.Status.idle, activity=activity)

@Client.command()
@commands.guild_only()
async def skip(ctx):
    if not ctx.author.voice:
        await ctx.send("You must be in a voice channel first!")
        return
    voice_client = ctx.voice_client
    if not voice_client or not voice_client.is_playing():
        await ctx.send("Nothing is playing!")
        return
    voice_client.stop()
    await ctx.send("Skipped!")

@Client.command()
@commands.guild_only()
async def play(ctx, *, songtitle: str = None):
    if not songtitle:
        await ctx.send("Please provide a song title!")
        return
    if not ctx.author.voice:
        await ctx.send("You must be in a voice channel first!")
        return
    if not ctx.voice_client:
        channel = ctx.author.voice.channel
        await channel.connect()
        embed = discord.Embed(title=f":loud_sound: Joined {channel.name}!", color=discord.Color.blue())
        await ctx.send(embed=embed)

    songs = getsongs(songtitle)
    if not songs or not songs["data"]["songs"]:
        await ctx.send("No results found.")
        return

    songs_list = ""
    count = 1
    for key, song in songs["data"]["songs"].items():
        songs_list += f"{count}. **{song['artist']}** - {song['title']}\n"
        count += 1

    embed = discord.Embed(title=":mag: Search Results:", description=songs_list, color=discord.Color.blue())
    await ctx.send(embed=embed, view=OptionButtons(songs["data"]["songs"]))

Client.run(bot_token)
