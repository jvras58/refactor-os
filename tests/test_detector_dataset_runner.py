"""Deterministic tests for MultiDetectorDatasetRunner (checkpoint/resume/limit),
using a fake service so no LLM/DB is touched."""
from __future__ import annotations

import asyncio

from app.core.exceptions import InvalidPythonCodeError
from app.services.detector_dataset_runner import MultiDetectorDatasetRunner


class _FakeScan:
    def model_dump(self, mode="json"):
        return {"fake": True}


class _FakeService:
    """Scripted stand-in: 'detected' content sentinel decides the compiled output."""

    def __init__(self):
        self.detect_calls: list[str] = []

    async def detect(self, source_code: str):
        self.detect_calls.append(source_code)
        if "BROKEN" in source_code:
            raise InvalidPythonCodeError("código não compila como Python: fake", line=1)
        return _FakeScan()

    def compile(self, scan):
        return ["God Class"] if scan else []


def _write_examples(tmp_path):
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "a.py").write_text("class Big: ...\n", encoding="utf-8")
    (examples / "b.py").write_text("def f(): return 1\n", encoding="utf-8")
    (examples / "c.py").write_text("BROKEN(:\n", encoding="utf-8")
    return examples


def test_runner_processes_all_files_and_writes_checkpoint(tmp_path):
    examples = _write_examples(tmp_path)
    checkpoint = tmp_path / "checkpoint.jsonl"
    service = _FakeService()
    runner = MultiDetectorDatasetRunner(examples, checkpoint, service=service)

    records = asyncio.run(runner.run())

    assert {r["file"] for r in records} == {"a.py", "b.py", "c.py"}
    assert len(service.detect_calls) == 3
    error_record = next(r for r in records if r["file"] == "c.py")
    assert error_record["error"]["phase"] == 1


def test_runner_resumes_without_reprocessing_done_files(tmp_path):
    examples = _write_examples(tmp_path)
    checkpoint = tmp_path / "checkpoint.jsonl"
    service = _FakeService()
    runner = MultiDetectorDatasetRunner(examples, checkpoint, service=service)

    asyncio.run(runner.run(limit=2))
    assert len(service.detect_calls) == 2

    records = asyncio.run(runner.run())  # continua, sem limit
    assert len(service.detect_calls) == 3  # só processou o que faltava
    assert len(records) == 3


def test_runner_limit_caps_new_files_per_call(tmp_path):
    examples = _write_examples(tmp_path)
    checkpoint = tmp_path / "checkpoint.jsonl"
    service = _FakeService()
    runner = MultiDetectorDatasetRunner(examples, checkpoint, service=service)

    records = asyncio.run(runner.run(limit=1))
    assert len(records) == 1
    assert len(service.detect_calls) == 1


def test_runner_reset_clears_checkpoint(tmp_path):
    examples = _write_examples(tmp_path)
    checkpoint = tmp_path / "checkpoint.jsonl"
    service = _FakeService()
    runner = MultiDetectorDatasetRunner(examples, checkpoint, service=service)

    asyncio.run(runner.run())
    assert len(service.detect_calls) == 3

    asyncio.run(runner.run(reset=True))
    assert len(service.detect_calls) == 6  # reprocessou tudo de novo
