"""Тесты построения графа зависимостей."""

import unittest

from graph import Ref, build_graph

DIAMOND = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
CYCLE = {"A": ["B"], "B": ["C"], "C": ["A"]}
CHAIN = {"A": ["B"], "B": ["C"], "C": ["D"], "D": ["E"], "E": []}


def build(table, root="A", depth=10, substring=""):
    """Строит граф по таблице смежности."""
    def get_deps(name, version):
        """Возвращает зависимости пакета из таблицы."""
        return [Ref(dep, version) for dep in table[name]]

    return build_graph(Ref(root, "1.0.0"), get_deps, depth, substring)


class BuildGraphTest(unittest.TestCase):
    """Обход в ширину, глубина, фильтр и циклы."""

    def test_single_package(self):
        """Пакет без зависимостей."""
        self.assertEqual(build({"A": []}), {"A": []})

    def test_diamond_visits_each_once(self):
        """Общая зависимость обрабатывается один раз."""
        self.assertEqual(build(DIAMOND), DIAMOND)

    def test_bfs_order(self):
        """Пакеты идут по уровням."""
        table = {"A": ["B", "C"], "B": ["D"], "C": ["E"], "D": [], "E": []}
        self.assertEqual(list(build(table)), ["A", "B", "C", "D", "E"])

    def test_depth_one(self):
        """Глубина 1 - только прямые зависимости."""
        self.assertEqual(build(CHAIN, depth=1), {"A": ["B"]})

    def test_depth_limit_in_middle(self):
        """Пакеты на границе глубины не раскрываются."""
        graph = build(CHAIN, depth=3)
        self.assertEqual(list(graph), ["A", "B", "C"])
        self.assertEqual(graph["C"], ["D"])

    def test_depth_larger_than_graph(self):
        """Большая глубина не мешает."""
        self.assertEqual(build(CHAIN, depth=100), CHAIN)

    def test_cycle(self):
        """Цикл не приводит к бесконечному обходу, ребро сохраняется."""
        self.assertEqual(build(CYCLE), CYCLE)

    def test_self_loop(self):
        """Зависимость пакета от самого себя."""
        self.assertEqual(build({"A": ["A", "B"], "B": []}),
                         {"A": ["A", "B"], "B": []})

    def test_cycle_with_depth(self):
        """Цикл и ограничение глубины вместе."""
        self.assertEqual(build(CYCLE, depth=2), {"A": ["B"], "B": ["C"]})

    def test_filter_removes_node_and_subtree(self):
        """Исключённый пакет и его зависимости не попадают в граф."""
        self.assertEqual(build(DIAMOND, substring="B"),
                         {"A": ["C"], "C": ["D"], "D": []})

    def test_filter_is_substring(self):
        """Фильтр работает по вхождению подстроки."""
        table = {"A": ["Test.X", "Lib"], "Lib": [], "Test.X": []}
        self.assertEqual(build(table, substring="Test"),
                         {"A": ["Lib"], "Lib": []})

    def test_filter_is_case_sensitive(self):
        """Регистр учитывается."""
        self.assertEqual(build(DIAMOND, substring="b"), DIAMOND)

    def test_empty_filter(self):
        """Пустая подстрока ничего не исключает."""
        self.assertEqual(build(DIAMOND, substring=""), DIAMOND)

    def test_versions_are_passed(self):
        """Версия корня передаётся в функцию получения зависимостей."""
        calls = []

        def get_deps(name, version):
            """Запоминает запрос."""
            calls.append((name, version))
            return []

        build_graph(Ref("A", "2.0.0"), get_deps, 3, "")
        self.assertEqual(calls, [("A", "2.0.0")])


if __name__ == "__main__":
    unittest.main()
