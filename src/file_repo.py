"""Тестовый репозиторий: граф зависимостей из текстового файла.

Формат: по одной строке на пакет, ``A: B C`` - пакет A зависит от B и C.
Имена - заглавные латинские буквы. Пустые строки и строки, начинающиеся
с ``#``, пропускаются.
"""

import re
from pathlib import Path

from errors import RepositoryError
from graph import Ref

NAME_RE = re.compile(r"^[A-Z]+$")
COMMENT_PREFIX = "#"
SEPARATOR = ":"


class FileRepositoryError(RepositoryError):
    """Ошибка чтения или разбора файла тестового репозитория."""


def parse_line(line: str, number: int) -> tuple[str, list[str]]:
    """Разбирает строку вида ``A: B C``."""
    name, separator, rest = line.partition(SEPARATOR)
    if not separator:
        raise FileRepositoryError(f"line {number}: expected 'A: B C'")
    name = name.strip()
    deps = list(dict.fromkeys(rest.split()))
    for item in [name, *deps]:
        if not NAME_RE.match(item):
            raise FileRepositoryError(
                f"line {number}: invalid package name '{item}' "
                "(capital Latin letters only)"
            )
    return name, deps


def parse_table(text: str) -> dict[str, list[str]]:
    """Разбирает весь файл в таблицу: пакет -> его зависимости."""
    table: dict[str, list[str]] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith(COMMENT_PREFIX):
            continue
        name, deps = parse_line(line, number)
        if name in table:
            raise FileRepositoryError(f"line {number}: {name} defined twice")
        table[name] = deps
    return table


def load_table(path: Path) -> dict[str, list[str]]:
    """Читает файл тестового репозитория."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        raise FileRepositoryError(
            f"cannot read test repository {path}: {err}"
        ) from err
    return parse_table(text)


class FileRepository:
    """Репозиторий, данные которого загружены из файла."""

    def __init__(self, path: Path):
        """Загружает файл; бросает FileRepositoryError при ошибках."""
        self.table = load_table(path)
        mentioned = {dep for deps in self.table.values() for dep in deps}
        self.known = set(self.table) | mentioned

    def dependencies(self, name: str, version: str) -> list[Ref]:
        """Возвращает прямые зависимости пакета (версия не учитывается)."""
        if name not in self.known:
            raise FileRepositoryError(
                f"package {name} not found in test repository"
            )
        return [Ref(dep, version) for dep in self.table.get(name, [])]
