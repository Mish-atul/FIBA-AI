"""Query parser for FIBA AI action retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

try:
    import spacy
except ImportError:  # pragma: no cover - optional dependency
    spacy = None


@dataclass
class QueryResult:
    raw_query: str
    action_verb: str
    action_category: str
    object_noun: str
    tool_noun: Optional[str]


VERB_CATEGORY_MAP = {
    "cut": "CUT",
    "cutting": "CUT",
    "chop": "CUT",
    "chopping": "CUT",
    "slice": "CUT",
    "slicing": "CUT",
    "dice": "CUT",
    "dicing": "CUT",
    "open": "OPEN",
    "opening": "OPEN",
    "unscrew": "OPEN",
    "unscrewing": "OPEN",
    "unlock": "OPEN",
    "peel": "OPEN",
    "peeling": "OPEN",
    "pour": "POUR",
    "pouring": "POUR",
    "fill": "POUR",
    "filling": "POUR",
    "drain": "POUR",
    "draining": "POUR",
    "pick": "PICK",
    "picking": "PICK",
    "grab": "PICK",
    "grabbing": "PICK",
    "take": "PICK",
    "taking": "PICK",
    "place": "PLACE",
    "placing": "PLACE",
    "put": "PLACE",
    "putting": "PLACE",
    "set": "PLACE",
    "drop": "PLACE",
    "dropping": "PLACE",
    "mix": "MIX",
    "mixing": "MIX",
    "stir": "MIX",
    "stirring": "MIX",
    "shake": "MIX",
    "shaking": "MIX",
    "blend": "MIX",
    "close": "CLOSE",
    "closing": "CLOSE",
    "shut": "CLOSE",
    "cap": "CLOSE",
    "cover": "CLOSE",
    "covering": "CLOSE",
    "seal": "CLOSE",
}

CATEGORY_TOOL_MAP = {
    "CUT": "knife",
    "OPEN": None,
    "POUR": None,
    "PICK": None,
    "PLACE": None,
    "MIX": "spoon",
    "CLOSE": None,
}

TOOL_WORDS = {"knife", "spoon", "fork", "scissors", "hand", "finger"}
STOP_WORDS = {
    "a",
    "an",
    "the",
    "some",
    "my",
    "with",
    "using",
    "from",
    "into",
    "onto",
    "off",
    "up",
    "down",
    "is",
    "are",
    "be",
}

_SPACY_MODEL = "en_core_web_sm"
_NLP = None
_SPACY_LOAD_ATTEMPTED = False


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"\b[a-zA-Z]+\b", text.lower().strip())
    return [tok for tok in tokens if tok not in STOP_WORDS]


def _load_spacy_model():
    global _NLP
    global _SPACY_LOAD_ATTEMPTED
    if _SPACY_LOAD_ATTEMPTED:
        return _NLP
    _SPACY_LOAD_ATTEMPTED = True

    if spacy is None:
        return None

    try:
        _NLP = spacy.load(_SPACY_MODEL)
    except Exception:
        _NLP = None
    return _NLP


def _parse_with_spacy(raw_query: str, tokens: list[str]) -> Optional[QueryResult]:
    nlp = _load_spacy_model()
    if nlp is None:
        return None

    doc = nlp(raw_query)
    action_verb = None
    action_category = None
    verb_index = None

    for token in doc:
        txt = token.text.lower()
        lemma = token.lemma_.lower()
        if token.pos_ in {"VERB", "AUX"} or txt in VERB_CATEGORY_MAP or lemma in VERB_CATEGORY_MAP:
            if txt in VERB_CATEGORY_MAP:
                action_verb = txt
            elif lemma in VERB_CATEGORY_MAP:
                action_verb = lemma
            else:
                action_verb = txt
            action_category = VERB_CATEGORY_MAP.get(action_verb, "UNKNOWN")
            verb_index = token.i
            break

    if action_verb is None:
        if tokens:
            action_verb = tokens[0]
            action_category = VERB_CATEGORY_MAP.get(action_verb, "UNKNOWN")
        else:
            action_verb = "unknown"
            action_category = "UNKNOWN"

    object_noun = None
    if verb_index is not None:
        for token in doc:
            if token.i <= verb_index:
                continue
            if token.pos_ in {"NOUN", "PROPN"}:
                candidate = token.lemma_.lower() if token.lemma_ else token.text.lower()
                if candidate and candidate not in STOP_WORDS:
                    object_noun = candidate
                    break

    if object_noun is None:
        fallback_tokens = tokens[1:] if tokens else []
        object_noun = fallback_tokens[0] if fallback_tokens else "object"

    tool_noun = CATEGORY_TOOL_MAP.get(action_category)
    for token in tokens:
        if token in TOOL_WORDS:
            tool_noun = token
            break

    return QueryResult(
        raw_query=raw_query,
        action_verb=action_verb,
        action_category=action_category,
        object_noun=object_noun,
        tool_noun=tool_noun,
    )


def _parse_with_regex(raw_query: str, tokens: list[str]) -> QueryResult:
    action_verb = "unknown"
    action_category = "UNKNOWN"
    verb_idx = -1

    for idx, token in enumerate(tokens):
        if token in VERB_CATEGORY_MAP:
            action_verb = token
            action_category = VERB_CATEGORY_MAP[token]
            verb_idx = idx
            break

    if action_verb == "unknown" and tokens:
        action_verb = tokens[0]
        action_category = VERB_CATEGORY_MAP.get(action_verb, "UNKNOWN")
        verb_idx = 0

    remaining = tokens[verb_idx + 1 :] if verb_idx >= 0 else tokens
    object_noun = remaining[0] if remaining else "object"

    tool_noun = CATEGORY_TOOL_MAP.get(action_category)
    for token in remaining[1:]:
        if token in TOOL_WORDS:
            tool_noun = token
            break

    return QueryResult(
        raw_query=raw_query,
        action_verb=action_verb,
        action_category=action_category,
        object_noun=object_noun,
        tool_noun=tool_noun,
    )


def parse_query(query_text: str) -> QueryResult:
    """Parse natural language query into action/object/tool components."""
    if not isinstance(query_text, str):
        raise TypeError("query_text must be a string")

    cleaned = query_text.strip()
    if not cleaned:
        return QueryResult(
            raw_query=query_text,
            action_verb="unknown",
            action_category="UNKNOWN",
            object_noun="object",
            tool_noun=None,
        )

    tokens = _tokenize(cleaned)
    spacy_result = _parse_with_spacy(cleaned, tokens)
    if spacy_result is not None:
        return spacy_result
    return _parse_with_regex(cleaned, tokens)


if __name__ == "__main__":
    sample_queries = [
        "cutting onion",
        "opening a box",
        "pouring water into cup",
        "picking up the bottle",
        "mixing ingredients with spoon",
    ]

    for query in sample_queries:
        result = parse_query(query)
        print(f"Query: {query}")
        print(
            "  -> verb=%s (%s), object=%s, tool=%s"
            % (
                result.action_verb,
                result.action_category,
                result.object_noun,
                result.tool_noun,
            )
        )
        print()
