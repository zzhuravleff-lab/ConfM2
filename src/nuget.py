"""Получение прямых зависимостей пакета из репозитория NuGet (API v3).

Используется только стандартная библиотека: сервисный индекс читается
как JSON, а зависимости берутся из файла .nuspec нужной версии пакета.
"""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from http import HTTPStatus
from typing import Optional
from xml.etree.ElementTree import Element, ParseError, fromstring

from errors import RepositoryError
from graph import Ref

REQUEST_TIMEOUT = 15
USER_AGENT = "ConfM2-dependency-visualizer/1.0"
PACKAGE_BASE_TYPE = "PackageBaseAddress/3.0.0"
ANY_FRAMEWORK = "any"
ANY_VERSION = "*"
SEMVER_PARTS = 3
REVISION_PARTS = 4


class NuGetError(RepositoryError):
    """Ошибка получения данных из репозитория NuGet."""

    def __init__(self, message: str, status: Optional[int] = None):
        """Сохраняет сообщение и HTTP-статус (если он известен)."""
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Dependency:
    """Прямая зависимость пакета."""

    name: str
    version_range: str
    framework: str


def fetch_bytes(url: str) -> bytes:
    """Скачивает содержимое URL, ошибки превращает в NuGetError."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
            return resp.read()
    except urllib.error.HTTPError as err:
        raise NuGetError(f"HTTP {err.code} for {url}", err.code) from err
    except (OSError, ValueError) as err:
        raise NuGetError(f"cannot download {url}: {err}") from err


def find_package_base(index_url: str) -> str:
    """Находит в сервисном индексе адрес хранилища пакетов (flat container)."""
    try:
        resources = json.loads(fetch_bytes(index_url))["resources"]
        for resource in resources:
            if resource.get("@type") == PACKAGE_BASE_TYPE:
                return resource["@id"].rstrip("/") + "/"
    except (ValueError, KeyError, TypeError, AttributeError) as err:
        raise NuGetError(f"invalid service index at {index_url}") from err
    raise NuGetError(f"{PACKAGE_BASE_TYPE} not found in {index_url}")


def normalize_version(version: str) -> str:
    """Приводит версию к виду, который использует NuGet в URL."""
    core = version.split("+", 1)[0].lower()
    numbers, dash, suffix = core.partition("-")
    parts = [str(int(part)) for part in numbers.split(".")]
    while len(parts) < SEMVER_PARTS:
        parts.append("0")
    if len(parts) == REVISION_PARTS and parts[-1] == "0":
        parts.pop()
    return ".".join(parts) + dash + suffix


def build_nuspec_url(base: str, name: str, version: str) -> str:
    """Строит URL файла .nuspec для указанной версии пакета."""
    lower = name.lower()
    return f"{base}{lower}/{normalize_version(version)}/{lower}.nuspec"


def local_name(tag: str) -> str:
    """Возвращает имя XML-тега без пространства имён."""
    return tag.rsplit("}", 1)[-1]


def children(element: Element, name: str) -> list[Element]:
    """Возвращает дочерние элементы с заданным именем."""
    return [child for child in element if local_name(child.tag) == name]


def read_dependencies(parent: Element, framework: str) -> list[Dependency]:
    """Читает элементы dependency внутри parent."""
    return [
        Dependency(node.get("id"), node.get("version") or ANY_VERSION,
                   framework)
        for node in children(parent, "dependency")
        if node.get("id")
    ]


def parse_dependencies(data: bytes) -> list[Dependency]:
    """Извлекает прямые зависимости из содержимого .nuspec."""
    try:
        root = fromstring(data)
    except ParseError as err:
        raise NuGetError(f"invalid nuspec XML: {err}") from err
    nodes = [node for node in root.iter()
             if local_name(node.tag) == "dependencies"]
    result: list[Dependency] = []
    for node in nodes[:1]:
        result += read_dependencies(node, ANY_FRAMEWORK)
        for group in children(node, "group"):
            framework = group.get("targetFramework") or ANY_FRAMEWORK
            result += read_dependencies(group, framework)
    return result


def min_version(version_range: str) -> str:
    """Выбирает минимальную версию из диапазона NuGet.

    ``4.3.0`` и ``[4.3.0, )`` дают ``4.3.0``; ``[1.0, 2.0)`` дают ``1.0``.
    """
    text = version_range.strip()
    if text[:1] in ("[", "("):
        low, _, high = text[1:-1].partition(",")
        text = low.strip() or high.strip()
    return text


def get_dependencies(base: str, name: str, version: str) -> list[Dependency]:
    """Возвращает прямые зависимости пакета заданной точной версии."""
    try:
        url = build_nuspec_url(base, name, version)
    except ValueError as err:
        raise NuGetError(f"cannot use version '{version}' of {name}") from err
    try:
        data = fetch_bytes(url)
    except NuGetError as err:
        if err.status == HTTPStatus.NOT_FOUND:
            raise NuGetError(f"package {name} {version} not found") from err
        raise
    return parse_dependencies(data)


def unique_refs(deps: list[Dependency]) -> list[Ref]:
    """Собирает уникальные пакеты по всем группам фреймворков.

    Для повторяющихся имён берётся первая встреченная версия.
    """
    refs: dict[str, Ref] = {}
    for dep in deps:
        refs.setdefault(dep.name, Ref(dep.name, min_version(dep.version_range)))
    return list(refs.values())


class RemoteRepository:
    """Реальный репозиторий NuGet, адрес которого - сервисный индекс."""

    def __init__(self, index_url: str):
        """Запоминает адрес индекса (хранилище ищется при первом запросе)."""
        self.index_url = index_url
        self.base: Optional[str] = None

    def dependencies(self, name: str, version: str) -> list[Ref]:
        """Возвращает прямые зависимости пакета (версия - точная)."""
        if self.base is None:
            self.base = find_package_base(self.index_url)
        return unique_refs(get_dependencies(self.base, name, version))
