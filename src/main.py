"""Точка входа: визуализатор графа зависимостей NuGet-пакетов."""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence, Union

from config import MODE_REMOTE, Config, ConfigError, load_config
from errors import RepositoryError
from file_repo import FileRepository
from graph import Ref, build_graph
from nuget import RemoteRepository

Repository = Union[RemoteRepository, FileRepository]

DEFAULT_CONFIG = "configs/config.yaml"
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_REPOSITORY_ERROR = 2


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Разбирает аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Dependency graph visualizer for NuGet packages."
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help="path to the YAML config file (default: %(default)s)",
    )
    return parser.parse_args(argv)


def open_repository(config: Config) -> Repository:
    """Создаёт репозиторий в соответствии с режимом работы."""
    if config.mode == MODE_REMOTE:
        return RemoteRepository(config.repository)
    return FileRepository(Path(config.repository))


def format_edges(name: str, targets: list[str]) -> str:
    """Форматирует одну строку графа: пакет -> его зависимости."""
    return f"  {name} -> {', '.join(targets) or '(none)'}"


def print_graph(config: Config, graph: dict[str, list[str]]) -> None:
    """Выводит граф зависимостей в виде списка смежности."""
    print(
        f"Dependency graph of {config.package_name} {config.version} "
        f"(max depth {config.max_depth}):"
    )
    for name, targets in graph.items():
        print(format_edges(name, targets))


def run(config: Config) -> int:
    """Строит и выводит граф зависимостей, возвращает код завершения."""
    try:
        repository = open_repository(config)
        graph = build_graph(
            Ref(config.package_name, config.version),
            repository.dependencies,
            config.max_depth,
            config.filter_substring,
        )
    except RepositoryError as err:
        print(f"Error: {err}", file=sys.stderr)
        return EXIT_REPOSITORY_ERROR
    print_graph(config, graph)
    return EXIT_OK


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Запускает приложение и возвращает код завершения."""
    args = parse_args(argv)
    try:
        config = load_config(Path(args.config))
    except ConfigError as err:
        for problem in err.problems:
            print(f"Error: {problem}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    return run(config)


if __name__ == "__main__":
    sys.exit(main())
