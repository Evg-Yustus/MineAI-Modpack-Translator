"""Helpers for validating target-language text without misclassifying Latin scripts."""

import re


_SAME_LATIN_SCRIPT_APIS = frozenset({
    "en",
    "es",
    "de",
    "fr",
    "pt",
    "it",
    "pl",
})
_ENGLISH_CLAUSE_WORDS = frozenset({
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "but",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "have",
    "if",
    "in",
    "into",
    "is",
    "it",
    "not",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "when",
    "which",
    "will",
    "with",
    "you",
    "your",
})
_LATIN_WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")


def requires_target_script_marker(target_lang: dict) -> bool:
    """Return True when the target language uses a script distinct from English.

    For same-script Latin targets a regex made only of diacritics is not a reliable
    language detector: valid translations such as ``Espada de hierro`` may contain
    no target-specific accented characters at all. Unknown languages stay strict by
    default so extending the language table cannot silently weaken validation.
    """
    return target_lang.get("api") not in _SAME_LATIN_SCRIPT_APIS


def uses_same_latin_script(target_lang: dict) -> bool:
    return not requires_target_script_marker(target_lang)


def has_untranslated_leading_article(
    source: str,
    candidate: str,
    target_lang: dict,
) -> bool:
    """Detect an English article left before otherwise translated text."""
    if not requires_target_script_marker(target_lang):
        return False
    target_pattern = target_lang.get("regex")
    if not target_pattern or not re.search(target_pattern, candidate):
        return False
    source_match = re.match(r"^\s*(the|an|a)\b", source, flags=re.IGNORECASE)
    candidate_match = re.match(
        r"^\s*(the|an|a)\b",
        candidate,
        flags=re.IGNORECASE,
    )
    return bool(
        source_match
        and candidate_match
        and source_match.group(1).casefold()
        == candidate_match.group(1).casefold()
    )


def has_long_untranslated_english_fragment(
    candidate: str,
    target_lang: dict,
) -> bool:
    """Detect a copied English clause inside a non-Latin translation."""
    if not requires_target_script_marker(target_lang):
        return False
    target_pattern = target_lang.get("regex")
    if not target_pattern or not re.search(target_pattern, candidate):
        return False

    for segment in re.split(r"[^\x00-\x7f]+", candidate):
        words = [word.casefold() for word in _LATIN_WORD.findall(segment)]
        if len(words) < 6:
            continue
        if sum(word in _ENGLISH_CLAUSE_WORDS for word in words) >= 2:
            return True
    return False
