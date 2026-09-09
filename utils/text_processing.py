"""Text processing utilities for sentence splitting and word timing."""

import re


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences.

    Handles Russian and English sentence boundaries.
    """
    if not text or not text.strip():
        return []

    # Split on sentence end punctuation, allowing 0+ spaces and optional closing quote »/"/'
    # e.g. '«Производство».Иерархия' -> two sentences (no space after period)
    pattern = r'(?<=[.!?…»"\'])\s*(?=[А-ЯA-Z\d«"\'(])'
    # Fallback: also split on period/semicolon directly if no lookahead match
    if re.search(r'[.!?…][А-ЯA-Z]', text):
        text = re.sub(r'([.!?…])(?=[А-ЯA-Z])', r'\1 ', text)
    sentences = re.split(pattern, text.strip())

    # Filter out empty sentences
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences


def split_into_words(text: str) -> list[str]:
    """Split text into words."""
    if not text:
        return []
    return re.findall(r"\b\w+\b", text)


def calculate_word_timings(
    sentence: str, duration: float
) -> list[tuple[str, float, float]]:
    """Calculate approximate word timings based on sentence duration.

    Distributes duration proportionally to word length.
    Returns list of (word, start_time, end_time) tuples.
    """
    words = split_into_words(sentence)
    if not words:
        return []

    # Calculate total character length for weighting
    total_length = sum(len(word) for word in words)
    if total_length == 0:
        # Equal distribution
        word_duration = duration / len(words)
        return [
            (word, i * word_duration, (i + 1) * word_duration)
            for i, word in enumerate(words)
        ]

    timings = []
    current_time = 0.0

    for word in words:
        # Duration proportional to word length
        word_duration = (len(word) / total_length) * duration
        start_time = current_time
        end_time = current_time + word_duration
        timings.append((word, start_time, end_time))
        current_time = end_time

    return timings


def clean_text(text: str) -> str:
    """Clean and normalize text for TTS processing."""
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove control characters except newlines
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Normalize quotes
    text = text.replace("«", '"').replace("»", '"')
    text = text.replace("„", '"').replace('"', '"')
    return text.strip()


def estimate_speech_duration(text: str, words_per_minute: int = 150) -> float:
    """Estimate speech duration in seconds based on word count."""
    words = split_into_words(text)
    word_count = len(words)
    return (word_count / words_per_minute) * 60


def get_text_statistics(text: str) -> dict:
    """Get statistics about the text."""
    sentences = split_into_sentences(text)
    words = split_into_words(text)
    chars = len(text)

    return {
        "sentences": len(sentences),
        "words": len(words),
        "characters": chars,
        "estimated_duration": estimate_speech_duration(text),
    }
