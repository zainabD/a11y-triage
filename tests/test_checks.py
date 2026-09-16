"""Each check gets a failing case and a passing case.

A test that only proves the check fires is half a test: the common bug in an
accessibility linter is a false positive, because a tool that cries wolf gets
switched off.
"""

import pytest
from bs4 import BeautifulSoup

from a11y_triage import checks
from a11y_triage.findings import Impact


def soup(html):
    return BeautifulSoup(html, "html.parser")


# --- 1.1.1 images ---------------------------------------------------------

def test_image_without_alt_is_reported():
    found = checks.check_images_have_alt(soup('<img src="cat.png">'))
    assert len(found) == 1
    assert found[0].criterion.number == "1.1.1"


def test_empty_alt_is_allowed():
    """alt="" is the correct way to mark a decorative image, not a violation."""
    assert checks.check_images_have_alt(soup('<img src="line.png" alt="">')) == []


def test_images_are_counted_together():
    found = checks.check_images_have_alt(soup("<img src=a><img src=b><img src=c>"))
    assert found[0].count == 3


# --- 3.3.2 form labels ----------------------------------------------------

def test_input_without_label_is_a_blocker():
    found = checks.check_inputs_have_labels(soup('<input type="text" id="email">'))
    assert found[0].impact is Impact.BLOCKER


@pytest.mark.parametrize(
    "html",
    [
        '<label for="e">Email</label><input id="e">',
        "<label>Email <input></label>",
        '<input aria-label="Email">',
        '<span id="l">Email</span><input aria-labelledby="l">',
    ],
)
def test_all_valid_labelling_methods_pass(html):
    assert checks.check_inputs_have_labels(soup(html)) == []


def test_submit_button_needs_no_label():
    assert checks.check_inputs_have_labels(soup('<input type="submit" value="Go">')) == []


# --- 1.3.1 headings -------------------------------------------------------

def test_skipped_heading_level_is_reported():
    found = checks.check_heading_order(soup("<h1>A</h1><h3>B</h3>"))
    assert any("skip" in f.message for f in found)


def test_sequential_headings_pass():
    assert checks.check_heading_order(soup("<h1>A</h1><h2>B</h2><h3>C</h3>")) == []


def test_missing_h1_is_reported():
    found = checks.check_heading_order(soup("<h2>A</h2><h3>B</h3>"))
    assert any("no h1" in f.message for f in found)


def test_page_with_no_headings_is_not_penalised():
    assert checks.check_heading_order(soup("<p>text</p>")) == []


# --- 3.1.1 / 2.4.2 document ----------------------------------------------

def test_missing_lang_is_reported():
    assert len(checks.check_html_lang(soup("<html><body></body></html>"))) == 1


def test_lang_present_passes():
    assert checks.check_html_lang(soup('<html lang="en"></html>')) == []


def test_empty_title_is_reported():
    assert len(checks.check_page_title(soup("<title>   </title>"))) == 1


def test_title_present_passes():
    assert checks.check_page_title(soup("<title>Checkout</title>")) == []


# --- 2.4.4 / 4.1.2 links and controls ------------------------------------

@pytest.mark.parametrize("text", ["click here", "Read More", "HERE", "learn more"])
def test_vague_link_text_is_reported(text):
    found = checks.check_link_purpose(soup(f'<a href="/x">{text}</a>'))
    assert any(f.criterion.number == "2.4.4" for f in found)


def test_descriptive_link_passes():
    assert checks.check_link_purpose(soup('<a href="/p">2026 annual report</a>')) == []


def test_icon_only_link_is_a_blocker():
    found = checks.check_link_purpose(soup('<a href="/x"><svg></svg></a>'))
    assert found[0].impact is Impact.BLOCKER


def test_icon_link_with_aria_label_passes():
    assert checks.check_link_purpose(soup('<a href="/x" aria-label="Search"><svg></svg></a>')) == []


def test_unnamed_button_is_a_blocker():
    assert checks.check_button_names(soup("<button></button>"))[0].impact is Impact.BLOCKER


def test_named_button_passes():
    assert checks.check_button_names(soup("<button>Save</button>")) == []


# --- 2.4.3 / 2.4.1 keyboard ----------------------------------------------

def test_positive_tabindex_is_reported():
    assert len(checks.check_positive_tabindex(soup('<div tabindex="3"></div>'))) == 1


@pytest.mark.parametrize("value", ["0", "-1"])
def test_zero_and_negative_tabindex_pass(value):
    assert checks.check_positive_tabindex(soup(f'<div tabindex="{value}"></div>')) == []


def test_skip_link_present_passes():
    html = '<a href="#main">Skip to main content</a><nav></nav><main></main>'
    assert checks.check_skip_link(soup(html)) == []


def test_missing_skip_link_reported_when_nav_exists():
    assert len(checks.check_skip_link(soup("<nav><a href=/a>A</a></nav><main></main>"))) == 1


# --- ordering -------------------------------------------------------------

def test_findings_are_sorted_worst_first():
    html = '<html><body><img src="a"><input id="x"><h1>T</h1></body></html>'
    found = checks.audit(html)
    impacts = [f.impact for f in found]
    assert impacts == sorted(impacts, reverse=True)


def test_more_widespread_issues_rank_first_within_impact():
    html = "<html><body>" + "<img src=a>" * 5 + "<title></title></body></html>"
    found = checks.audit(html)
    serious = [f for f in found if f.impact is Impact.SERIOUS]
    assert serious[0].count >= serious[-1].count


def test_clean_page_produces_no_findings():
    html = """<html lang="en"><head><title>Contact</title></head><body>
    <a href="#main">Skip to main content</a>
    <nav><a href="/about">About us</a></nav>
    <main><h1>Contact</h1><h2>By email</h2>
    <img src="logo.png" alt="Acme">
    <label for="e">Your email</label><input id="e" type="email">
    <button>Send</button></main></body></html>"""
    assert checks.audit(html) == []
