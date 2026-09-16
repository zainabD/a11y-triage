"""Terminal and Markdown output."""

from __future__ import annotations

from .findings import Finding, Impact

BADGE = {
    Impact.BLOCKER: "BLOCKER ",
    Impact.SERIOUS: "SERIOUS ",
    Impact.MODERATE: "MODERATE",
    Impact.MINOR: "MINOR   ",
}


def summarise(findings: list[Finding]) -> str:
    if not findings:
        return "No violations found by the static checks."
    counts = {}
    for f in findings:
        counts[f.impact] = counts.get(f.impact, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: -kv[0])
    parts = [f"{n} {BADGE[impact].strip().lower()}" for impact, n in ordered]
    instances = sum(f.count for f in findings)
    return f"{len(findings)} issue types, {instances} instances: " + ", ".join(parts)


def to_terminal(findings: list[Finding], source: str) -> str:
    out = [f"\na11y-triage  {source}", "=" * 72, summarise(findings), ""]
    if not findings:
        out.append(
            "Note: static checks cannot see colour contrast, focus visibility, "
            "or reflow.\nA clean result here is not a conformance claim."
        )
        return "\n".join(out)

    for i, f in enumerate(findings, 1):
        out.append(f"{i}. [{BADGE[f.impact]}] {f.criterion}")
        if f.count > 1:
            out.append(f"   {f.count} instances")
        out.append(f"   {f.message}")
        out.append(f"   markup: {f.snippet}")
        if f.remediation:
            out.append("   fix:")
            for line in f.remediation.splitlines():
                out.append(f"     {line}")
        out.append("")

    out.append("-" * 72)
    out.append(
        "Fix blockers first: they stop a task completely rather than making it "
        "harder.\nStatic checks cannot see colour contrast, focus visibility, "
        "or reflow."
    )
    return "\n".join(out)


def to_markdown(findings: list[Finding], source: str) -> str:
    out = [f"# Accessibility triage: {source}", "", summarise(findings), ""]
    for f in findings:
        out += [
            f"## {BADGE[f.impact].strip()} — {f.criterion}",
            "",
            f"**Instances:** {f.count}",
            "",
            f.message,
            "",
            "```html",
            f.snippet,
            "```",
            "",
        ]
        if f.remediation:
            out += ["**Remediation**", "", f.remediation, ""]
    return "\n".join(out)
