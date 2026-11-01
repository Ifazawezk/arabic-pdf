"""The download script must identify itself and give up politely."""

import importlib.util
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("real_world", ROOT / "bench" / "real_world.py")
real_world = importlib.util.module_from_spec(spec)
spec.loader.exec_module(real_world)


class Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.data


def test_downloads_say_what_they_are(tmp_path, monkeypatch):
    seen = {}

    def urlopen(request, timeout):
        seen["agent"] = request.get_header("User-agent")
        return Response(b"%PDF-1.7")

    monkeypatch.setattr(real_world.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(real_world, "REAL", tmp_path)
    real_world.fetch("doc", "https://example.org/doc.pdf")
    assert seen["agent"] == real_world.USER_AGENT
    assert seen["agent"].startswith("arabic-pdf")
    assert "Mozilla" not in seen["agent"]


def test_an_html_answer_is_not_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(real_world.urllib.request, "urlopen", lambda request, timeout: Response(b"<!doctype html>"))
    monkeypatch.setattr(real_world, "REAL", tmp_path)
    with pytest.raises(ValueError):
        real_world.fetch("doc", "https://example.org/doc.pdf")
    assert not (tmp_path / "doc" / "doc.pdf").exists()


def test_a_refusing_source_is_skipped_once_and_reported(tmp_path, monkeypatch, capsys):
    calls = []

    def urlopen(request, timeout):
        calls.append(request.full_url)
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(real_world.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(real_world, "REAL", tmp_path)
    monkeypatch.setattr(sys, "argv", ["real_world.py"])
    real_world.main()
    assert len(calls) == len(set(calls)) == len(real_world.SOURCES)  # one try each, no retry
    assert capsys.readouterr().out.count("skipped") == len(real_world.SOURCES)
