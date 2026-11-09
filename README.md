# NuGet Dependency Visualizer

Инструмент визуализации графа зависимостей для менеджера пакетов NuGet
(.NET). Практическая работа №2, вариант №10, группа ИКБО-20-25.

Готовые средства (менеджеры пакетов, библиотеки) для получения
зависимостей не используются: данные собираются самостоятельно.

## Общее описание

Приложение — консольная утилита (CLI) на Python. Все пользовательские
параметры задаются в конфигурационном файле формата YAML.

Статус этапов:

- [x] Этап 1. Минимальный прототип с конфигурацией
- [x] Этап 2. Сбор данных
- [x] Этап 3. Основные операции
- [ ] Этап 4. Дополнительные операции
- [ ] Этап 5. Визуализация

## Структура репозитория

| Путь                      | Назначение                                   |
|---------------------------|----------------------------------------------|
| `src/main.py`             | Точка входа, разбор аргументов, вывод        |
| `src/config.py`           | Загрузка и проверка YAML-конфигурации        |
| `src/nuget.py`            | Получение зависимостей из репозитория NuGet  |
| `src/graph.py`            | Построение графа (BFS с рекурсией)           |
| `src/file_repo.py`        | Тестовый репозиторий из файла                |
| `src/errors.py`           | Общее исключение `RepositoryError`           |
| `tests/`                  | Модульные тесты и локальный сервер NuGet     |
| `configs/`                | Примеры корректных конфигураций              |
| `configs/errors/`         | Конфигурации с ошибками для демонстрации     |
| `repos/`                  | Файлы тестовых репозиториев                  |
| `configs/test/`           | Конфигурации для демонстрации тестового режима |
| `scripts/`                | Скрипты демонстрации и запуска тестов        |
| `run.bat`, `Makefile`     | Запуск приложения                            |

## Настройки (файл YAML)

| Ключ               | Тип    | Описание                                      |
|--------------------|--------|-----------------------------------------------|
| `package_name`     | строка | Имя анализируемого пакета                     |
| `repository`       | строка | URL репозитория или путь к файлу тестового    |
|                    |        | репозитория (зависит от `mode`)               |
| `mode`             | строка | Режим работы с репозиторием: `remote` —       |
|                    |        | реальный репозиторий по URL, `test` — файл    |
|                    |        | с описанием тестового графа                   |
| `version`          | строка | Версия пакета, например `"13.0.3"`            |
| `output_file`      | строка | Имя файла с изображением графа (`*.png`)     |
| `max_depth`        | число  | Максимальная глубина анализа, целое `>= 1`    |
| `filter_substring` | строка | Пакеты, в имени которых есть подстрока,       |
|                    |        | не учитываются; `""` — без фильтра            |

Пример (`configs/config.yaml`):

```yaml
package_name: Newtonsoft.Json
repository: https://api.nuget.org/v3/index.json
mode: remote
version: "13.0.3"
output_file: graph.png
max_depth: 3
filter_substring: Test
```

Версию нужно записывать в кавычках: без них YAML превращает `13.0`
в число.

## Обработка ошибок

Все найденные проблемы выводятся сразу (в `stderr`, с префиксом `Error:`),
код завершения — `1`. Проверяются:

- файл конфигурации не найден, не читается или не является файлом;
- синтаксическая ошибка YAML, корень документа не словарь;
- отсутствующие и неизвестные ключи;
- имя пакета (допустимы буквы, цифры, `.`, `_`, `-`);
- формат версии (NuGet/SemVer);
- режим (`remote` или `test`);
- URL (схема `http`/`https`) в режиме `remote`;
- существование файла в режиме `test`;
- расширение `.png` и существование каталога для `output_file`;
- `max_depth`: целое число не меньше 1 (логические значения отклоняются);
- `filter_substring`: строка.

## Сбор данных (этап 2)

Режим `remote`. Репозиторий — адрес сервисного индекса NuGet API v3
(для nuget.org: `https://api.nuget.org/v3/index.json`).

1. Скачать сервисный индекс (JSON) и найти ресурс
   `PackageBaseAddress/3.0.0` — адрес хранилища пакетов.
2. Привести имя пакета к нижнему регистру, а версию — к нормализованному
   виду NuGet (`1.0` -> `1.0.0`, `1.2.3.0` -> `1.2.3`, без `+metadata`).
