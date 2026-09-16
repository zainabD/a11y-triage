"""Optional Claude pass that turns findings into remediation guidance.

The checks know *what* is wrong. This adds the part a reviewer actually needs:
a concrete fix for this markup, and an order to work in. It is optional by
design, so the tool still does something useful with no API key configured.
"""

from __future__ import annotations

import os

from .findings import Finding

DEFAULT_MODEL = "claude-sonnet-5"

PROMPT = """You are reviewing accessibility findings for a web page. For each \
finding, give a concrete remediation a developer can act on today.

Rules:
- Be specific to the markup shown. No generic advice.
- Show corrected HTML where markup is the fix.
- If a finding needs a human judgement call (what alt text should say, whether \
an image is decorative), say so plainly instead of inventing content.
- Do not restate the problem. The reader already has it.
- Two or three sentences per finding, plus a code block only when it helps.

Findings:
{findings}

Return one block per finding, in the same order, formatted as:

### <criterion number>
<remediation>
"""


def is_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _format(findings: list[Finding]) -> str:
    lines = []
    for f in findings:
        lines.append(
            f"- {f.criterion} | impact {f.impact.name} | {f.count} instance(s)\n"
            f"  problem: {f.message}\n"
            f"  markup:  {f.snippet}"
        )
    return "\n".join(lines)


def enrich(findings: list[Finding], model: str = DEFAULT_MODEL) -> list[Finding]:
    """Attach remediation text to each finding. Returns findings unchanged on failure."""
    if not findings or not is_available():
        return findings

    try:
        import anthropic
    except ImportError:
        return findings

    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": PROMPT.format(findings=_format(findings))}],
        )
    except Exception as exc:  # network, auth, rate limit: degrade, do not crash
        print(f"  (skipping AI remediation: {type(exc).__name__}: {exc})")
        return findings

    text = "".join(block.text for block in response.content if block.type == "text")
    for finding, section in zip(findings, _split_sections(text)):
        finding.remediation = section
    return findings


def _split_sections(text: str) -> list[str]:
    """Split the response on '### ' headings, keeping only the bodies."""
    parts = text.split("### ")
    bodies = []
    for part in parts[1:]:
        _, _, body = part.partition("\n")
        bodies.append(body.strip())
    return bodies
