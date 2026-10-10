import os
import sys
import pytest
import requests
from starlette.testclient import TestClient

# Ensure backend root is on sys.path and is current working directory
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)
os.chdir(backend_root)

from app.main import app
from app.database.database import init_db

# Ensure database tables exist
init_db()

test_client = TestClient(app, base_url="http://127.0.0.1:8000")

_real_request = requests.Session.request


def is_live_server_running(url: str = "http://127.0.0.1:8000/health") -> bool:
    try:
        r = _real_request(requests.Session(), "GET", url, timeout=0.3)
        return r.status_code == 200
    except Exception:
        return False


_server_live = is_live_server_running()


def custom_request(self, method, url, **kwargs):
    if _server_live:
        return _real_request(self, method, url, **kwargs)

    # Route through TestClient in-memory if no live server is running
    parsed_path = url
    for prefix in ("http://127.0.0.1:8000", "http://localhost:8000", "http://127.0.0.1:8001", "http://localhost:8001"):
        if url.startswith(prefix):
            parsed_path = url[len(prefix):]
            break

    # Translate requests arguments to TestClient arguments
    headers = kwargs.get("headers")
    params = kwargs.get("params")
    json_data = kwargs.get("json")
    data = kwargs.get("data")
    files = kwargs.get("files")

    # Starlette testclient expects files in form data
    res = test_client.request(
        method=method,
        url=parsed_path,
        headers=headers,
        params=params,
        json=json_data,
        data=data,
        files=files,
    )

    # Wrap TestClient Response to mimic requests.Response interface
    return res


@pytest.fixture(autouse=True)
def route_requests_to_testclient(monkeypatch):
    """Ensure tests run cleanly with or without a standalone background server."""
    if not _server_live:
        monkeypatch.setattr(requests.Session, "request", custom_request)
        monkeypatch.setattr(requests, "get", lambda url, **kw: custom_request(requests.Session(), "GET", url, **kw))
        monkeypatch.setattr(requests, "post", lambda url, **kw: custom_request(requests.Session(), "POST", url, **kw))
        monkeypatch.setattr(requests, "delete", lambda url, **kw: custom_request(requests.Session(), "DELETE", url, **kw))
