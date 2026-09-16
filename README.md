# a11y-triage

Audit a web page for WCAG violations, then rank them by how badly they block a
real user.

Most accessibility linters stop at detection and hand back a flat list of two
hundred violations. That is the same failure mode as a vulnerability scanner
that reports a missing security header at the same severity as an
unauthenticated remote execution: technically complete, operationally useless.
The hard question is not *what is wrong*, it is *what do I fix first*.

`a11y-triage` answers the second one.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Use

```bash
# a URL or a local file
.venv/bin/python -m a11y_triage.cli https://example.com
.venv/bin/python -m a11y_triage.cli build/index.html

# add a concrete remediation per finding, via Claude
export ANTHROPIC_API_KEY=sk-ant-...
.venv/bin/python -m a11y_triage.cli https://example.com --explain

# write a Markdown report, and fail a build on anything serious or worse
.venv/bin/python -m a11y_triage.cli https://example.com \
    --markdown report.md --fail-on serious
```

Exit code is non-zero when a finding meets `--fail-on` (default `blocker`), so
it drops straight into CI.

## How findings are ranked

Impact is about user consequence, not how hard the fix is.

| Impact | Meaning |
|---|---|
| `BLOCKER` | someone relying on assistive technology cannot complete the task |
| `SERIOUS` | the task is possible but significantly harder |
| `MODERATE` | confusing or inconsistent, still workable |
| `MINOR` | polish |

Within an impact level, more widespread issues rank first. One missing `alt` is
a bug; forty is a process failure, and the remediation is a different
conversation.

## What it checks

Ten checks, each mapped to a specific success criterion.

| Criterion | Check |
|---|---|
| 1.1.1 Non-text Content | `img` with no `alt` attribute |
| 1.3.1 Info and Relationships | heading level skips, missing `h1` |
| 2.4.1 Bypass Blocks | no skip link ahead of navigation |
| 2.4.2 Page Titled | missing or empty `title` |
| 2.4.3 Focus Order | positive `tabindex` |
| 2.4.4 Link Purpose | "click here", "read more", empty link text |
| 3.1.1 Language of Page | missing `lang` on `html` |
| 3.3.2 Labels or Instructions | form control with no associated label |
| 4.1.2 Name, Role, Value | unnamed `button`, untitled `iframe` |

## What it deliberately does not check

Colour contrast, focus visibility, reflow at 320 px, and anything else that
needs a rendering engine. Those are real criteria and they are not guessable
from markup. A confident wrong finding costs more reviewer trust than a missing
one, so the tool says nothing rather than guessing.

**A clean run is not a conformance claim.** It means the static checks found
nothing, which is the floor, not the ceiling.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

Every check has both a failing and a passing case. The common bug in a linter
is the false positive, because a tool that cries wolf gets switched off.

## Background

Built by Zainab Alsidiki. I spent seven years on a platform of 200+ production
sites, developing to Section 508, which incorporates WCAG 2.0 Level AA, and
running a security remediation cadence of 7 to 10 findings a month. The triage
model here comes from that second half: the scanner output was never the
bottleneck, deciding what mattered was.
