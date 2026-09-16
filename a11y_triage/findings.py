"""The shape of a finding, and how findings get ranked.

Detection is the easy half. Most accessibility tools stop there and hand you
200 undifferentiated violations, which is the same failure mode as a
vulnerability scanner that reports every missing header at the same severity as
an unauthenticated RCE. The useful half is deciding what to fix first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Impact(IntEnum):
    """How badly a violation blocks someone.

    Ordered so that sorting puts the worst first. The scale is deliberately
    about *user consequence*, not how easy the fix is.
    """

    BLOCKER = 4   # a user relying on assistive tech cannot complete the task
    SERIOUS = 3   # the task is possible but significantly harder
    MODERATE = 2  # confusing or inconsistent, workable
    MINOR = 1     # a polish issue


@dataclass(frozen=True)
class Criterion:
    """A WCAG success criterion."""

    number: str   # e.g. "1.1.1"
    name: str     # e.g. "Non-text Content"
    level: str    # "A" or "AA"

    def __str__(self) -> str:
        return f"WCAG {self.number} {self.name} (Level {self.level})"


@dataclass
class Finding:
    criterion: Criterion
    impact: Impact
    message: str
    snippet: str
    # How many identical instances of this problem were found on the page.
    # One missing alt attribute is a bug; forty is a process failure, and the
    # remediation advice is different.
    count: int = 1
    remediation: str | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def priority(self) -> tuple:
        """Sort key: worst impact first, then most widespread, then Level A."""
        return (-self.impact, -self.count, self.criterion.level != "A")