3. Скачать `{base}{имя}/{версия}/{имя}.nuspec`.
4. Разобрать XML (независимо от пространства имён) и извлечь элементы
   `dependency` — как из групп `group targetFramework="..."`, так и
   напрямую из `dependencies`.

## Граф зависимостей (этап 3)

Граф строится обходом в ширину (BFS) с рекурсией: функция `bfs`
обрабатывает один уровень графа и рекурсивно вызывает себя для
следующего (глубина рекурсии равна числу уровней, а не числу пакетов).

Правила:

- **Глубина.** Корневой пакет — уровень 0. Зависимости раскрываются,
  пока уровень меньше `max_depth`: при `max_depth: 1` в графе только
  прямые зависимости корня, при `2` — ещё и их зависимости и т. д.
- **Фильтр.** Пакет, в имени которого есть `filter_substring`
  (с учётом регистра), не попадает в граф: ни как вершина, ни как цель
  ребра, и его зависимости не анализируются. Пустая строка — без
  фильтра. Фильтр, совпадающий с именем самого корня, — ошибка
  конфигурации.
- **Циклы.** Каждый пакет раскрывается один раз (множество посещённых).
  Ребро, замыкающее цикл, сохраняется в графе, но повторного обхода нет.
- **Фреймворки.** В `.nuspec` зависимости разбиты по целевым
  фреймворкам. В граф попадает объединение уникальных имён по всем
  группам; если пакет встречается с разными версиями, берётся первая.
- **Версии транзитивных зависимостей.** Диапазон версий заменяется его
  нижней границей (`4.3.0` и `[4.3.0, )` -> `4.3.0`; `[1.0, 2.0)` -> `1.0`).
  Это упрощение: реальный менеджер выбирает минимальную из
  существующих версий, подходящих под диапазон. Версию, которую нельзя
  определить (например `*`), или пакет, которого нет в репозитории,
  программа сообщает ошибкой.

Вывод: список смежности в порядке обхода (`пакет -> зависимости`);
`(none)` — зависимостей нет. Пакеты на границе глубины показаны только
как цели рёбер.

### Тестовый режим

В режиме `test` в `repository` указывается путь к файлу с описанием
графа; пакеты называются заглавными латинскими буквами. Формат —
по строке на пакет (`версия` в этом режиме не используется):

```
# комментарии и пустые строки допускаются
A: B C
B: D
D:
```

Пакет, упомянутый только как зависимость, считается пакетом без
зависимостей. Ошибки файла (нет `:`, неверное имя, пакет описан дважды,
корневого пакета нет в файле) сообщаются с номером строки.

## Коды завершения

| Код | Значение                                              |
|-----|-------------------------------------------------------|
| 0   | Успех                                                 |
| 1   | Ошибка конфигурации                                   |
| 2   | Ошибка репозитория (сеть, 404, неверный JSON/XML,     |
|     | ошибка файла тестового репозитория)                   |

## Описание функций

`src/config.py`:

- `read_yaml(path)` — читает файл и возвращает словарь, бросает
  `ConfigError` при ошибках чтения и разбора;
- `check_*` — проверки отдельных параметров, возвращают текст ошибки
  или `None`;
- `find_key_problems(raw)` — отсутствующие и неизвестные ключи;
- `find_value_problems(raw)` — проверка значений всех ключей;
- `load_config(path)` — загрузка и проверка, возвращает `Config`.

`src/nuget.py`:

- `fetch_bytes(url)` — скачивает URL, ошибки превращает в `NuGetError`;
- `find_package_base(index_url)` — адрес хранилища пакетов из индекса;
- `normalize_version(version)` — нормализация версии;
- `build_nuspec_url(base, name, version)` — URL файла `.nuspec`;
- `parse_dependencies(data)` — разбор `.nuspec`, список `Dependency`;
- `min_version(range)` — нижняя граница диапазона версий;
- `get_dependencies(base, name, version)` — зависимости точной версии;
- `unique_refs(deps)` — уникальные пакеты по всем фреймворкам;
- `RemoteRepository.dependencies(name, version)` — всё вместе
  (адрес хранилища запрашивается один раз).

