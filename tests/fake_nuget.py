"""Локальный HTTP-сервер, имитирующий репозиторий NuGet для тестов."""

import functools
import json
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOCALHOST = "127.0.0.1"
INDEX_PATH = "/v3/index.json"
FLAT_PATH = "/v3-flatcontainer/"
PACKAGE_BASE_TYPE = "PackageBaseAddress/3.0.0"


class QuietHandler(SimpleHTTPRequestHandler):
    """Отдаёт файлы из каталога и не пишет журнал запросов."""

    def log_message(self, *args):
        """Отключает вывод журнала запросов."""


class FakeNuGet:
    """Запускает сервер в отдельном потоке."""

    def __init__(self, files: dict[str, bytes]):
        """Принимает словарь: путь на сервере -> содержимое файла."""
        self.tmp = tempfile.TemporaryDirectory()
        handler = functools.partial(QuietHandler, directory=self.tmp.name)
        self.server = ThreadingHTTPServer((LOCALHOST, 0), handler)
        self.base = f"http://{LOCALHOST}:{self.server.server_port}"
        self.write_file(INDEX_PATH, self.index_json())
        for path, content in files.items():
            self.write_file(path, content)
        self.thread = threading.Thread(target=self.server.serve_forever)

    def write_file(self, url_path: str, content: bytes) -> None:
        """Сохраняет файл так, чтобы сервер отдавал его по url_path."""
        target = Path(self.tmp.name) / url_path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def index_json(self) -> bytes:
        """Формирует сервисный индекс с адресом flat container."""
        resource = {"@id": self.base + FLAT_PATH, "@type": PACKAGE_BASE_TYPE}
        index = {"version": "3.0.0", "resources": [resource]}
        return json.dumps(index).encode()

    @property
    def index_url(self) -> str:
        """URL сервисного индекса."""
        return self.base + INDEX_PATH

    def __enter__(self):
        """Запускает сервер."""
        self.thread.start()
        return self

    def __exit__(self, *exc_info):
        """Останавливает сервер и удаляет временные файлы."""
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()
