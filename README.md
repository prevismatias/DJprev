# DJprev | discord bot

Simple music bot made in python that utilizes yt_dlp and FFMPEG. Uses soundcloud's api to search and get song files. In the case of songs being DRM protected, the bot will stream the song from youtube.

## Installation
If you don't want to manually install packages please use the batch/shell script provided in the release :D
### Prerequisites

You will need the following:
- Python3
- FFMPEG
- pip
- Soundcloud Client ID
- Soundcloud Oauth Token
- Create a Discord bot: [Discord Developer Portal](https://discord.com/developers/home)

### FFMPEG:
For windows: you can download FFMPEG using this [link](https://ffmpeg.org/). Then place the directory for ffmpeg.exe in FFMPEG= within the .env file.  

For linux use: `sudo apt install ffmpeg -y` and then `FFMPEG=ffmpeg` into the .env file.

### SoundCloud:
1. First open soundcloud while logged into your account.
2. Get your Soundcloud Client ID by looking at api requests.
3. You can get your Soundcloud OAuth token by going through your browser's client-side storage. 
4. The OAuth Token expires every year or less, you'll have to replace it every now and then.

![Image](https://i.imgur.com/vlm0irC.jpeg)  

![Image](https://i.imgur.com/08O62Hz.jpeg)  


### Python:
start the bot simply with `python3 bot.py`   
Creating a linux service is something I will leave to you guys. Go learn something!
### Commands
```
!play (search query) | searches for song on soundcloud then plays it or adds it to the queue
!skip | skips current song
```

## Technologies

* [FFMPEG](https://ffmpeg.org/) - Audio Streamer
* [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Audio Downloader
* [Discord Developer Portal](https://discord.com/developers/home) - Discord

## License
Project is protected under the [GPL v3](https://www.gnu.org/licenses/gpl-3.0.en.html) license. Feel free to use, modify, and sell it, just keep it open source under the same license.
