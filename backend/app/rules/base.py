from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.review import Finding, ReviewContext


class ReviewRule(ABC):
    """Base contract for one deterministic review rule."""

    rule_id: str
    category: str
    title: str

    @abstractmethod
    def evaluate(
        self,
        context: ReviewContext,
        prior_findings: Sequence[Finding] = (),
    ) -> Finding:
        """Evaluate the rule without external state or LLM dependencies."""

