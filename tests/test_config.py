"""Тесты загрузки и проверки конфигурации."""

import tempfile
import unittest
from pathlib import Path

from config import ConfigError, load_config

ROOT = Path(__file__).resolve().parents[1]
TEST_REPO = ROOT / "repos" / "test_repo.txt"
VALID = {
    "package_name": "Newtonsoft.Json",
    "repository": "https://api.nuget.org/v3/index.json",
    "mode": "remote",
    "version": '"13.0.3"',
    "output_file": "graph.png",
    "max_depth": "3",
    "filter_substring": '""',
}


def render(**changes) -> str:
    """Собирает текст YAML на основе VALID с заменой/удалением ключей."""
    data = {**VALID, **changes}
    return "\n".join(f"{k}: {v}" for k, v in data.items() if v is not None)


class ConfigTestCase(unittest.TestCase):
    """Базовый класс: создаёт временный каталог с конфигом."""

    def setUp(self):
        """Создаёт временный каталог."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, text: str) -> Path:
        """Записывает текст в файл конфигурации и возвращает путь."""
        path = Path(self.tmp.name) / "config.yaml"
        path.write_text(text, encoding="utf-8")
        return path

    def problems(self, text: str) -> list[str]:
        """Возвращает список ошибок, найденных в конфигурации."""
        with self.assertRaises(ConfigError) as ctx:
            load_config(self.write(text))
        return ctx.exception.problems


class ValidConfigTest(ConfigTestCase):
    """Корректные конфигурации."""

    def test_remote_mode(self):
        """Режим remote с URL загружается без ошибок."""
        config = load_config(self.write(render()))
        self.assertEqual(config.package_name, "Newtonsoft.Json")
        self.assertEqual(config.max_depth, 3)
        self.assertEqual(config.filter_substring, "")

    def test_test_mode(self):
        """Режим test с существующим файлом загружается без ошибок."""
        text = render(mode="test", repository=TEST_REPO.as_posix())
        self.assertEqual(load_config(self.write(text)).mode, "test")


class FileErrorTest(ConfigTestCase):
    """Ошибки чтения файла."""

    def test_missing_file(self):
        """Несуществующий файл конфигурации."""
        with self.assertRaises(ConfigError):
            load_config(Path(self.tmp.name) / "nope.yaml")

    def test_directory_instead_of_file(self):
        """Вместо файла указан каталог."""
        with self.assertRaises(ConfigError):
            load_config(Path(self.tmp.name))

    def test_broken_yaml(self):
        """Синтаксическая ошибка YAML."""
        self.assertTrue(self.problems("package_name: [A\nmode: x"))

    def test_not_a_mapping(self):
        """Корень документа не словарь."""
        self.assertTrue(self.problems("- a\n- b"))

    def test_empty_file(self):
        """Пустой файл."""
        self.assertTrue(self.problems(""))


class KeyErrorTest(ConfigTestCase):
    """Ошибки набора ключей."""

    def test_missing_key(self):
        """Отсутствует обязательный ключ."""
        problems = self.problems(render(max_depth=None))
        self.assertIn("missing key: 'max_depth'", problems)

    def test_unknown_key(self):
        """Лишний ключ."""
        problems = self.problems(render() + "\ncolor: red")
        self.assertIn("unknown key: 'color'", problems)


class ValueErrorTest(ConfigTestCase):
    """Ошибки значений параметров."""

    def assert_one_problem(self, key: str, value: str):
        """Проверяет, что неверное значение даёт ровно одну ошибку."""
        problems = self.problems(render(**{key: value}))
        self.assertEqual(len(problems), 1)
        self.assertIn(key, problems[0])

    def test_bad_package_name(self):
        """Недопустимое имя пакета."""
        self.assert_one_problem("package_name", '"bad name!"')

    def test_version_as_float(self):
        """Версия без кавычек превращается в число."""
        self.assert_one_problem("version", "13.0")

    def test_bad_mode(self):
        """Неизвестный режим."""
        self.assert_one_problem("mode", "offline")

    def test_bad_extension(self):
        """Файл изображения не PNG."""
        self.assert_one_problem("output_file", "graph.jpg")

    def test_missing_output_dir(self):
        """Каталог для изображения не существует."""
        self.assert_one_problem("output_file", "no_dir/graph.png")

    def test_depth_zero(self):
        """Нулевая глубина."""
        self.assert_one_problem("max_depth", "0")

    def test_depth_bool(self):
        """Логическое значение вместо числа."""
        self.assert_one_problem("max_depth", "true")

    def test_filter_not_string(self):
        """Подстрока фильтра не строка."""
        self.assert_one_problem("filter_substring", "5")

    def test_filter_matches_package(self):
        """Фильтр исключает сам анализируемый пакет."""
        problems = self.problems(render(filter_substring="Json"))
        self.assertEqual(len(problems), 1)
        self.assertIn("filter_substring", problems[0])

    def test_bad_url(self):
        """Неверная схема URL в режиме remote."""
        self.assert_one_problem("repository", "ftp://example.com")

    def test_missing_test_file(self):
        """Файл тестового репозитория не найден."""
        problems = self.problems(render(mode="test", repository="nope.txt"))
        self.assertEqual(len(problems), 1)

    def test_all_problems_reported(self):
        """Все ошибки возвращаются сразу."""
        problems = self.problems(render(mode="x", max_depth="0"))
        self.assertEqual(len(problems), 2)


if __name__ == "__main__":
    unittest.main()
