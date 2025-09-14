#!/usr/bin/env python3
import csv
import sys
import subprocess
from pathlib import Path

def read_videos_csv(csv_file):
    """Read videos from CSV file"""
    videos = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'url' not in row:
                    print(f"Warning: Missing 'url' column in row: {row}")
                    continue

                url = row['url'].strip()
                watch_date = row.get('watch_date', '').strip()

                if not url:
                    print(f"Warning: Empty URL in row: {row}")
                    continue

                videos.append({
                    'url': url,
                    'watch_date': watch_date if watch_date else None
                })

        return videos
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

def download_video(url, watch_date=None):
    """Download a single video using the existing script"""
    cmd = ['uv', 'run', 'python', 'download_transcript.py', url]
    if watch_date:
        cmd.append(watch_date)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Success: {url}")
            return True
        else:
            print(f"✗ Failed: {url}")
            if result.stderr:
                print(f"  Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"✗ Failed: {url} - {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python batch_download.py <csv_file>")
        print("\nCSV format:")
        print("url,watch_date")
        print("https://www.youtube.com/watch?v=dQw4w9WgXcQ,2024-01-15")
        print("https://youtu.be/abc123,2024-01-16")
        sys.exit(1)

    csv_file = sys.argv[1]

    if not Path(csv_file).exists():
        print(f"Error: File '{csv_file}' does not exist")
        sys.exit(1)

    videos = read_videos_csv(csv_file)

    if not videos:
        print("No videos found in CSV file")
        sys.exit(1)

    print(f"Found {len(videos)} videos to process\n")

    successful = 0
    failed = 0

    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] Processing: {video['url']}")

        if download_video(video['url'], video['watch_date']):
            successful += 1
        else:
            failed += 1

        print()  # Add spacing between videos

    print(f"Batch processing complete:")
    print(f"✓ Successful: {successful}")
    print(f"✗ Failed: {failed}")

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()