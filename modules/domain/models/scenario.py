import json
from typing import Self, TextIO

__all__ = ["ScenarioProperty"]


class ScenarioProperty:
    def __init__(self, title: str, author: str) -> None:
        self.title = title
        self.author = author

    @classmethod
    def from_file(cls, file: TextIO) -> Self:
        meta = json.load(file)
        return cls(title=meta.get("title", ""), author=meta.get("author", ""))

    @classmethod
    def from_path(cls, path: str) -> Self:
        with open(path, encoding="utf-8") as file:
            return cls.from_file(file)
