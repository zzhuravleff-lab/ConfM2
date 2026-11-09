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
- [ ] Этап 3. Основные операции
- [ ] Этап 4. Дополнительные операции
- [ ] Этап 5. Визуализация

## Структура репозитория

| Путь                      | Назначение                                   |
|---------------------------|----------------------------------------------|
| `src/main.py`             | Точка входа, разбор аргументов, вывод        |
| `src/config.py`           | Загрузка и проверка YAML-конфигурации        |
| `src/nuget.py`            | Получение зависимостей из репозитория NuGet  |
| `tests/`                  | Модульные тесты и локальный сервер NuGet     |
| `configs/`                | Примеры корректных конфигураций              |
| `configs/errors/`         | Конфигурации с ошибками для демонстрации     |
| `repos/test_repo.txt`     | Заготовка тестового репозитория (этап 3)     |
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

Работает в режиме `remote`. Репозиторий — адрес сервисного индекса NuGet
API v3 (для nuget.org: `https://api.nuget.org/v3/index.json`).

Алгоритм (только стандартная библиотека, без менеджеров пакетов):

1. Скачать сервисный индекс (JSON) и найти ресурс
   `PackageBaseAddress/3.0.0` — адрес хранилища пакетов.
2. Привести имя пакета к нижнему регистру, а версию — к нормализованному
   виду NuGet (`1.0` -> `1.0.0`, `1.2.3.0` -> `1.2.3`, без `+metadata`).
3. Скачать `{base}{имя}/{версия}/{имя}.nuspec`.
4. Разобрать XML (независимо от пространства имён) и извлечь элементы
   `dependency` — как из групп `group targetFramework="..."`, так и
   напрямую из `dependencies`.

Выводятся все прямые зависимости: имя, диапазон версий (как записан
в .nuspec; `*` — версия не указана) и целевой фреймворк (`any` — группы
нет). Если зависимостей нет, выводится `(none)`.

Режим `test` пока не поддерживается (появится на этапе 3): программа
сообщает об этом и завершается с кодом 3.

## Коды завершения

| Код | Значение                                              |
|-----|-------------------------------------------------------|
| 0   | Успех                                                 |
| 1   | Ошибка конфигурации                                   |
| 2   | Ошибка репозитория (сеть, 404, неверный JSON/XML)     |
| 3   | Режим не поддерживается на текущем этапе              |

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
- `get_direct_dependencies(index_url, name, version)` — всё вместе.

`src/main.py`:

- `parse_args(argv)` — разбор аргумента `--config`;
- `print_dependencies(config, deps)` — вывод прямых зависимостей;
- `run(config)` — получение и вывод зависимостей, код завершения;
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

Формат вывода (список зависимостей зависит от пакета и версии):

```
> python src/main.py --config configs/config.yaml
Direct dependencies of Newtonsoft.Json 13.0.3:
  Microsoft.CSharp 4.3.0 [.NETStandard1.0]
  NETStandard.Library 1.6.1 [.NETStandard1.0]
  System.ComponentModel.TypeConverter 4.3.0 [.NETStandard1.0]
  System.Runtime.Serialization.Primitives 4.3.0 [.NETStandard1.0]
  Microsoft.CSharp 4.3.0 [.NETStandard1.3]
  NETStandard.Library 1.6.1 [.NETStandard1.3]
  System.ComponentModel.TypeConverter 4.3.0 [.NETStandard1.3]
  System.Runtime.Serialization.Formatters 4.3.0 [.NETStandard1.3]
  System.Runtime.Serialization.Primitives 4.3.0 [.NETStandard1.3]
  System.Xml.XmlDocument 4.3.0 [.NETStandard1.3]
  
  <имя> <диапазон версий> [<целевой фреймворк>]
```

Пакет не найден:

```
> python src/main.py --config configs/config_missing.yaml
Error: package Missing.Package 1.0.0 not found
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
