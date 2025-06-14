import yt_dlp
import os
import asyncio
from handle_error import catch_errors

VALID_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}


@catch_errors
async def download_video(url, output_path="videos", max_size_mb=10):
    # Ensure the output directory exists
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # if 'instagram.com/' in url:
    #     cookie = './instagram_cookies.txt'
    # else:
    #     cookie = './youtube_cookies.txt'
    options = {
        'outtmpl': f'{output_path}/target.%(ext)s',
        'noplaylist': True,  # Only download the single video
        'max_filesize': max_size_mb * 1024 * 1024,
        'quiet': True,  # Show download progress
        # 'cookiefile': cookie
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            await asyncio.to_thread(ydl.download, [url])
            print("Download complete!")
        except yt_dlp.utils.DownloadError as e:
            print(f"Error downloading: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
    return await find_valid_video()


@catch_errors
async def find_valid_video():
    """Finds a valid video file in the given folder, ignoring .part files."""
    base_name = 'target'  # Get filename without extension

    for ext in VALID_VIDEO_EXTENSIONS:
        video_file = os.path.join('videos', f"{base_name}{ext}")
        if os.path.exists(video_file):
            return video_file  # Return the valid video file

    return 'failed'  # No valid video found
