import re
from dataclasses import dataclass
from typing import Final

_TOKEN_PATTERN: Final = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class CandidateCase:
    case_id: str
    root_cause: str
    observed_features: tuple[str, ...]
    verification_steps: tuple[str, ...]
    fix: tuple[str, ...]
    waveform_references: tuple[str, ...]
    created_at_sort_key: str


@dataclass(frozen=True)
class RankedCandidateCase:
    case: CandidateCase
    confidence: float
    observed_match_tokens: tuple[str, ...]
    waveform_match_tokens: tuple[str, ...]


def rank_candidate_cases(
    cases: tuple[CandidateCase, ...],
    *,
    observed_features: tuple[str, ...],
    waveform_features: tuple[str, ...],
    limit: int = 3,
) -> tuple[RankedCandidateCase, ...]:
    """Rank verified cases using deterministic token overlap only.

    The score is a retrieval heuristic. It is intentionally not a probability,
    safety margin, or engineering confidence claim.
    """

    observed_tokens = _tokens(observed_features)
    waveform_tokens = _tokens(waveform_features)
    query_tokens = observed_tokens | waveform_tokens
    ranked: list[RankedCandidateCase] = []
    for case in cases:
        case_tokens = _tokens(
            (
                case.root_cause,
                *case.observed_features,
                *case.verification_steps,
                *case.fix,
            )
        )
        matched_tokens = query_tokens & case_tokens
        score = (
            len(matched_tokens) / len(query_tokens | case_tokens)
            if query_tokens and case_tokens
            else 0.0
        )
        ranked.append(
            RankedCandidateCase(
                case=case,
                confidence=score,
                observed_match_tokens=tuple(sorted(observed_tokens & case_tokens)),
                waveform_match_tokens=tuple(sorted(waveform_tokens & case_tokens)),
            )
        )

    ranked.sort(key=lambda item: item.case.created_at_sort_key, reverse=True)
    ranked.sort(key=lambda item: item.confidence, reverse=True)
    return tuple(ranked[:limit])


def _tokens(values: tuple[str, ...]) -> set[str]:
    return {
        token.casefold()
        for value in values
        for token in _TOKEN_PATTERN.findall(value)
    }
