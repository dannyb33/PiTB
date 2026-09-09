import html
import re

import html2text

# Zero-width and other invisible characters marketing emails abuse for hidden
# preheaders and tracking junk: soft hyphen, combining grapheme joiner,
# Mongolian vowel separator, ZWSP, ZWNJ, ZWJ, word joiner, BOM.
_INVISIBLE_RE = re.compile(r"[\u00ad\u034f\u180e\u200b\u200c\u200d\u2060\ufeff]")
_BLANK_RE = re.compile(r"\n{3,}")
_HSPACE_RE = re.compile(r"[^\S\n]+")
_EMPTY_LINK_RE = re.compile(r"!?\[\s*\]\([^)]*\)")  # links with no text


def clean_text(text: str, *, single_line: bool = False, unescape: bool = False) -> str:
    """Normalize email text: drop invisible characters, tidy whitespace.

    single_line: collapse newlines too (for snippets).
    unescape: decode HTML entities (Gmail HTML-escapes snippets).
    """
    if unescape:
        text = html.unescape(text)
    text = _INVISIBLE_RE.sub("", text)
    text = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
    )

    if single_line:
        return _HSPACE_RE.sub(" ", text.replace("\n", " ")).strip()

    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return _BLANK_RE.sub("\n\n", text).strip()


def html_to_text(html_body: str) -> str:
    """Convert an HTML email body to Markdown-ish plain text (html2text)."""
    converter = html2text.HTML2Text()
    converter.body_width = 0  # don't hard-wrap lines
    converter.ignore_images = True  # drop tracking pixels and image clutter
    converter.ignore_tables = True  # table markup is noise in emails
    converter.single_line_break = True  # single newlines, not markdown breaks
    converter.unicode_snob = True  # keep unicode instead of ASCII escapes
    return _EMPTY_LINK_RE.sub("", converter.handle(html_body))
