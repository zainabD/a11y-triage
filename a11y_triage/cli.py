"""Command line entry point."""

from __future__ import annotations

import argparse
import pathlib
import sys

from . import __version__, ai
from .checks import audit
from .findings import Impact
from .report import to_markdown, to_terminal


def _load(target: str) -> tuple[str, str]:
    """Return (html, label) for a URL or a local file path."""
    if target.startswith(("http://", "https://")):
        import httpx

        response = httpx.get(target, follow_redirects=True, timeout=20.0)
        response.raise_for_status()
        return response.text, target
    path = pathlib.Path(target)
    if not path.is_file():
        raise SystemExit(f"Not a URL or a readable file: {target}")
    return path.read_text(encoding="utf-8", errors="replace"), str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="a11y-triage",
        description="Audit a page for WCAG violations and rank them by user impact.",
    )
    parser.add_argument("target", help="URL or path to an HTML file")
    parser.add_argument(
        "--explain",
        action="store_true",
        help="use Claude to add a concrete remediation per finding (needs ANTHROPIC_API_KEY)",
    )
    parser.add_argument("--model", default=ai.DEFAULT_MODEL, help="Claude model for --explain")
    parser.add_argument("--markdown", metavar="FILE", help="also write a Markdown report")
    parser.add_argument(
        "--fail-on",
        choices=[i.name.lower() for i in Impact],
        default="blocker",
        help="exit non-zero if any finding is at least this severe (default: blocker)",
    )
    parser.add_argument("--version", action="version", version=f"a11y-triage {__version__}")
    args = parser.parse_args(argv)

    html, label = _load(args.target)
    findings = audit(html)

    if args.explain:
        if not ai.is_available():
            print("  (--explain needs ANTHROPIC_API_KEY; continuing without it)")
        else:
            findings = ai.enrich(findings, model=args.model)

    print(to_terminal(findings, label))

    if args.markdown:
        pathlib.Path(args.markdown).write_text(to_markdown(findings, label), encoding="utf-8")
        print(f"\nWrote {args.markdown}")

    threshold = Impact[args.fail_on.upper()]
    return 1 if any(f.impact >= threshold for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
