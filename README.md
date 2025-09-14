# YouTube Transcript Downloader

A simple Python tool to download YouTube video transcripts and save them as markdown files.

## What it does

Downloads transcripts from YouTube videos and saves them to `~/journal/youtube/transcripts/` as markdown files with metadata including video title, duration, language, and timestamps.

## How to use

```bash
# Basic usage
./yt "https://www.youtube.com/watch?v=VIDEO_ID"

# With watch date
./yt "https://www.youtube.com/watch?v=VIDEO_ID" "2024-01-15"

# Just video ID works too
./yt "VIDEO_ID"
```

## Built with

- Python 3.10+
- `youtube-transcript-api` for fetching transcripts
- `requests` for scraping video titles
- `uv` for dependency management

## Setup

```bash
uv sync
```

That's it. The `./yt` wrapper script handles execution with `uv run`.