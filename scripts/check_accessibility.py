"""Static accessibility guard for the shipped HTML shell."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class AccessibilityParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []
        self.ids: set[str] = set()
        self.labels_for: set[str] = set()
        self.has_main = False
        self.has_nav = False
        self.has_skip_link = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            self.ids.add(element_id)
        if tag == "main":
            self.has_main = True
        if tag == "nav":
            self.has_nav = True
        if tag == "a" and values.get("href") == "#main-content":
            self.has_skip_link = True
        if tag == "label" and values.get("for"):
            self.labels_for.add(values["for"])
        if tag == "img" and not values.get("alt"):
            self.errors.append("img without alt text")
        if tag == "canvas" and not (values.get("aria-label") or values.get("aria-describedby")):
            self.errors.append("canvas without an accessible name")
        if tag in {"input", "textarea", "select"}:
            if values.get("type") == "hidden":
                return
            if not (values.get("aria-label") or values.get("aria-labelledby") or element_id and element_id in self.labels_for):
                self.errors.append(f"{tag} without label: {element_id or '<anonymous>'}")


def main() -> int:
    html = Path("app/index.html").read_text(encoding="utf-8")
    parser = AccessibilityParser()
    parser.feed(html)
    errors = list(parser.errors)
    if not parser.has_main:
        errors.append("missing main landmark")
    if not parser.has_nav:
        errors.append("missing nav landmark")
    if not parser.has_skip_link:
        errors.append("missing skip link")
    if "lang=\"ru\"" not in html:
        errors.append("document language must be ru")
    if errors:
        print("ACCESSIBILITY STATIC CHECK FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("ACCESSIBILITY STATIC CHECK OK · landmarks, labels, alt text and text language present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
