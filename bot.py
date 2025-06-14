import discord
import os
from dotenv import load_dotenv
import asyncio
from downloader import download_video
from vidprocess import video_process
from handle_error import catch_errors
from reddit_fetcher import monitor_reddit
from storage import *

load_dotenv()

bot_token = os.getenv("BOT_TOKEN")
OUTPUT_PATH = "videos"
video_messages = {}
# print(video_messages)


class Client(discord.Client):
    def __init__(self, *, intents, **options):
        super().__init__(intents=intents, **options)

    @catch_errors
    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        self.download_queue = asyncio.Queue()
        self.subreddits = load_data()
        self.owner = 1199990491022901300
        self.monitor_task = None

        self.subreddit_lock = asyncio.Lock()
        self.file_lock = asyncio.Lock()

        asyncio.create_task(self.process_video_from_queue())
        await self.restart_monitoring()

    async def restart_monitoring(self):
        async with self.subreddit_lock:
            if self.monitor_task:
                self.monitor_task.cancel()
                try:
                    await self.monitor_task  # Wait for task to end
                except asyncio.CancelledError:
                    pass
            self.monitor_task = asyncio.create_task(monitor_reddit(self))
            await asyncio.sleep(30)

    @catch_errors
    async def on_message(self, message):
        message.content = message.content.lower()
        if message.author == self.user:
            return
        if message.content.startswith('!md') and (
            "youtube.com/" in message.content
            or "facebook.com/" in message.content
        ):
            url = message.content.split(" ")[-1].strip()
            await message.delete()
            bot_msg = await message.channel.send(
                f"{message.author.mention} Your video is on its way... ⏳"
            )
            await self.download_queue.put((url, message, bot_msg, False, False))
        elif message.content.startswith('addreddit ') and message.author.id == self.owner:
            # print(self.subreddits)
            rdata = message.content.split(" ")
            subreddit_name = rdata[1].strip()
            fetch_type = rdata[2].strip()
            self.subreddits[subreddit_name]['channel'] = message.channel.id
            self.subreddits[subreddit_name]['type'] = fetch_type
            await save_data(self.subreddits, self.file_lock)
            await message.channel.send(f"✅ Added **r/{subreddit_name}** to this channel! ({fetch_type})")
            await self.restart_monitoring()
        elif message.content.startswith('delreddit ') and message.author.id == self.owner:
            subreddit_name = message.content.split(" ")[1].strip()
            if subreddit_name in self.subreddits.keys():
                del self.subreddits[subreddit_name]
                await save_data(self.subreddits, self.file_lock)
                await message.channel.send(f"✅ Removed **r/{subreddit_name}** from this channel!")
                await self.restart_monitoring()
            else:
                await message.channel.send(f"⚠️ **r/{subreddit_name}** is not currently being monitored!")
        elif message.content.startswith('listreddit'):
            newline = '\n'
            await message.channel.send(f"Currently monitoring: {''.join([f'{newline}1. r/{s} in {self.get_channel(self.subreddits[s]['channel']).name} ({self.subreddits[s]['type']})' for s in self.subreddits.keys()])}")

    @catch_errors
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        if reaction.emoji == "🗑️" and reaction.message.id in video_messages:
            # print(reaction.message.id, user.id)
            if user.id == video_messages[reaction.message.id]:
                await reaction.message.delete()
                del video_messages[reaction.message.id]

    @catch_errors
    async def process_video_from_queue(self):
        while True:
            url, message, bot_msg, rchannel, sub_name = await self.download_queue.get()

            filename = await download_video(url)

            if filename != "failed":
                filename = await video_process(filename, message.author.mention, bot_msg)
                try:
                    if rchannel:
                        rchannel.send(
                            f"**r/{sub_name}**: {url}", file=discord.File(filename))
                    else:
                        await bot_msg.edit(
                            content=f"Shared by {message.author.mention}! React with 🗑️ to delete.",
                            attachments=[discord.File(filename)]
                        )
                except discord.HTTPException as e:
                    print(f"Error editing message: {e}")
                except discord.NotFound:
                    print("Message was deleted before it could be edited.")
                except discord.Forbidden:
                    print("Bot doesn't have permission to edit the message.")
                except Exception as e:
                    print(f"Unexpected error: {e}")

                if not rchannel:
                    video_messages[bot_msg.id] = message.author.id
                    await bot_msg.add_reaction("⬆️")
                    await bot_msg.add_reaction("⬇️")
                    await bot_msg.add_reaction("🗑️")
            elif not rchannel:
                await bot_msg.edit(
                    content=f"Oops! {message.author.mention}, file too big or not a video. ❌"
                )
                await asyncio.sleep(5)  # Wait for 5 seconds
                await bot_msg.delete()

            await self.cleanup_folder(OUTPUT_PATH)

            self.download_queue.task_done()

    @catch_errors
    async def cleanup_folder(self, folder):
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")


if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    client = Client(intents=intents)
    # asyncio.run(client.start(bot_token))   # Instead of client.run(bot_token)
    client.run(bot_token)
