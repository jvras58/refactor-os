"""Runs ``MultiDetectorService.detect()`` over every example file in a dataset.

Phase-by-phase input/output is captured via ``logging`` inside
``MultiDetectorService`` itself (INFO = summary, DEBUG = full prompt/response
content) — configure the root/``app.services.multi_detector_service`` logger to
see it. This runner adds:

- Discovery of every ``.py`` file under a directory (e.g. ``dataset_2/examples/``).
- A JSONL checkpoint, one record per finished file, so an interrupted run (each
  file costs 4 real LLM calls, throttled 20s apart by ``app.utils.retry``) can be
  resumed without repeating already-done files — mirrors
  ``scripts/run_refactor_resumable.py``.
- The final compiled (phase 4) result per file, plus the raw scan for inspection.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.multi_detector_exceptions import InvalidPythonCodeError
from app.services.multi_detector_service import MultiDetectorService

logger = logging.getLogger(__name__)


class MultiDetectorDatasetRunner:
    """Runs the new detector over every ``.py`` file under ``examples_dir``."""

    def __init__(
        self,
        examples_dir: Path,
        checkpoint_path: Path,
        service: MultiDetectorService | None = None,
    ) -> None:
        self._examples_dir = examples_dir
        self._checkpoint_path = checkpoint_path
        self._service = service or MultiDetectorService()

    def _discover_files(self) -> list[Path]:
        return sorted(self._examples_dir.rglob("*.py"))

    def _relative_label(self, path: Path) -> str:
        return str(path.relative_to(self._examples_dir))

    def _load_done(self) -> set[str]:
        if not self._checkpoint_path.exists():
            return set()
        done: set[str] = set()
        for line in self._checkpoint_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["file"])
        return done

    def _append(self, record: dict) -> None:
        self._checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with self._checkpoint_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def run(self, reset: bool = False, limit: int | None = None) -> list[dict]:
        """Runs the pipeline over the dataset, returns all records (done + new).

        ``limit`` caps how many *new* files are processed this call — useful to
        try a few files before committing to a full, multi-LLM-call run.
        """
        if reset and self._checkpoint_path.exists():
            self._checkpoint_path.unlink()

        done = self._load_done()
        files = self._discover_files()
        pending = [f for f in files if self._relative_label(f) not in done]
        if limit is not None:
            pending = pending[:limit]

        logger.info(
            "MultiDetectorDatasetRunner: %d arquivos no total, %d já feitos, %d a processar nesta chamada",
            len(files), len(done), len(pending),
        )

        for path in pending:
            label = self._relative_label(path)
            source_code = path.read_text(encoding="utf-8")
            logger.info("=== [%s] iniciando ===", label)
            record: dict = {"file": label}

            try:
                scan = await self._service.detect(source_code)
            except InvalidPythonCodeError as exc:
                logger.error("[%s] fase 1 falhou: %s", label, exc)
                record["error"] = {"phase": 1, "message": str(exc), "line": exc.line}
                self._append(record)
                continue

            compiled = self._service.compile(scan)
            record["scan"] = scan.model_dump(mode="json")
            record["compiled"] = compiled
            logger.info("[%s] concluído — detectados: %s", label, compiled)
            self._append(record)

        return [
            json.loads(line)
            for line in self._checkpoint_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