`src/graph.py`:

- `build_graph(root, get_deps, max_depth, substring)` — строит граф;
- `bfs(level, walk, depth)` — рекурсивный обход в ширину;
- `expand(ref, walk)` — записывает рёбра пакета, возвращает новые пакеты;
- `is_excluded(name, substring)` — проверка фильтра.

`src/file_repo.py`:

- `parse_line`, `parse_table`, `load_table` — разбор файла;
- `FileRepository.dependencies(name, version)` — зависимости пакета.

`src/main.py`:

- `parse_args(argv)` — разбор аргумента `--config`;
- `open_repository(config)` — репозиторий по режиму работы;
- `print_graph(config, graph)` — вывод графа;
- `run(config)` — построение и вывод графа, код завершения;
- `main(argv)` — запуск приложения.

## Сборка и запуск

Сборка не требуется. Нужен Python 3.9+ и PyYAML:

```
pip install -r requirements.txt
```

Запуск:

```
python src/main.py --config configs/config.yaml
```

Без `--config` используется `configs/config.yaml`. Альтернативы:
`run.bat` (Windows) и `make run ARGS="--config configs/config.yaml"`.

## Тесты

```
scripts\run_tests.bat
```

или `make test`, или (из корня репозитория):

```
set PYTHONPATH=src
python -m unittest discover -s tests -v
```

Тесты не обращаются к интернету: репозиторий NuGet имитирует локальный
HTTP-сервер (`tests/fake_nuget.py`).

## Примеры использования

Реальный репозиторий (`mode: remote`, нужен интернет):

```
> python src/main.py --config configs/config.yaml
```

Тестовый репозиторий `repos/test_repo.txt` (граф с общей зависимостью D
и циклом B -> D -> F -> B). Все запуски сразу — `scripts\demo_test_repo.bat`.

```
A: B C
B: D
C: D E
D: F
E:
F: B
```

Полный граф (`configs/test/full.yaml`, глубина 10):

```
> python src/main.py --config configs/test/full.yaml
Dependency graph of A 1.0.0 (max depth 10):
  A -> B, C
  B -> D
  C -> D, E
  D -> F
  E -> (none)
  F -> B
```

Глубина 1 и 2 (`depth1.yaml`, `depth2.yaml`):

```
Dependency graph of A 1.0.0 (max depth 1):
  A -> B, C

Dependency graph of A 1.0.0 (max depth 2):
  A -> B, C
  B -> D
  C -> D, E
```

Фильтр `D` (`filter.yaml`) — пакет D и всё, что за ним, исключено:

```
Dependency graph of A 1.0.0 (max depth 10):
  A -> B, C
  B -> (none)
  C -> E
  E -> (none)
```

Другой корневой пакет (`subtree.yaml`, корень C):

```
Dependency graph of C 1.0.0 (max depth 10):
  C -> D, E
  D -> F
  E -> (none)
  F -> B
  B -> D
```

Циклы (`cycle.yaml`, `self_loop.yaml`):

```
Dependency graph of A 1.0.0 (max depth 10):
  A -> B
  B -> C
  C -> A

Dependency graph of A 1.0.0 (max depth 10):
  A -> A, B
  B -> C
  C -> (none)
```

Ошибки тестового режима:

```
> python src/main.py --config configs/test/missing_root.yaml
Error: package Z not found in test repository

> python src/main.py --config configs/test/bad_names.yaml
Error: line 2: invalid package name 'b' (capital Latin letters only)

> python src/main.py --config configs/test/bad_syntax.yaml
Error: line 1: expected 'A: B C'

> python src/main.py --config configs/test/filter_root.yaml
Error: 'filter_substring' matches 'package_name'
```

Ошибки конфигурации (все примеры лежат в `configs/errors/`, запуск всех
сразу — `scripts\demo_errors.bat`):

```
> python src/main.py --config configs/errors/bad_types.yaml
Error: 'package_name' must be a string like Newtonsoft.Json
Error: 'version' must be a quoted string like "13.0.3"
Error: 'output_file' must look like name.png
Error: 'max_depth' must be an integer
Error: 'filter_substring' must be a string (use "" for no filter)

> python src/main.py --config nonexistent.yaml
Error: config file not found: nonexistent.yaml
```
