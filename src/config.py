"""Загрузка и проверка конфигурации инструмента визуализации графа."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

import yaml

MODE_REMOTE = "remote"
MODE_TEST = "test"
MODES = (MODE_REMOTE, MODE_TEST)
MIN_DEPTH = 1
OUTPUT_EXTENSION = ".png"
URL_SCHEMES = ("http", "https")
PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
VERSION_RE = re.compile(
    r"^\d+(\.\d+){1,3}(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$"
)


class ConfigError(Exception):
    """Ошибка конфигурации: хранит список всех найденных проблем."""

    def __init__(self, problems: list[str]):
        """Сохраняет список сообщений об ошибках."""
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Config:
    """Параметры, настраиваемые пользователем."""

    package_name: str
    repository: str
    mode: str
    version: str
    output_file: str
    max_depth: int
    filter_substring: str


def read_yaml(path: Path) -> dict[str, Any]:
    """Читает YAML-файл и возвращает его содержимое как словарь."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigError([f"config file not found: {path}"])
    except (IsADirectoryError, PermissionError, UnicodeDecodeError) as err:
        raise ConfigError([f"cannot read config file {path}: {err}"])
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as err:
        raise ConfigError([f"invalid YAML syntax: {err}"])
    if not isinstance(data, dict):
        raise ConfigError(["config must be a mapping of key: value"])
    return data


def check_package_name(value: Any) -> Optional[str]:
    """Проверяет имя пакета."""
    if not isinstance(value, str) or not PACKAGE_RE.match(value):
        return "'package_name' must be a string like Newtonsoft.Json"
    return None


def check_version(value: Any) -> Optional[str]:
    """Проверяет версию пакета (строка в формате NuGet/SemVer)."""
    if not isinstance(value, str) or not VERSION_RE.match(value):
        return "'version' must be a quoted string like \"13.0.3\""
    return None


def check_mode(value: Any) -> Optional[str]:
    """Проверяет режим работы с репозиторием."""
    if value not in MODES:
        return f"'mode' must be one of: {', '.join(MODES)}"
    return None


def check_output_file(value: Any) -> Optional[str]:
    """Проверяет имя файла с изображением графа."""
    if not isinstance(value, str):
        return "'output_file' must be a string"
    path = Path(value)
    if path.suffix.lower() != OUTPUT_EXTENSION or not path.stem:
        return f"'output_file' must look like name{OUTPUT_EXTENSION}"
    if not path.parent.is_dir():
        return f"'output_file' directory does not exist: {path.parent}"
    return None


def check_max_depth(value: Any) -> Optional[str]:
    """Проверяет максимальную глубину анализа."""
    if isinstance(value, bool) or not isinstance(value, int):
        return "'max_depth' must be an integer"
    if value < MIN_DEPTH:
        return f"'max_depth' must be >= {MIN_DEPTH}"
    return None


def check_filter(value: Any) -> Optional[str]:
    """Проверяет подстроку фильтрации (пустая строка - без фильтра)."""
    if not isinstance(value, str):
        return "'filter_substring' must be a string (use \"\" for no filter)"
    return None


def check_repository(value: Any, mode: str) -> Optional[str]:
    """Проверяет URL или путь к файлу в зависимости от режима."""
    if not isinstance(value, str) or not value.strip():
        return "'repository' must be a non-empty string"
    if mode == MODE_REMOTE:
        parsed = urlparse(value)
        if parsed.scheme not in URL_SCHEMES or not parsed.netloc:
            return "'repository' must be an http(s) URL in remote mode"
    elif not Path(value).is_file():
        return f"'repository' file not found in test mode: {value}"
    return None


CHECKERS: dict[str, Callable[[Any], Optional[str]]] = {
    "package_name": check_package_name,
    "version": check_version,
    "mode": check_mode,
    "output_file": check_output_file,
    "max_depth": check_max_depth,
    "filter_substring": check_filter,
}
REQUIRED_KEYS = ("repository",) + tuple(CHECKERS)


def find_key_problems(raw: dict[str, Any]) -> list[str]:
    """Находит отсутствующие и неизвестные ключи."""
    missing = [f"missing key: '{key}'" for key in REQUIRED_KEYS
               if key not in raw]
    unknown = [f"unknown key: '{key}'" for key in raw
               if key not in REQUIRED_KEYS]
    return missing + unknown


def find_value_problems(raw: dict[str, Any]) -> list[str]:
    """Проверяет значения всех присутствующих ключей."""
    problems = [checker(raw[key]) for key, checker in CHECKERS.items()
                if key in raw]
    if "repository" in raw and raw.get("mode") in MODES:
        problems.append(check_repository(raw["repository"], raw["mode"]))
    return [problem for problem in problems if problem]


def load_config(path: Path) -> Config:
    """Загружает конфигурацию; при ошибках бросает ConfigError."""
    raw = read_yaml(path)
    problems = find_key_problems(raw) + find_value_problems(raw)
    if problems:
        raise ConfigError(problems)
    return Config(**{key: raw[key] for key in REQUIRED_KEYS})
