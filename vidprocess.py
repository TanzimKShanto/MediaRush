import subprocess
import json
import ffmpeg
import os
import asyncio
import re
import sys
from handle_error import catch_errors


def get_bitrate(duration):
    max_file_size = 83886080  # 10 * 1024 * 1024
    return f'{int((max_file_size / duration) * 0.8 / 1000)}k'


def parse_time(time_str):
    # Convert time string (HH:MM:SS.ms) to total seconds
    hours, minutes, seconds = map(float, time_str.split(':'))
    return hours * 3600 + minutes * 60 + seconds


@catch_errors
async def get_video_codec(file_path):
    command = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'format=duration,stream=codec_name', '-of', 'json', file_path
    ]
    result = await asyncio.to_thread(subprocess.run, command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = result.stdout.decode('utf-8')
    data = json.loads(output)
    codec = data['streams'][0]['codec_name'] if 'streams' in data else None
    duration = data['format']['duration']
    return [codec, int(float(duration))]


@catch_errors
async def convert_to_compatible_format(input_file, output_file, duration, mention, bot_msg):
    """ try:
        # Convert video to H.264 video codec and AAC audio codec in MP4 format
        await asyncio.to_thread(
            lambda: ffmpeg.input(input_file).output(
                output_file, vcodec='libx264', video_bitrate=get_bitrate(duration), acodec='aac',  preset='ultrafast', r=30).run()
        )
    except ffmpeg.Error as e:
        print("Error occurred during conversion:", e) """
    try:
        stream = ffmpeg.input(input_file)
        stream = ffmpeg.output(stream, output_file, vcodec='libx264', video_bitrate=get_bitrate(
            duration), acodec='aac',  preset='ultrafast', r=30)
        cmd = ffmpeg.compile(stream, overwrite_output=True)
    except Exception as e:
        print(f"Error building FFmpeg command: {e}", file=sys.stderr)
        return

    time_re = re.compile(r'time=(\d+:\d+:\d+\.\d+)')

    # Create async subprocess
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stderr=asyncio.subprocess.PIPE,
    )

    # Buffer to accumulate stderr output
    buffer = b''

    if mention:
        while True:
            # Read a chunk of stderr data
            chunk = await process.stderr.read(1024)
            if not chunk:
                break
            buffer += chunk

            # Decode buffer and split on carriage returns (FFmpeg uses \r for progress)
            text = buffer.decode(errors='replace')
            if '\r' in text:
                lines = text.split('\r')
                # Process all but the last line (which might be incomplete)
                for line in lines[:-1]:
                    line = line.strip()
                    match = time_re.search(line)
                    if match:
                        time_str = match.group(1)
                        try:
                            current_time = parse_time(time_str)
                            percent = min((current_time / duration) * 100, 100)
                            progress_bar = "█" * \
                                int(percent // 10) + "▒" * \
                                (10 - int(percent // 10))
                            await bot_msg.edit(content=f"**{mention}** Optimizing: {progress_bar} **{int(percent)}%** rendered!")
                            """ print(f"\rProgress: {percent:.2f}%",
                                  end='', flush=True) """
                        except Exception as e:
                            print(
                                f"\nError parsing time: {e}", file=sys.stderr)
                # Keep the last partial line in the buffer
                buffer = lines[-1].encode()

    # Wait for process to finish
    await process.wait()
    print()  # New line after completion


@catch_errors
async def video_process(input_video, mention=None, bot_msg=None):
    codec, duration = await get_video_codec(input_video)
    # print(codec)
    output_video = input_video.replace('target', 'main')
    vcodec = 'libx264'
    if codec not in ['h264', 'vp9', 'vp8']:
        if 'mp4' not in input_video:
            output_video = 'videos/main.mp4'
        await convert_to_compatible_format(input_video, output_video, duration, mention, bot_msg)
    else:
        os.rename(input_video, output_video)
    return output_video

# asyncio.run(video_process('videos/target.webm'))
