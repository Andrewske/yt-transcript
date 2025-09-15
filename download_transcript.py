#!/home/kevin/coding/yt-transcript/.venv python3
import sys
import re
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import requests
from youtube_transcript_api import YouTubeTranscriptApi

# Configuration
OUTPUT_DIR = Path.home() / "journal" / "youtube" / "transcripts"


def extract_video_id(url):
    """Extract video ID from YouTube URL or return as-is if already an ID"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*&v=([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Check if input is already a video ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    raise ValueError(f"Invalid YouTube URL: {url}")


def validate_date(date_string):
    """Validate date format YYYY-MM-DD"""
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def get_video_title(video_id):
    """Fetch video title from YouTube"""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Extract title from HTML
        title_match = re.search(r'<title>(.+?) - YouTube</title>', response.text)
        if title_match:
            return title_match.group(1)

        # Fallback to video ID if title not found
        return video_id
    except Exception:
        # If anything fails, use video ID as fallback
        return video_id


def sanitize_filename(title):
    """Convert title to safe filename (lowercase with dashes)"""
    # Convert to lowercase
    filename = title.lower()

    # Replace spaces and special characters with dashes
    filename = re.sub(r'[^\w\s-]', '', filename)  # Remove special chars except spaces and dashes
    filename = re.sub(r'[\s_]+', '-', filename)   # Replace spaces and underscores with dashes
    filename = re.sub(r'-+', '-', filename)       # Collapse multiple dashes
    filename = filename.strip('-')                # Remove leading/trailing dashes

    # Limit length to prevent filesystem issues
    if len(filename) > 100:
        filename = filename[:100].rstrip('-')

    return filename or 'untitled'


def get_transcript(video_id):
    """Fetch transcript from YouTube"""
    try:
        # Create API instance and fetch transcript
        api = YouTubeTranscriptApi()
        segments = api.fetch(video_id, languages=['en', 'en-GB', 'en-US', 'en-AU'])

        # Process segments to include timing data
        processed_segments = []
        for segment in segments:
            processed_segments.append({
                'text': segment.text,
                'start': segment.start,
                'duration': segment.duration
            })

        # Combine into full text (for backward compatibility)
        full_text = ' '.join(segment.text for segment in segments)

        # Calculate duration
        if segments:
            last_segment = segments[-1]
            duration = last_segment.start + last_segment.duration
        else:
            duration = 0

        return {
            'text': full_text,
            'segments': processed_segments,
            'duration': duration,
            'language': 'en',  # We requested English
            'is_generated': True,  # We can't easily determine this with the simple API
        }
    except Exception as e:
        raise ValueError(f"Failed to fetch transcript: {str(e)}")


def format_duration(seconds):
    """Convert seconds to HH:MM:SS or MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def create_markdown(video_id, transcript_data, url, watch_date, use_timeline=False):
    """Create markdown content with metadata and transcript"""
    download_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duration_str = format_duration(transcript_data['duration'])

    markdown = f"""

**URL:** {url}
**Watch Date:** {watch_date}
**Download Date:** {download_date}
**Language:** {transcript_data['language']}
**Duration:** {duration_str}
**Type:** {'Auto-generated' if transcript_data['is_generated'] else 'Manual'}

## Transcript

"""

    if use_timeline and 'segments' in transcript_data:
        # Create timestamped transcript
        for segment in transcript_data['segments']:
            timestamp = format_duration(segment['start'])
            markdown += f"[{timestamp}] {segment['text']}\n"
    else:
        # Use original full text format
        markdown += transcript_data['text']

    return markdown


def save_transcript(video_title, markdown_content):
    """Save transcript to markdown file"""
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate filename from sanitized title
    safe_title = sanitize_filename(video_title)
    filename = f"{safe_title}.md"
    filepath = OUTPUT_DIR / filename

    # Write to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    return filepath


def analyze_transcript_async(file_path):
    """Call analysis script in background"""
    try:
        subprocess.Popen([
            "uv", "run", "python", "analyze_transcript.py", str(file_path)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Note: Transcript analysis skipped - {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Download YouTube video transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  %(prog)s "dQw4w9WgXcQ" --watch-date 2024-01-15
  %(prog)s "https://youtu.be/dQw4w9WgXcQ" --timeline"""
    )

    parser.add_argument('url', help='YouTube URL or video ID')
    parser.add_argument('watch_date', nargs='?',
                       help='Watch date in YYYY-MM-DD format (defaults to today)')
    parser.add_argument('--no-timeline', action='store_false', dest='timeline',
                       help='Disable timestamps in transcript output (timeline is default)')

    args = parser.parse_args()

    try:
        # Handle watch date
        if args.watch_date:
            if not validate_date(args.watch_date):
                print(f"Error: Invalid date format '{args.watch_date}'. Use YYYY-MM-DD")
                sys.exit(1)
            watch_date = args.watch_date
        else:
            watch_date = datetime.now().strftime("%Y-%m-%d")

        # Process transcript
        print(f"Extracting video ID...")
        video_id = extract_video_id(args.url)

        print(f"Fetching video title...")
        video_title = get_video_title(video_id)

        print(f"Fetching transcript for video: {video_id}")
        transcript_data = get_transcript(video_id)

        print(f"Formatting as markdown...")
        markdown = create_markdown(video_id, transcript_data, args.url, watch_date, args.timeline)

        print(f"Saving transcript...")
        filepath = save_transcript(video_title, markdown)

        print(f"✓ Transcript saved to: {filepath}")

        # Start analysis in background
        analyze_transcript_async(filepath)

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
