"""Module for text processing, cleaning, and quality validation."""

import re

from engine.annotation import constants


def _remove_code_blocks(note: str) -> str:
    """
    Remove code blocks and inline code from the note.

    Args:
        note: The note string to process.

    Returns:
        The note string with code blocks and inline code removed.
    """
    note = re.sub(r"```.*?```", "", note, flags=re.DOTALL)
    note = re.sub(r"`[^`]+`", "", note)
    return note.strip()


def _replace_repetitive_phrases(note: str) -> str:
    """
    Replace repetitive phrases in the note with improved versions.

    Args:
        note: The note string to process.

    Returns:
        The note string with repetitive phrases replaced.
    """
    improved_note = note
    for old_phrase, new_phrase in constants.REPETITIVE_PHRASES_MAP.items():
        improved_note = improved_note.replace(old_phrase, new_phrase)
    return improved_note


def _remove_code_patterns(note: str) -> str:
    """
    Remove specific code patterns that might have slipped through.

    Args:
        note: The note string to process.

    Returns:
        The note string with code patterns removed.
    """
    patterns = [
        r"class\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\{[^}]*\}",
        r"def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*:[^:]*:",
        r"function\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*\{[^}]*\}",
        r"import\s+[^;]+;",
        r"from\s+[^;]+;",
    ]
    for pattern in patterns:
        note = re.sub(pattern, "", note)
    return note


def _remove_redundant_sentences(note: str) -> str:
    """
    Remove redundant sentences from the note.

    Args:
        note: The note string to process.

    Returns:
        The note string with redundant sentences removed.
    """
    sentences = note.split(". ")
    unique_sentences: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and sentence not in unique_sentences:
            is_redundant = False
            for existing in unique_sentences:
                if (
                    len(set(sentence.lower().split()) & set(existing.lower().split()))
                    > 3
                ):
                    is_redundant = True
                    break
            if not is_redundant:
                unique_sentences.append(sentence)
    improved_note = ". ".join(unique_sentences)
    if improved_note and not improved_note.endswith("."):
        improved_note += "."
    return improved_note


def _truncate_note(note: str) -> str:
    """Truncates the note, now using centralized constants."""
    if len(note) > constants.NOTE_MAX_LENGTH:
        sentences = note.split(". ")
        if len(sentences) > constants.NOTE_MAX_SENTENCES:
            note = ". ".join(sentences[: constants.NOTE_MAX_SENTENCES]) + "."
    return note


def validate_editorial_note_quality(note: str) -> str:
    """
    Validates and improves the quality of a generated editorial note.

    Args:
        note: The original editorial note
    Returns:
        Improved editorial note
    """
    if not note or len(note.strip()) < constants.NOTE_MIN_LENGTH:
        return note
    note = _remove_code_blocks(note)
    note = _remove_code_patterns(note)
    note = _replace_repetitive_phrases(note)
    note = _remove_redundant_sentences(note)
    note = _truncate_note(note)
    note = note.replace("`", "")
    note = " ".join(note.split())
    return note
