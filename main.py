import asyncio
import os
import re
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message
import yt_dlp

# Replace these with your actual API credentials
API_ID = "your_api_id"
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"

# Initialize the bot client
app = Client("telegram_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Folder to store downloaded files
DOWNLOAD_FOLDER = "downloaded_files"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Function to process links one by one
async def process_link(message: Message, file_id: int, link: str, title: str):
    try:
        # Show progress message
        progress_message = await message.reply(f"Processing: {title}\nFile size: Calculating... \nProgress: 0%")
        
        # Prepare the download options
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{title}.%(ext)s'),
            'progress_hooks': [lambda d: update_progress(d, progress_message, title)],
            'noplaylist': True,
        }

        # Download the file
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)

        # Send the file
        downloaded_file_path = os.path.join(DOWNLOAD_FOLDER, f"{title}.{info_dict['ext']}")
        await message.reply_document(
            document=downloaded_file_path,
            caption=f"[📁File ID: {file_id}] **{title}**",
            parse_mode="Markdown"
        )

        # Delete progress message after completion
        await progress_message.delete()

        # Clean up the downloaded file
        os.remove(downloaded_file_path)

    except FloodWait as e:
        await message.reply(f"⚠️ Flood wait error. Please wait for {e.x} seconds before retrying.")
        await asyncio.sleep(e.x)
        await process_link(message, file_id, link, title)  # Retry processing the link
    except Exception as e:
        await message.reply(f"❌ Error processing link: {e}")

# Function to update progress in the message
def update_progress(d, progress_message, title):
    if d['status'] == 'downloading':
        total_size = d.get('total_bytes', 1)
        downloaded = d.get('downloaded_bytes', 0)
        percent = d.get('percent', 0)
        eta = d.get('eta', 0)

        # Calculate the progress bar
        bar_length = 20
        filled_length = int(bar_length * percent / 100)
        progress_bar = '█' * filled_length + '░' * (bar_length - filled_length)

        # Update the message with progress
        progress_message.edit(
            text=f"Processing: {title}\nFile size: {format_size(total_size)}\n"
                 f"Progress: {percent}%\n{progress_bar}\nETA: {format_time(eta)}"
        )

# Helper function to format file size
def format_size(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1048576:
        return f"{size / 1024:.2f} KB"
    elif size < 1073741824:
        return f"{size / 1048576:.2f} MB"
    else:
        return f"{size / 1073741824:.2f} GB"

# Helper function to format ETA time
def format_time(seconds):
    if seconds <= 0:
        return "Unknown"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"

# Handler for receiving text files with links
@app.on_message(filters.document.mime_type == "text/plain")
async def handle_txt(client, message):
    try:
        # Download the TXT file
        file = await message.document.download()

        # Read the links from the TXT file
        with open(file, "r") as f:
            links = f.readlines()

        # Process each link one by one
        for i, link in enumerate(links, start=1):
            link = link.strip()
            if link:
                # Extract title from the link or assign default if not found
                title = link.split('/')[-1] if len(link.split('/')) > 1 else f"File_{i}"
                await process_link(message, i, link, title)

        # Delete the file after processing
        os.remove(file)

    except Exception as e:
        await message.reply(f"❌ Error processing the file: {e}")

# Start the bot
if __name__ == "__main__":
    app.run()