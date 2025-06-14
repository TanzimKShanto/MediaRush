import asyncpraw
import os
from dotenv import load_dotenv
import asyncio
from downloader import download_video
from vidprocess import video_process

load_dotenv()

REDDIT_CLIENT_ID = "-HitQ7-VIYoZVO0GACg46g"
REDDIT_CLIENT_SECRET = "UC0oCtAWM3xfaqagoE-zFn4iqZBCVg"
user_agent = "python:MediaRush:v1.0 (by /u/Pure_Membership_2573)"

CHANNEL_ID = 1347727180683284491


def is_image(url):
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    return any(url.lower().endswith(ext) for ext in image_extensions)


async def monitor_reddit(client):
    while True:  # Auto-reconnect loop
        try:
            if not client.subreddits:
                await asyncio.sleep(10)  # No subreddits to watch
                continue
            # Initialize a NEW Reddit client INSIDE the async loop
            async with asyncpraw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent=user_agent,
            ) as reddit:
                subreddit = await reddit.subreddit('+'.join(client.subreddits.keys()))
                stream = subreddit.stream.submissions(skip_existing=True)

                # print(reddit.user.me())
                print("Connected to Reddit stream")
                async for submission in stream:
                    # print(client.subreddits)
                    sub_name = submission.subreddit.display_name.lower()
                    # print(submission.subreddit)
                    channel = client.get_channel(
                        client.subreddits[sub_name]['channel'])
                    if client.subreddits[sub_name]['type'] == 'image' and is_image(submission.url):
                        if channel:
                            await channel.send(f"**r/{sub_name}**: {submission.url}")
                        else:
                            print("Error: Discord channel not found.")
                    elif client.subreddits[sub_name]['type'] == 'video' and submission.get("is_video", False):
                        client.download_queue.put(
                            (submission.url, False, False, channel, sub_name))

        except Exception as e:
            print(f"Reddit stream error: {e}. Retrying in 30 seconds...")
            await asyncio.sleep(30)  # Restart monitoring
