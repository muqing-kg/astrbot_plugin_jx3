from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse


_ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "code", "em", "h2", "h3", "h4", "h5",
    "h6", "hr", "i", "img", "li", "ol", "p", "pre", "s", "strong",
    "table", "tbody", "td", "th", "thead", "tr", "u", "ul",
}
_VOID_TAGS = {"br", "hr", "img"}
_DROP_CONTENT_TAGS = {
    "embed", "iframe", "math", "noscript", "object", "script", "style", "svg",
}
_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"alt", "src", "title"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}
_URL_ATTRIBUTES = {"a": "href", "img": "src"}


def _safe_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    if parsed.scheme in {"http", "https", "mailto"}:
        return True
    return not parsed.scheme and not parsed.netloc and not value.strip().startswith("//")


def _safe_attributes(tag: str, attrs: list[tuple[str, str | None]]) -> list[str]:
    allowed = _ALLOWED_ATTRIBUTES.get(tag, set())
    url_attribute = _URL_ATTRIBUTES.get(tag)
    values = {name.lower(): value for name, value in attrs}
    if url_attribute and not (values.get(url_attribute) and _safe_url(values[url_attribute])):
        return []
    output = []
    for name, value in attrs:
        name = name.lower()
        if name not in allowed or value is None:
            continue
        if name in _URL_ATTRIBUTES.values() and not _safe_url(value):
            continue
        output.append(f'{name}="{escape(value, quote=True)}"')
    return output


class _AllowlistHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.drop_depth = 0
        self.open_tags: list[str] = []
        self.suppressed_end_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.drop_depth:
            if tag in _DROP_CONTENT_TAGS:
                self.drop_depth += 1
            return
        if tag in _DROP_CONTENT_TAGS:
            self.drop_depth += 1
            return
        if tag not in _ALLOWED_TAGS:
            return
        attributes = _safe_attributes(tag, attrs)
        if tag in _URL_ATTRIBUTES and not attributes:
            return
        self.open_tags.append(tag)
        attribute_text = (" " + " ".join(attributes)) if attributes else ""
        if tag in _VOID_TAGS:
            self.parts.append(f"<{tag}{attribute_text}>")
        else:
            self.parts.append(f"<{tag}{attribute_text}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.suppressed_end_tags and self.suppressed_end_tags[-1] == tag:
            self.suppressed_end_tags.pop()
            return
        if self.drop_depth:
            if tag in _DROP_CONTENT_TAGS:
                self.drop_depth -= 1
            return
        if self.open_tags and self.open_tags[-1] == tag:
            self.open_tags.pop()
            self.parts.append(f"</{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _VOID_TAGS:
            self.handle_starttag(tag, attrs)
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if not self.drop_depth:
            self.parts.append(escape(data, quote=False))

    def result(self) -> str:
        return "".join(self.parts)


def sanitize_html(html: str) -> str:
    """Render upstream HTML through a small formatting-tag allowlist."""
    parser = _AllowlistHTMLParser()
    parser.feed(html or "")
    parser.close()
    return parser.result()
