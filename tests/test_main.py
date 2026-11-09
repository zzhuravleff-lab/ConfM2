"""Тесты командной строки."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from fake_nuget import FLAT_PATH, FakeNuGet
from main import EXIT_CONFIG_ERROR, EXIT_OK, EXIT_REPOSITORY_ERROR, main
from test_nuget import GROUPED, NUSPEC_PATH

ROOT = Path(__file__).resolve().parents[1]
REPOS = ROOT / "repos"
CONFIG = """package_name: {package}
repository: {repository}
mode: {mode}
version: "1.0.0"
output_file: graph.png
max_depth: {depth}
filter_substring: "{substring}"
"""
LEAF = b"<package><metadata><dependencies/></metadata></package>"
LIB_A = (b'<package><metadata><dependencies><dependency id="Lib.B" '
         b'version="2.1.0"/></dependencies></metadata></package>')
REMOTE_FILES = {
    NUSPEC_PATH: GROUPED,
    f"{FLAT_PATH}lib.a/1.0.0/lib.a.nuspec": LIB_A,
    f"{FLAT_PATH}lib.b/2.1.0/lib.b.nuspec": LEAF,
}


class CliTestCase(unittest.TestCase):
    """Запуск main с временным конфигом."""

    def setUp(self):
        """Создаёт временный каталог."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_main(self, repository: str, package: str = "Demo",
                 mode: str = "remote", depth: int = 5, substring: str = ""):
        """Запускает main и возвращает код, stdout и stderr."""
        path = Path(self.tmp.name) / "config.yaml"
        path.write_text(CONFIG.format(
            package=package, repository=repository, mode=mode,
            depth=depth, substring=substring), encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--config", str(path)])
        return code, out.getvalue(), err.getvalue()

    def run_test_mode(self, repo_file: str, **kwargs):
        """Запускает main в тестовом режиме."""
        repository = (REPOS / repo_file).as_posix()
        return self.run_main(repository, package="A", mode="test", **kwargs)


class RemoteModeTest(CliTestCase):
    """Режим remote (локальный сервер вместо nuget.org)."""

    def test_prints_transitive_graph(self):
        """Выводится граф с транзитивными зависимостями."""
        with FakeNuGet(REMOTE_FILES) as server:
            code, out, _ = self.run_main(server.index_url)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Dependency graph of Demo 1.0.0 (max depth 5):", out)
        self.assertIn("  Demo -> Lib.A, Lib.B", out)
        self.assertIn("  Lib.A -> Lib.B", out)
        self.assertIn("  Lib.B -> (none)", out)

    def test_depth_limit(self):
        """При глубине 1 раскрывается только корень."""
        with FakeNuGet(REMOTE_FILES) as server:
            _, out, _ = self.run_main(server.index_url, depth=1)
        self.assertNotIn("Lib.A ->", out)

    def test_filter(self):
        """Пакеты с подстрокой в имени исключаются."""
        with FakeNuGet(REMOTE_FILES) as server:
            _, out, _ = self.run_main(server.index_url, substring="Lib.A")
        self.assertIn("  Demo -> Lib.B", out)
        self.assertNotIn("Lib.A", out)

    def test_package_not_found(self):
        """Неизвестный пакет: код 2 и сообщение в stderr."""
        with FakeNuGet({}) as server:
            code, _, err = self.run_main(server.index_url)
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertIn("not found", err)

    def test_transitive_package_not_found(self):
        """Недоступная транзитивная зависимость - ошибка репозитория."""
        files = {NUSPEC_PATH: GROUPED}
        with FakeNuGet(files) as server:
            code, _, err = self.run_main(server.index_url)
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertIn("Lib.A", err)


class TestModeTest(CliTestCase):
    """Режим test с файлами из каталога repos."""

    def test_full_graph_with_cycle(self):
        """Полный граф, цикл B -> D -> F -> B."""
        code, out, _ = self.run_test_mode("test_repo.txt")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.splitlines()[1:], [
            "  A -> B, C", "  B -> D", "  C -> D, E",
            "  D -> F", "  E -> (none)", "  F -> B"])

    def test_depth(self):
        """Ограничение глубины."""
        _, out, _ = self.run_test_mode("test_repo.txt", depth=1)
        self.assertEqual(out.splitlines()[1:], ["  A -> B, C"])

    def test_filter(self):
        """Фильтрация пакетов."""
        _, out, _ = self.run_test_mode("test_repo.txt", substring="D")
        self.assertEqual(out.splitlines()[1:], [
            "  A -> B, C", "  B -> (none)", "  C -> E", "  E -> (none)"])

    def test_simple_cycle(self):
        """Цикл A -> B -> C -> A."""
        _, out, _ = self.run_test_mode("cycle.txt")
        self.assertEqual(out.splitlines()[1:],
                         ["  A -> B", "  B -> C", "  C -> A"])

    def test_missing_root(self):
        """Корневого пакета нет в файле."""
        code, _, err = self.run_main(
            (REPOS / "test_repo.txt").as_posix(), package="Z", mode="test")
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertIn("package Z not found", err)

    def test_invalid_repo_file(self):
        """Некорректный файл репозитория."""
        code, _, err = self.run_test_mode("bad_names.txt")
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertIn("line 2", err)


class ConfigErrorTest(CliTestCase):
    """Ошибки конфигурации."""

    def test_config_error(self):
        """Ошибка конфигурации: код 1."""
        code, _, err = self.run_main("ftp://x")
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("Error:", err)


if __name__ == "__main__":
    unittest.main()
