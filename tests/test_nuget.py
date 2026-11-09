"""Тесты получения и разбора зависимостей NuGet."""

import unittest
from unittest import mock

import nuget
from fake_nuget import FLAT_PATH, FakeNuGet
from nuget import Dependency, NuGetError

NS = "http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd"
GROUPED = f"""\ufeff<?xml version="1.0" encoding="utf-8"?>
<package xmlns="{NS}"><metadata><id>Demo</id><version>1.0.0</version>
<dependencies>
  <group targetFramework=".NETStandard2.0">
    <dependency id="Lib.A" version="[1.0.0, )" />
    <dependency id="Lib.B" version="2.1.0" />
  </group>
  <group targetFramework="net6.0" />
</dependencies></metadata></package>""".encode("utf-8")
FLAT = b"""<package><metadata><dependencies>
<dependency id="Old.Lib" version="1.2" /><dependency id="NoVersion" />
</dependencies></metadata></package>"""
EMPTY = b"<package><metadata><id>Demo</id></metadata></package>"
NUSPEC_PATH = f"{FLAT_PATH}demo/1.0.0/demo.nuspec"


class NormalizeVersionTest(unittest.TestCase):
    """Нормализация версий как в NuGet."""

    def test_pads_to_three_parts(self):
        """Недостающие части дополняются нулями."""
        self.assertEqual(nuget.normalize_version("1.0"), "1.0.0")

    def test_drops_zero_revision(self):
        """Нулевая четвёртая часть отбрасывается."""
        self.assertEqual(nuget.normalize_version("1.2.3.0"), "1.2.3")

    def test_keeps_revision(self):
        """Ненулевая четвёртая часть сохраняется."""
        self.assertEqual(nuget.normalize_version("1.2.3.4"), "1.2.3.4")

    def test_prerelease_and_metadata(self):
        """Метаданные сборки удаляются, суффикс в нижнем регистре."""
        self.assertEqual(nuget.normalize_version("1.0-Beta+x"), "1.0.0-beta")


class ParseDependenciesTest(unittest.TestCase):
    """Разбор .nuspec."""

    def test_groups_with_namespace_and_bom(self):
        """Зависимости из групп, пустая группа даёт пустой результат."""
        deps = nuget.parse_dependencies(GROUPED)
        self.assertEqual(deps, [
            Dependency("Lib.A", "[1.0.0, )", ".NETStandard2.0"),
            Dependency("Lib.B", "2.1.0", ".NETStandard2.0"),
        ])

    def test_flat_dependencies(self):
        """Зависимости без групп; версия по умолчанию - любая."""
        deps = nuget.parse_dependencies(FLAT)
        self.assertEqual(deps, [
            Dependency("Old.Lib", "1.2", nuget.ANY_FRAMEWORK),
            Dependency("NoVersion", nuget.ANY_VERSION, nuget.ANY_FRAMEWORK),
        ])

    def test_no_dependencies(self):
        """Пакет без зависимостей."""
        self.assertEqual(nuget.parse_dependencies(EMPTY), [])

    def test_invalid_xml(self):
        """Некорректный XML."""
        with self.assertRaises(NuGetError):
            nuget.parse_dependencies(b"<package>")


class FindPackageBaseTest(unittest.TestCase):
    """Разбор сервисного индекса."""

    def find(self, raw: bytes) -> str:
        """Вызывает find_package_base с подменённой загрузкой."""
        with mock.patch.object(nuget, "fetch_bytes", return_value=raw):
            return nuget.find_package_base("http://x/index.json")

    def test_found(self):
        """Адрес найден, в конце добавляется слэш."""
        raw = (b'{"resources":[{"@id":"http://x/f",'
               b'"@type":"PackageBaseAddress/3.0.0"}]}')
        self.assertEqual(self.find(raw), "http://x/f/")

    def test_missing_resource(self):
        """В индексе нет нужного ресурса."""
        with self.assertRaises(NuGetError):
            self.find(b'{"resources":[]}')

    def test_not_json(self):
        """Индекс не является JSON."""
        with self.assertRaises(NuGetError):
            self.find(b"<html>")

    def test_wrong_structure(self):
        """Неверная структура JSON."""
        with self.assertRaises(NuGetError):
            self.find(b'{"resources":[1]}')


class LocalServerTest(unittest.TestCase):
    """Полный сценарий через локальный HTTP-сервер."""

    def test_direct_dependencies(self):
        """Версия 1.0 находит пакет 1.0.0 без учёта регистра имени."""
        with FakeNuGet({NUSPEC_PATH: GROUPED}) as server:
            deps = nuget.get_direct_dependencies(
                server.index_url, "Demo", "1.0"
            )
        self.assertEqual([dep.name for dep in deps], ["Lib.A", "Lib.B"])

    def test_package_not_found(self):
        """Отсутствующий пакет даёт понятную ошибку."""
        with FakeNuGet({}) as server:
            with self.assertRaises(NuGetError) as ctx:
                nuget.get_direct_dependencies(server.index_url, "X", "1.0")
        self.assertIn("not found", str(ctx.exception))

    def test_server_unavailable(self):
        """Недоступный сервер."""
        with self.assertRaises(NuGetError):
            nuget.get_direct_dependencies("http://127.0.0.1:1/i", "X", "1.0")

    def test_malformed_url(self):
        """Некорректный URL."""
        with self.assertRaises(NuGetError):
            nuget.get_direct_dependencies("not a url", "X", "1.0")


if __name__ == "__main__":
    unittest.main()
