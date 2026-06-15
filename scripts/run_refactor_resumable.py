"""Avaliação do Refatorador **resumível** — pensada para modelos locais lentos.

O ``evaluate_refactor`` roda o pipeline completo (detect + reflection) por problema,
o que em modelo local/CPU leva muitos minutos cada. Este runner grava um checkpoint
JSONL por problema concluído: se a execução for interrompida, basta rodar de novo que
ele **pula os já feitos** e continua. Ao terminar todos, escreve o JSON + Markdown
finais (mesmo formato do ``run_evaluation.py``).

O backend do LLM vem das settings (``.env`` / variáveis de ambiente), igual ao
``run_evaluation.py``. Exemplos:

    # API Mistral online
    uv run python scripts/run_refactor_resumable.py

    # modelo local via Ollama
    set LLM_PROVIDER=ollama && set LLM_MODEL_ID=mistral && \
        uv run python scripts/run_refactor_resumable.py \
        --json dataset/reports/local-mistral-refactor.json

    # recomeçar do zero (descarta o checkpoint)
    uv run python scripts/run_refactor_resumable.py --reset
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.core.schemas import RefactorQualityMetrics, RefactorRequest
from app.services.evaluation_service import EvaluationService
from app.services.quality_checks import assess_refactoring

try:  # roda como `python scripts/...` (scripts/ no sys.path) ou como módulo
    from scripts.run_evaluation import to_markdown
except ImportError:
    from run_evaluation import to_markdown

DEFAULT_JSON = Path("dataset/reports/refactor-eval.json")


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _load_checkpoint(path: Path) -> dict[str, dict]:
    done: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                done[record["file"]] = record
    return done


def _append_checkpoint(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _score(label, original, expected_pattern, result) -> dict:
    if result.proposal is None:
        return {
            "file": label, "expected_pattern": expected_pattern.value, "applied_pattern": None,
            "pattern_correct": False, "syntax_valid": False, "logic_preserved": False,
            "missing_public_api": [], "is_correct": False,
            "approved": result.approved, "iterations": result.iterations,
        }
    assessment = assess_refactoring(
        original, result.proposal.refactored_code, result.proposal.applied_pattern, expected_pattern
    )
    return {
        "file": label, "expected_pattern": expected_pattern.value,
        "applied_pattern": result.proposal.applied_pattern.value,
        "pattern_correct": assessment["pattern_correct"],
        "syntax_valid": assessment["syntax_valid"],
        "logic_preserved": assessment["logic_preserved"],
        "missing_public_api": assessment["api_detail"].get("missing", []),
        "is_correct": assessment["is_correct"],
        "approved": result.approved, "iterations": result.iterations,
    }


def _aggregate(inputs, done: dict[str, dict]) -> RefactorQualityMetrics:
    per_file = [done[label] for label, _, _ in inputs if label in done]
    scored = [r for r in per_file if not r.get("error")]
    total = len(inputs)
    return RefactorQualityMetrics(
        total=total,
        accuracy=_safe_div(sum(r["is_correct"] for r in scored), total),
        pattern_accuracy=_safe_div(sum(r["pattern_correct"] for r in scored), total),
        syntax_valid_rate=_safe_div(sum(r["syntax_valid"] for r in scored), total),
        logic_preserved_rate=_safe_div(sum(r["logic_preserved"] for r in scored), total),
        pipeline_approved_rate=_safe_div(sum(r.get("approved", False) for r in scored), total),
        avg_iterations=_safe_div(sum(r.get("iterations", 0) for r in scored), total),
        per_file=per_file,
    )


async def main() -> int:
    parser = argparse.ArgumentParser(description="Avaliação resumível do Agente Refatorador.")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON, help="caminho do relatório JSON final")
    parser.add_argument("--md", type=Path, help="caminho do relatório Markdown (default: ao lado do JSON)")
    parser.add_argument("--checkpoint", type=Path, help="JSONL de checkpoint (default: <json>.partial.jsonl)")
    parser.add_argument("--reset", action="store_true", help="descarta o checkpoint e recomeça do zero")
    args = parser.parse_args()

    json_out = args.json
    md_out = args.md or json_out.with_suffix(".md")
    checkpoint = args.checkpoint or json_out.with_suffix(".partial.jsonl")
    json_out.parent.mkdir(parents=True, exist_ok=True)
    if args.reset and checkpoint.exists():
        checkpoint.unlink()

    service = EvaluationService()
    inputs = service._refactor_inputs_from_dataset()  # noqa: SLF001
    done = _load_checkpoint(checkpoint)
    print(f"total={len(inputs)} concluídos={len(done)} restantes={len(inputs) - len(done)}", flush=True)

    import time

    for idx, (label, original, expected_pattern) in enumerate(inputs, 1):
        if label in done:
            print(f"[{idx}/{len(inputs)}] pula {label}", flush=True)
            continue
        started = time.time()
        try:
            result = await service._service.run(  # noqa: SLF001
                RefactorRequest(source_code=original, file_name=label)
            )
            record = _score(label, original, expected_pattern, result)
        except Exception as exc:  # noqa: BLE001
            record = {"file": label, "error": True, "error_msg": str(exc)[:200]}
        _append_checkpoint(checkpoint, record)
        done[label] = record
        status = "ERRO" if record.get("error") else f"is_correct={record['is_correct']}"
        print(f"[{idx}/{len(inputs)}] {label} em {time.time() - started:.0f}s {status}", flush=True)

    metrics = _aggregate(inputs, done)
    payload = {"refactor": metrics.model_dump()}
    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_out.write_text(to_markdown(payload), encoding="utf-8")
    print(
        f"PRONTO. accuracy={metrics.accuracy:.3f} pattern={metrics.pattern_accuracy:.3f} "
        f"aprovado={metrics.pipeline_approved_rate:.3f}\n  JSON: {json_out}\n  MD:   {md_out}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
