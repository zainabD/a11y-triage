"""Static WCAG checks against parsed HTML.

Every check here maps to a specific success criterion and only reports what can
be determined from markup alone. Anything requiring rendering (colour contrast,
focus visibility, reflow at 320px) is deliberately out of scope rather than
guessed at: a confident wrong finding costs more reviewer trust than a missing
one.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from .findings import Criterion, Finding, Impact

NON_TEXT_CONTENT = Criterion("1.1.1", "Non-text Content", "A")
INFO_RELATIONSHIPS = Criterion("1.3.1", "Info and Relationships", "A")
BYPASS_BLOCKS = Criterion("2.4.1", "Bypass Blocks", "A")
PAGE_TITLED = Criterion("2.4.2", "Page Titled", "A")
LINK_PURPOSE = Criterion("2.4.4", "Link Purpose (In Context)", "A")
LANGUAGE_OF_PAGE = Criterion("3.1.1", "Language of Page", "A")
LABELS_OR_INSTRUCTIONS = Criterion("3.3.2", "Labels or Instructions", "A")
NAME_ROLE_VALUE = Criterion("4.1.2", "Name, Role, Value", "A")
FOCUS_ORDER = Criterion("2.4.3", "Focus Order", "A")

# Link text that carries no meaning once a screen reader user pulls the page's
# links out of context, which is exactly how many of them navigate.
VAGUE_LINK_TEXT = {
    "click here", "here", "read more", "more", "learn more",
    "this link", "link", "details", "continue", "go",
}

# Inputs that do not need a visible label to be operable.
UNLABELLED_OK = {"hidden", "submit", "reset", "button", "image"}


def _snippet(tag, limit: int = 120) -> str:
    text = " ".join(str(tag).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _accessible_name(tag) -> str:
    """Approximate the accessible name of an element.

    This is a simplification of the real accname algorithm: enough to catch a
    control that has no name at all, which is the failure worth reporting.
    """
    for attr in ("aria-label", "title", "alt"):
        if tag.get(attr, "").strip():
            return tag[attr].strip()
    if tag.get("aria-labelledby", "").strip():
        return "(aria-labelledby)"
    return tag.get_text(strip=True)


def check_images_have_alt(soup: BeautifulSoup) -> list[Finding]:
    """1.1.1 - every img needs an alt attribute, even if empty."""
    missing = [img for img in soup.find_all("img") if img.get("alt") is None]
    if not missing:
        return []
    return [
        Finding(
            criterion=NON_TEXT_CONTENT,
            impact=Impact.SERIOUS,
            message=(
                f"{len(missing)} image(s) have no alt attribute. A screen reader "
                "falls back to announcing the filename, or skips the image with "
                "no indication anything was there."
            ),
            snippet=_snippet(missing[0]),
            count=len(missing),
            tags=["images", "screen-reader"],
        )
    ]


def check_inputs_have_labels(soup: BeautifulSoup) -> list[Finding]:
    """1.3.1 / 3.3.2 - a form control needs a programmatically associated label.

    Visual proximity is not association. A label sitting next to an input looks
    fine and tells assistive technology nothing.
    """
    label_targets = {
        lab["for"].strip() for lab in soup.find_all("label") if lab.get("for")
    }
    unlabelled = []
    for control in soup.find_all(["input", "select", "textarea"]):
        if control.name == "input" and control.get("type", "text").lower() in UNLABELLED_OK:
            continue
        if control.get("id", "").strip() in label_targets:
            continue
        if control.find_parent("label") is not None:
            continue
        if control.get("aria-label", "").strip() or control.get("aria-labelledby", "").strip():
            continue
        unlabelled.append(control)

    if not unlabelled:
        return []
    return [
        Finding(
            criterion=LABELS_OR_INSTRUCTIONS,
            impact=Impact.BLOCKER,
            message=(
                f"{len(unlabelled)} form control(s) have no associated label. A "
                "screen reader user hears an unlabelled edit field and cannot "
                "know what to type, which blocks the form outright."
            ),
            snippet=_snippet(unlabelled[0]),
            count=len(unlabelled),
            tags=["forms", "blocker"],
        )
    ]


def check_heading_order(soup: BeautifulSoup) -> list[Finding]:
    """1.3.1 - heading levels should not skip, and a page needs one h1."""
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    findings: list[Finding] = []

    levels = [int(h.name[1]) for h in headings]
    h1_count = levels.count(1)
    if headings and h1_count == 0:
        findings.append(
            Finding(
                criterion=INFO_RELATIONSHIPS,
                impact=Impact.MODERATE,
                message=(
                    "The page has headings but no h1. Screen reader users "
                    "navigate by heading level, so the document has no anchor."
                ),
                snippet=_snippet(headings[0]),
                tags=["headings", "structure"],
            )
        )

    skips = []
    previous = None
    for tag, level in zip(headings, levels):
        if previous is not None and level > previous + 1:
            skips.append((tag, previous, level))
        previous = level
    if skips:
        tag, was, now = skips[0]
        findings.append(
            Finding(
                criterion=INFO_RELATIONSHIPS,
                impact=Impact.MODERATE,
                message=(
                    f"{len(skips)} heading level skip(s), e.g. h{was} followed "
                    f"directly by h{now}. Skipped levels imply a section that "
                    "does not exist and break outline navigation."
                ),
                snippet=_snippet(tag),
                count=len(skips),
                tags=["headings", "structure"],
            )
        )
    return findings


def check_html_lang(soup: BeautifulSoup) -> list[Finding]:
    """3.1.1 - the html element needs a valid lang attribute."""
    html = soup.find("html")
    if html is not None and html.get("lang", "").strip():
        return []
    return [
        Finding(
            criterion=LANGUAGE_OF_PAGE,
            impact=Impact.SERIOUS,
            message=(
                "The html element has no lang attribute. A screen reader will "
                "read the page with the wrong pronunciation rules, which can "
                "make English content unintelligible in a Spanish voice."
            ),
            snippet=_snippet(html) if html is not None else "<html>",
            tags=["document", "screen-reader"],
        )
    ]


def check_page_title(soup: BeautifulSoup) -> list[Finding]:
    """2.4.2 - the page needs a non-empty, descriptive title."""
    title = soup.find("title")
    if title is not None and title.get_text(strip=True):
        return []
    return [
        Finding(
            criterion=PAGE_TITLED,
            impact=Impact.SERIOUS,
            message=(
                "The page has no title, or the title is empty. It is the first "
                "thing announced on load and the only label in a tab list."
            ),
            snippet="<title>" if title is None else _snippet(title),
            tags=["document"],
        )
    ]


def check_link_purpose(soup: BeautifulSoup) -> list[Finding]:
    """2.4.4 - link text should describe its destination."""
    vague, empty = [], []
    for link in soup.find_all("a", href=True):
        name = _accessible_name(link)
        if not name:
            empty.append(link)
        elif name.strip().lower().rstrip(" .>…") in VAGUE_LINK_TEXT:
            vague.append(link)

    findings: list[Finding] = []
    if empty:
        findings.append(
            Finding(
                criterion=NAME_ROLE_VALUE,
                impact=Impact.BLOCKER,
                message=(
                    f"{len(empty)} link(s) have no accessible name at all, "
                    "usually an icon-only link. It is announced as just 'link'."
                ),
                snippet=_snippet(empty[0]),
                count=len(empty),
                tags=["links", "blocker"],
            )
        )
    if vague:
        findings.append(
            Finding(
                criterion=LINK_PURPOSE,
                impact=Impact.MODERATE,
                message=(
                    f"{len(vague)} link(s) use non-descriptive text such as "
                    "'click here' or 'read more'. Many screen reader users "
                    "browse a list of links with no surrounding context."
                ),
                snippet=_snippet(vague[0]),
                count=len(vague),
                tags=["links", "content"],
            )
        )
    return findings


def check_button_names(soup: BeautifulSoup) -> list[Finding]:
    """4.1.2 - every button needs an accessible name."""
    unnamed = [b for b in soup.find_all("button") if not _accessible_name(b)]
    if not unnamed:
        return []
    return [
        Finding(
            criterion=NAME_ROLE_VALUE,
            impact=Impact.BLOCKER,
            message=(
                f"{len(unnamed)} button(s) have no accessible name. The control "
                "is reachable but its purpose is unknowable without sight."
            ),
            snippet=_snippet(unnamed[0]),
            count=len(unnamed),
            tags=["controls", "blocker"],
        )
    ]


def check_iframe_titles(soup: BeautifulSoup) -> list[Finding]:
    """4.1.2 - an iframe needs a title describing its contents."""
    untitled = [f for f in soup.find_all("iframe") if not f.get("title", "").strip()]
    if not untitled:
        return []
    return [
        Finding(
            criterion=NAME_ROLE_VALUE,
            impact=Impact.MODERATE,
            message=(
                f"{len(untitled)} iframe(s) have no title attribute. The frame "
                "is announced without any indication of what it contains."
            ),
            snippet=_snippet(untitled[0]),
            count=len(untitled),
            tags=["embeds"],
        )
    ]


def check_positive_tabindex(soup: BeautifulSoup) -> list[Finding]:
    """2.4.3 - a positive tabindex forces focus order out of document order."""
    positive = []
    for tag in soup.find_all(attrs={"tabindex": True}):
        try:
            if int(tag["tabindex"]) > 0:
                positive.append(tag)
        except (TypeError, ValueError):
            continue
    if not positive:
        return []
    return [
        Finding(
            criterion=FOCUS_ORDER,
            impact=Impact.MODERATE,
            message=(
                f"{len(positive)} element(s) use a positive tabindex, which "
                "pulls them out of document order and makes keyboard focus "
                "jump unpredictably across the page."
            ),
            snippet=_snippet(positive[0]),
            count=len(positive),
            tags=["keyboard"],
        )
    ]


def check_skip_link(soup: BeautifulSoup) -> list[Finding]:
    """2.4.1 - a keyboard user needs a way past repeated navigation."""
    has_landmark = bool(
        soup.find("main") or soup.find(attrs={"role": "main"})
    )
    for link in soup.find_all("a", href=True)[:5]:
        if link["href"].startswith("#") and "skip" in _accessible_name(link).lower():
            return []
    if not soup.find("nav") and not has_landmark:
        return []
    return [
        Finding(
            criterion=BYPASS_BLOCKS,
            impact=Impact.MODERATE,
            message=(
                "No skip link found in the first few links. A keyboard user has "
                "to tab through the whole navigation on every page load."
            ),
            snippet="(expected an early anchor such as "
                    '<a href="#main">Skip to main content</a>)',
            tags=["keyboard", "navigation"],
        )
    ]

def check_data_table_headers(soup: BeautifulSoup) -> list[Finding]:
    """1.3.1 - a data table needs th cells so rows and columns are announced."""
    bad = []
    for table in soup.find_all("table"):
        if table.get("role") == "presentation":
            continue          # explicitly a layout table, not data
        if not table.find("th"):
            bad.append(table)
    if not bad:
        return []
    return [
        Finding(
            criterion=INFO_RELATIONSHIPS,
            impact=Impact.SERIOUS,
            message=(
                f"{len(bad)} table(s) have no th cells. A screen reader "
                "announces each cell with no row or column context, so the "
                "data is readable but meaningless."
            ),
            snippet=_snippet(bad[0]),
            count=len(bad),
            tags=["tables", "structure"],
        )
    ]


ALL_CHECKS = (
    check_inputs_have_labels,
    check_button_names,
    check_link_purpose,
    check_images_have_alt,
    check_html_lang,
    check_page_title,
    check_heading_order,
    check_iframe_titles,
    check_positive_tabindex,
    check_skip_link,
    check_data_table_headers,
)


def audit(html: str) -> list[Finding]:
    """Run every check and return findings worst-first."""
    soup = BeautifulSoup(html, "html.parser")
    findings: list[Finding] = []
    for check in ALL_CHECKS:
        findings.extend(check(soup))
    findings.sort(key=lambda f: f.priority)
    return findings
