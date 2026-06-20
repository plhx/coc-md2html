import base64
import binascii
import html
import unicodedata
from typing import Self, Sequence, TextIO

from .markdown import NamedMarkdown

__all__ = ["PageBuilder", "Template"]


class Template:
    def __init__(self, content: str) -> None:
        self.content = content

    @classmethod
    def from_file(cls, file: TextIO) -> Self:
        return cls(file.read())

    @classmethod
    def from_path(cls, path: str) -> Self:
        with open(path, encoding="utf-8") as file:
            return cls.from_file(file)


class PageBuilder:
    def __init__(self) -> None:
        self.title: str | None = None
        self.template: Template | None = None

    def set_title(self, title: str) -> Self:
        self.title = title
        return self

    def set_template(self, template: Template) -> Self:
        self.template = template
        return self

    def build(self, files: Sequence[NamedMarkdown]) -> str:
        # タイトルとテンプレートファイルがあることが前提
        if self.title is None:
            raise RuntimeError("タイトルが指定されていません")
        if self.template is None:
            raise RuntimeError("テンプレートファイルが指定されていません")
        content = self.template.content.replace("<!-- MD -->", self._build_pages(files))
        content = content.replace("<!-- TITLE -->", html.escape(self.title, quote=True))
        title_css = self._to_css_string(self.title)
        # 既定のスタイルシートを追加する
        content = content.replace(
            "<!-- STYLE -->",
            f"""<style>
@page :left {{
    @bottom-left {{
        content: {title_css};
        font-size: var(--bulma-size-7);
        font-style: italic;
        font-family: "Yu Mincho", "YuMincho", "Hiragino Mincho ProN", "Noto Serif JP", serif;
        color: var(--bulma-grey);
    }}
}}

@page :right {{
    @bottom-left {{
        content: {title_css};
        font-size: var(--bulma-size-7);
        font-style: italic;
        font-family: "Yu Mincho", "YuMincho", "Hiragino Mincho ProN", "Noto Serif JP", serif;
        color: var(--bulma-grey);
    }}
}}
</style>
""",
        )
        return content

    def _to_css_string(self, text: str) -> str:
        escaped: list[str] = []
        for ch in text:
            if ch == "\\":
                escaped.append("\\\\")
                continue
            if ch == "'":
                escaped.append("\\'")
                continue
            code = ord(ch)
            if 0x20 <= code <= 0x7E:
                escaped.append(ch)
            else:
                escaped.append(f"\\{code:X} ")
        return "'" + "".join(escaped) + "'"

    def _build_pages(self, files: Sequence[NamedMarkdown]) -> str:
        # ファイル番号でソートして埋め込む
        files = sorted(files, key=lambda x: x.index)
        pages: list[str] = []
        for file in files:
            name_norm = unicodedata.normalize("NFC", file.name.rstrip(".md"))
            name_hex = binascii.hexlify(name_norm.encode("utf-8")).decode("ascii")
            anchor = f'<div id="{name_hex}"></div>'
            pages.append(f"{anchor}\n\n{file.content}")
        # 最後にページ区切りで連結する
        page_content = "\n\n--------\n".join(pages)
        page_content_utf8 = page_content.encode("utf-8", page_content)
        # 最後にBase64形式で埋め込む
        return base64.b64encode(page_content_utf8).decode("ascii")
