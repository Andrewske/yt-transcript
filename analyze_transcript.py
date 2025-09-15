#!/usr/bin/env python3
"""
Analyze YouTube transcripts using local Ollama LLM and build searchable index.
"""

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Extract the most important keywords from this transcript. Focus on key topics, concepts, technologies, and subjects discussed.

Guidelines:
- Use specific nouns and key phrases (1-3 words max)
- Prioritize concrete topics over abstract concepts
- Avoid filler words, pronouns, or generic terms
- Choose words that would help categorize this content

Text: {transcript_text}

Output format:
["keyword1", "keyword2", "keyword3", ...]"""

INDEX_FILE = Path("/home/kevin/journal/youtube/transcript_index.json")
OLLAMA_URL = "http://localhost:11434"


def check_ollama_status() -> bool:
    """Verify Ollama service is running."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def parse_transcript_file(file_path: Path) -> Optional[Dict]:
    """Extract metadata and content from markdown transcript file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract video ID from URL in metadata
        video_id_match = re.search(r'watch\?v=([a-zA-Z0-9_-]+)', content)
        if not video_id_match:
            logger.error(f"Could not find video ID in {file_path}")
            return None

        # Extract title from first heading
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else file_path.stem

        # Extract transcript text (everything after "## Transcript")
        transcript_match = re.search(r'## Transcript\s*\n(.+)', content, re.DOTALL)
        transcript_text = transcript_match.group(1).strip() if transcript_match else ""

        if not transcript_text:
            logger.error(f"No transcript content found in {file_path}")
            return None

        word_count = len(transcript_text.split())

        return {
            "video_id": video_id_match.group(1),
            "title": title,
            "file_path": str(file_path.absolute()),
            "transcript_text": transcript_text,
            "word_count": word_count
        }

    except Exception as e:
        logger.error(f"Error parsing transcript file {file_path}: {e}")
        return None


def clean_transcript_text(transcript_text: str) -> str:
    """Remove time markers and normalize whitespace from transcript text."""
    # Remove time markers like [21:32], [1:23:45], etc.
    cleaned = re.sub(r'\[\d+:\d+(?::\d+)?\]', '', transcript_text)

    # Remove backslashes before single quotes
    cleaned = cleaned.replace("\\'", "'")

    # Replace multiple newlines with single spaces
    cleaned = re.sub(r'\n+', ' ', cleaned)

    # Replace multiple spaces with single spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)

    # Strip leading/trailing whitespace
    return cleaned.strip()


def clean_keywords(keywords: List[str]) -> List[str]:
    """Clean and filter extracted keywords."""
    cleaned = []
    stop_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
        'a', 'an', 'some', 'any', 'all', 'each', 'every', 'one', 'two', 'first', 'second',
        'conversation', 'speaker', 'individual', 'discussion', 'mentioned', 'include', 'including'
    }

    for keyword in keywords:
        if not keyword or not keyword.strip():
            continue

        # Clean the keyword
        clean_kw = keyword.strip().strip('"\'.,;:!?').lower()

        # Skip if too short, too long, or a stop word
        if len(clean_kw) < 2 or len(clean_kw) > 25 or clean_kw in stop_words:
            continue

        # Skip phrases that sound like descriptions
        if any(phrase in clean_kw for phrase in ['topic', 'points mentioned', 'seems to be', 'conversation is']):
            continue

        # Capitalize properly and add
        if clean_kw not in [c.lower() for c in cleaned]:  # Avoid duplicates
            cleaned.append(clean_kw.title() if not clean_kw.isupper() else clean_kw)

    return cleaned[:10]  # Limit to 10 keywords


def analyze_with_ollama(transcript_text: str) -> Optional[Dict]:
    """Send transcript to Ollama for analysis."""
    try:
        # Clean transcript text by removing time markers and normalizing whitespace
        transcript_text = clean_transcript_text(transcript_text)

        # Truncate transcript if too long to avoid token limits
        max_chars = 50000  # Rough estimate for token limit
        if len(transcript_text) > max_chars:
            transcript_text = transcript_text[:max_chars] + "\n[Content truncated for analysis]"
            logger.info(f'Transcript truncated for analysis due to length {len(transcript_text)}')

        payload = {
            "model": "qwen2.5:7b",
            "prompt": ANALYSIS_PROMPT.format(transcript_text=transcript_text),
            "stream": False
        }

        logger.info("Sending transcript to Ollama for analysis...")
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)

        if response.status_code == 200:
            response_data = response.json()
            analysis_text = response_data.get("response", "")

            # Try to parse as JSON first
            try:
                analysis = json.loads(analysis_text)
                logger.info("Analysis completed successfully")

                # If we got an array directly, clean and return it
                if isinstance(analysis, list):
                    return clean_keywords(analysis)

                # If we got an object, try to extract keywords from it
                if isinstance(analysis, dict):
                    # Try to find any array values
                    for value in analysis.items():
                        if isinstance(value, list):
                            return value
                    # If no arrays, collect all string values
                    keywords = [str(v) for v in analysis.values() if v is not None and str(v).strip()]
                    return clean_keywords(keywords)

                return analysis
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract array from text
                logger.info("Response is not valid JSON, attempting text parsing")

                # Look for array-like patterns in the text
                import re
                array_match = re.search(r'\[(.*?)\]', analysis_text, re.DOTALL)
                if array_match:
                    array_content = array_match.group(1)
                    # Split by comma and clean up
                    keywords = [item.strip().strip('"\'') for item in array_content.split(',')]
                    keywords = [k for k in keywords if k]  # Remove empty strings
                    logger.info("Extracted keywords from text format")
                    return clean_keywords(keywords)

                # Fallback: split by common delimiters
                words = re.findall(r'\b[A-Za-z][A-Za-z\s]+[A-Za-z]\b', analysis_text)
                keywords = list(set(words[:10]))  # Remove duplicates
                logger.warning("Using fallback keyword extraction")
                return clean_keywords(keywords)
        else:
            logger.error(f"Ollama API error: {response.status_code}")
            return None

    except requests.exceptions.Timeout:
        logger.error("Ollama API request timed out")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama API request failed: {e}")
        return None


def load_index() -> Dict:
    """Load existing transcript index or create empty one."""
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading index file: {e}. Starting fresh.")

    return {"transcripts": []}


def save_index(data: Dict) -> None:
    """Save updated index to JSON file."""
    try:
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Index updated with {len(data['transcripts'])} transcripts")
    except IOError as e:
        logger.error(f"Failed to save index: {e}")


def is_already_analyzed(video_id: str, index: Dict) -> bool:
    """Check if transcript already processed."""
    return any(t["video_id"] == video_id for t in index["transcripts"])


def main():
    """CLI interface taking file path argument."""
    if len(sys.argv) != 2:
        print("Usage: python analyze_transcript.py <transcript_file_path>")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    # Check Ollama status
    if not check_ollama_status():
        logger.error("Ollama service not available at http://localhost:11434")
        logger.error("Please ensure Ollama is running and try again")
        sys.exit(1)

    # Parse transcript file
    transcript_data = parse_transcript_file(file_path)
    if not transcript_data:
        logger.error("Failed to parse transcript file")
        sys.exit(1)

    # Load existing index
    index = load_index()

    # Check if already analyzed
    if is_already_analyzed(transcript_data["video_id"], index):
        logger.info("Transcript already analyzed, skipping...")
        return

    # Analyze with Ollama
    analysis = analyze_with_ollama(transcript_data["transcript_text"])
    if not analysis:
        logger.error("Failed to analyze transcript")
        sys.exit(1)

    # Build index entry
    entry = {
        "video_id": transcript_data["video_id"],
        "title": transcript_data["title"],
        "file_path": transcript_data["file_path"],
        "keywords": analysis,
        "analyzed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "word_count": transcript_data["word_count"]
    }

    # Add to index and save
    index["transcripts"].append(entry)
    save_index(index)

    logger.info(f"Successfully analyzed and indexed: {transcript_data['title']}")


if __name__ == "__main__":
    main()
