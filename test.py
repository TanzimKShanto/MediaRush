import ffmpeg
import asyncio
import re
import sys


def parse_time(time_str):
    # Convert time string (HH:MM:SS.ms) to total seconds
    hours, minutes, seconds = map(float, time_str.split(':'))
    return hours * 3600 + minutes * 60 + seconds


async def track_progress_async(input_file, output_file):
    # Get total duration using ffprobe (run in executor to avoid blocking)
    try:
        loop = asyncio.get_running_loop()
        probe = await loop.run_in_executor(None, ffmpeg.probe, input_file)
        duration = float(probe['format']['duration'])
    except Exception as e:
        print(f"Error probing input file: {e}", file=sys.stderr)
        return

    # Build FFmpeg command
    try:
        stream = ffmpeg.input(input_file)
        stream = ffmpeg.output(stream, output_file)
        cmd = ffmpeg.compile(stream, overwrite_output=True)
    except Exception as e:
        print(f"Error building FFmpeg command: {e}", file=sys.stderr)
        return

    # Regular expression to match time progress
    time_re = re.compile(r'time=(\d+:\d+:\d+\.\d+)')

    # Create async subprocess
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stderr=asyncio.subprocess.PIPE,
    )

    # Buffer to accumulate stderr output
    buffer = b''

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
                        print(f"\rProgress: {percent:.2f}%",
                              end='', flush=True)
                    except Exception as e:
                        print(f"\nError parsing time: {e}", file=sys.stderr)
            # Keep the last partial line in the buffer
            buffer = lines[-1].encode()

    # Wait for process to finish
    await process.wait()
    print()  # New line after completion


async def main():
    await track_progress_async('videos/input.mp4', 'videos/output.mp4')

if __name__ == "__main__":
    asyncio.run(main())
