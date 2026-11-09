"""Точка входа: визуализатор графа зависимостей NuGet-пакетов."""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from config import MODE_REMOTE, Config, ConfigError, load_config
from nuget import Dependency, NuGetError, get_direct_dependencies

DEFAULT_CONFIG = "configs/config.yaml"
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_REPOSITORY_ERROR = 2
EXIT_UNSUPPORTED = 3


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


def format_dependency(dep: Dependency) -> str:
    """Форматирует зависимость для вывода на экран."""
    return f"  {dep.name} {dep.version_range} [{dep.framework}]"


def print_dependencies(config: Config, deps: list[Dependency]) -> None:
    """Выводит все прямые зависимости пакета."""
    print(f"Direct dependencies of {config.package_name} {config.version}:")
    if not deps:
        print("  (none)")
    for dep in deps:
        print(format_dependency(dep))


def run(config: Config) -> int:
    """Получает и выводит прямые зависимости, возвращает код завершения."""
    if config.mode != MODE_REMOTE:
        print("Error: test mode is not supported yet", file=sys.stderr)
        return EXIT_UNSUPPORTED
    try:
        deps = get_direct_dependencies(
            config.repository, config.package_name, config.version
        )
    except NuGetError as err:
        print(f"Error: {err}", file=sys.stderr)
        return EXIT_REPOSITORY_ERROR
    print_dependencies(config, deps)
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
