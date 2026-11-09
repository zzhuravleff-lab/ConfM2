"""Точка входа: визуализатор графа зависимостей NuGet-пакетов."""

import argparse
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Sequence

from config import Config, ConfigError, load_config

DEFAULT_CONFIG = "configs/config.yaml"
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1


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


def print_params(config: Config) -> None:
    """Выводит все параметры в формате ключ-значение."""
    for key, value in asdict(config).items():
        shown = repr(value) if value == "" else value
        print(f"{key}: {shown}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Запускает приложение и возвращает код завершения."""
    args = parse_args(argv)
    try:
        config = load_config(Path(args.config))
    except ConfigError as err:
        for problem in err.problems:
            print(f"Error: {problem}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    print_params(config)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
