from app.diagnosis import CandidateCase, rank_candidate_cases


def test_rank_candidate_cases_is_deterministic_and_limits_to_top_three() -> None:
    cases = tuple(
        CandidateCase(
            case_id=str(index),
            root_cause=root_cause,
            observed_features=(observed_feature,),
            verification_steps=("measure again",),
            fix=("review operating point",),
            waveform_references=(),
            created_at_sort_key=f"2026-08-16T00:00:0{index}+00:00",
        )
        for index, (root_cause, observed_feature) in enumerate(
            (
                ("Cause A", "high VDS overshoot"),
                ("Cause B", "low resonant current"),
                ("Cause C", "low resonant current"),
                ("Cause D", "low resonant current"),
            ),
            start=1,
        )
    )

    ranked = rank_candidate_cases(
        cases,
        observed_features=("low resonant current",),
        waveform_features=(),
    )

    assert len(ranked) == 3
    assert [item.case.case_id for item in ranked] == ["4", "3", "2"]
    assert ranked[0].confidence == ranked[1].confidence == ranked[2].confidence
    assert ranked[0].observed_match_tokens == ("current", "low", "resonant")


def test_rank_candidate_cases_marks_missing_feature_match_as_zero_score() -> None:
    case = CandidateCase(
        case_id="case-1",
        root_cause="Insufficient resonant current.",
        observed_features=("low current",),
        verification_steps=("measure current",),
        fix=("review tank",),
        waveform_references=(),
        created_at_sort_key="2026-08-16T00:00:00+00:00",
    )

    ranked = rank_candidate_cases(
        (case,), observed_features=(), waveform_features=()
    )

    assert ranked[0].confidence == 0
    assert ranked[0].observed_match_tokens == ()
