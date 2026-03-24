"""
Creative MRI text analysis: Python-computed metrics.
Only Flesch-Kincaid reading level — kept as a credibility anchor for outreach
("9.2 on the Flesch-Kincaid scale" sounds more authoritative than LLM-only analysis).
"""
import re
from typing import Any, Dict


def _count_syllables(word: str) -> int:
    """Count syllables using vowel-group heuristic."""
    word = word.lower().strip()
    if not word:
        return 0
    # Remove trailing silent-e
    if word.endswith("e") and len(word) > 2:
        word = word[:-1]
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    return max(1, count)


def _split_sentences(text: str) -> list:
    """Split text into sentences on .!? boundaries."""
    parts = re.split(r'[.!?]+', text)
    return [s.strip() for s in parts if s.strip()]


def _tokenize_words(text: str) -> list:
    """Extract words (letters/apostrophes only)."""
    return re.findall(r"[a-zA-Z']+", text)


def compute_reading_level(text: str) -> Dict[str, Any]:
    """
    Compute Flesch-Kincaid grade level.
    FK grade = 0.39*(words/sentences) + 11.8*(syllables/words) - 15.59

    Returns dict with flesch_kincaid_grade, sentence_count, word_count, syllable_count.
    """
    if not text or not text.strip():
        return {
            "flesch_kincaid_grade": 0.0,
            "sentence_count": 0,
            "word_count": 0,
            "syllable_count": 0,
        }

    sentences = _split_sentences(text)
    words = _tokenize_words(text)
    sentence_count = max(1, len(sentences))
    word_count = len(words)

    if word_count == 0:
        return {
            "flesch_kincaid_grade": 0.0,
            "sentence_count": sentence_count,
            "word_count": 0,
            "syllable_count": 0,
        }

    syllable_count = sum(_count_syllables(w) for w in words)

    fk_grade = (
        0.39 * (word_count / sentence_count)
        + 11.8 * (syllable_count / word_count)
        - 15.59
    )
    # Clamp to reasonable range
    fk_grade = max(0.0, round(fk_grade, 1))

    return {
        "flesch_kincaid_grade": fk_grade,
        "sentence_count": sentence_count,
        "word_count": word_count,
        "syllable_count": syllable_count,
    }
