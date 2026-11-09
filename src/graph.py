"""Построение графа зависимостей обходом в ширину (BFS с рекурсией)."""

from dataclasses import dataclass, field
from typing import Callable, NamedTuple


class Ref(NamedTuple):
    """Ссылка на пакет: имя и версия."""

    name: str
    version: str


GetDeps = Callable[[str, str], list[Ref]]


@dataclass
class Walk:
    """Состояние обхода: параметры анализа и накопленный результат."""

    get_deps: GetDeps
    max_depth: int
    substring: str
    graph: dict[str, list[str]] = field(default_factory=dict)
    seen: set[str] = field(default_factory=set)


def is_excluded(name: str, substring: str) -> bool:
    """Проверяет, нужно ли пропустить пакет (пустая подстрока - не нужно)."""
    return bool(substring) and substring in name


def expand(ref: Ref, walk: Walk) -> list[Ref]:
    """Записывает рёбра пакета и возвращает новые пакеты для обхода."""
    walk.graph[ref.name] = []
    fresh = []
    for dep in walk.get_deps(ref.name, ref.version):
        if is_excluded(dep.name, walk.substring):
            continue
        walk.graph[ref.name].append(dep.name)
        if dep.name not in walk.seen:
            walk.seen.add(dep.name)
            fresh.append(dep)
    return fresh


def bfs(level: list[Ref], walk: Walk, depth: int) -> None:
    """Обрабатывает уровень графа и рекурсивно переходит к следующему."""
    if not level or depth >= walk.max_depth:
        return
    next_level = [fresh for ref in level for fresh in expand(ref, walk)]
    bfs(next_level, walk, depth + 1)


def build_graph(
    root: Ref, get_deps: GetDeps, max_depth: int, substring: str
) -> dict[str, list[str]]:
    """Строит граф зависимостей: пакет -> список его прямых зависимостей.

    В графе только пакеты, зависимости которых были проанализированы;
    пакеты на границе глубины встречаются лишь как цели рёбер.
    """
    walk = Walk(get_deps, max_depth, substring, seen={root.name})
    bfs([root], walk, 0)
    return walk.graph
