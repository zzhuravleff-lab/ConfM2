"""Тесты командной строки."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from fake_nuget import FakeNuGet
from main import (EXIT_CONFIG_ERROR, EXIT_OK, EXIT_REPOSITORY_ERROR,
                  EXIT_UNSUPPORTED, main)
from test_nuget import GROUPED, NUSPEC_PATH

ROOT = Path(__file__).resolve().parents[1]
TEST_REPO = (ROOT / "repos" / "test_repo.txt").as_posix()
CONFIG = """package_name: Demo
repository: {repository}
mode: {mode}
version: "1.0.0"
output_file: graph.png
max_depth: 3
filter_substring: ""
"""


class CliTest(unittest.TestCase):
    """Запуск main с временным конфигом."""

    def setUp(self):
        """Создаёт временный каталог."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_main(self, repository: str, mode: str = "remote"):
        """Запускает main и возвращает код, stdout и stderr."""
        path = Path(self.tmp.name) / "config.yaml"
        path.write_text(CONFIG.format(repository=repository, mode=mode))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--config", str(path)])
        return code, out.getvalue(), err.getvalue()

    def test_prints_dependencies(self):
        """Зависимости выводятся на экран."""
        with FakeNuGet({NUSPEC_PATH: GROUPED}) as server:
            code, out, _ = self.run_main(server.index_url)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Direct dependencies of Demo 1.0.0:", out)
        self.assertIn("Lib.A [1.0.0, ) [.NETStandard2.0]", out)

    def test_no_dependencies_message(self):
        """Для пакета без зависимостей выводится (none)."""
        empty = b"<package><metadata/></package>"
        with FakeNuGet({NUSPEC_PATH: empty}) as server:
            code, out, _ = self.run_main(server.index_url)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("(none)", out)

    def test_package_not_found(self):
        """Неизвестный пакет: код 2 и сообщение в stderr."""
        with FakeNuGet({}) as server:
            code, _, err = self.run_main(server.index_url)
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertIn("not found", err)

    def test_test_mode_unsupported(self):
        """Тестовый режим пока не поддерживается."""
        code, _, err = self.run_main(TEST_REPO, mode="test")
        self.assertEqual(code, EXIT_UNSUPPORTED)
        self.assertIn("Error:", err)

    def test_config_error(self):
        """Ошибка конфигурации: код 1."""
        code, _, err = self.run_main("ftp://x")
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("Error:", err)


if __name__ == "__main__":
    unittest.main()
