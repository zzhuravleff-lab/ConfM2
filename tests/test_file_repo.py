"""Тесты тестового репозитория (файл с описанием графа)."""

import tempfile
import unittest
from pathlib import Path

from file_repo import FileRepository, FileRepositoryError, parse_table
from graph import Ref


class ParseTableTest(unittest.TestCase):
    """Разбор текста файла."""

    def test_valid(self):
        """Корректный файл с пустыми строками и комментариями."""
        text = "# graph\nA: B C\n\nB:\n  C :  \n"
        self.assertEqual(parse_table(text),
                         {"A": ["B", "C"], "B": [], "C": []})

    def test_duplicates_in_line_removed(self):
        """Повторы в списке зависимостей удаляются."""
        self.assertEqual(parse_table("A: B B"), {"A": ["B"]})

    def test_no_colon(self):
        """Строка без двоеточия."""
        with self.assertRaises(FileRepositoryError) as ctx:
            parse_table("A B")
        self.assertIn("line 1", str(ctx.exception))

    def test_lowercase_name(self):
        """Имя не из заглавных латинских букв."""
        with self.assertRaises(FileRepositoryError):
            parse_table("A: b")

    def test_digit_in_name(self):
        """Цифры в имени недопустимы."""
        with self.assertRaises(FileRepositoryError):
            parse_table("A1: B")

    def test_defined_twice(self):
        """Пакет описан дважды."""
        with self.assertRaises(FileRepositoryError):
            parse_table("A: B\nA: C")


class FileRepositoryTest(unittest.TestCase):
    """Работа с файлом репозитория."""

    def setUp(self):
        """Создаёт временный каталог."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def repo(self, text: str) -> FileRepository:
        """Создаёт репозиторий из текста."""
        path = Path(self.tmp.name) / "repo.txt"
        path.write_text(text, encoding="utf-8")
        return FileRepository(path)

    def test_dependencies(self):
        """Зависимости пакета возвращаются как Ref."""
        repo = self.repo("A: B C\nB:\n")
        self.assertEqual(repo.dependencies("A", "1.0.0"),
                         [Ref("B", "1.0.0"), Ref("C", "1.0.0")])

    def test_mentioned_package_is_leaf(self):
        """Пакет, упомянутый только как зависимость, не имеет зависимостей."""
        self.assertEqual(self.repo("A: B").dependencies("B", "1"), [])

    def test_unknown_package(self):
        """Неизвестный пакет."""
        with self.assertRaises(FileRepositoryError):
            self.repo("A: B").dependencies("Z", "1")

    def test_missing_file(self):
        """Файл не существует."""
        with self.assertRaises(FileRepositoryError):
            FileRepository(Path(self.tmp.name) / "none.txt")

    def test_not_utf8(self):
        """Файл не в кодировке UTF-8."""
        path = Path(self.tmp.name) / "bin.txt"
        path.write_bytes(b"\xff\xfe\x00")
        with self.assertRaises(FileRepositoryError):
            FileRepository(path)


if __name__ == "__main__":
    unittest.main()
