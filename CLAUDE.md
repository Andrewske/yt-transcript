# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a simple YouTube transcript downloader written in Python. The project downloads YouTube video transcripts and saves them as markdown files with metadata. It's designed to be minimal with no complex frameworks - just essential functionality.

## Key Commands

### Development Setup
```bash
# Install dependencies using uv (preferred)
uv sync

# Run the script directly
uv run python download_transcript.py <youtube_url> [watch_date]

# Use the convenient wrapper script
./yt <youtube_url> [watch_date]
```

### Usage Examples
```bash
# Basic usage with YouTube URL
./yt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# With optional watch date
./yt "https://www.youtube.com/watch?v=dQw4w9WgXcQ" "2024-01-15"

# Using just video ID
./yt "dQw4w9WgXcQ"
```

## Architecture

### Core Components

- **`download_transcript.py`**: Main Python script containing all functionality
- **`yt`**: Bash wrapper script that uses `uv run` for easy execution
- **`pyproject.toml`**: Python project configuration with minimal dependencies

### Key Functions in `download_transcript.py`

- `extract_video_id()`: Extracts video ID from various YouTube URL formats
- `get_video_title()`: Fetches video title by scraping YouTube HTML
- `get_transcript()`: Fetches transcript using youtube-transcript-api
- `sanitize_filename()`: Converts video titles to filesystem-safe filenames
- `create_markdown()`: Formats transcript with metadata as markdown
- `save_transcript()`: Saves to `~/journal/youtube/transcripts/`

### Data Flow

1. URL/ID input → Video ID extraction
2. Video ID → Title fetching (web scraping)
3. Video ID → Transcript fetching (API)
4. Transcript + metadata → Markdown formatting
5. Sanitized filename + content → File saving

## Output Structure

Transcripts are saved to `~/journal/youtube/transcripts/` as markdown files named using sanitized video titles. Each file includes:

- Video metadata (URL, dates, duration, language)
- Transcript type (auto-generated vs manual)
- Full transcript text

## Dependencies

- **youtube-transcript-api**: Core transcript fetching
- **requests**: Video title scraping from YouTube HTML

The project uses `uv` for dependency management and execution.