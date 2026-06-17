"""CLI para rodar o novo MultiDetectorService sobre os exemplos do dataset_2.

Cada arquivo custa 8 chamadas reais de LLM (fase 3, uma por smell/pattern), throttled a 20s entre chamadas
(``app.utils.retry``) — 30 arquivos = ~80+ minutos. Use ``--limit`` para testar com
poucos arquivos antes de rodar tudo. A execução é resumível: interrompeu? roda de
novo que ele pula os arquivos já no checkpoint.

O log detalhado de entrada/saída de cada fase (heurística, prompts, respostas da
LLM) sai pelo `logging` — passe ``--log-level DEBUG`` para ver o conteúdo completo
dos prompts e respostas; o default ``INFO`` mostra só um resumo por fase.

Exemplos:
    # testar com 2 arquivos antes de rodar tudo
    uv run python scripts/run_multi_detector.py --limit 2 --log-level DEBUG

    # rodar o dataset_2/examples inteiro
    uv run python scripts/run_multi_detector.py

    # continuar de onde parou (default — não precisa de flag)
    uv run python scripts/run_multi_detector.py

    # descartar checkpoint e recomeçar do zero
    uv run python scripts/run_multi_detector.py --reset
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from app.services.multi_detector_dataset_runner import MultiDetectorDatasetRunner

DEFAULT_EXAMPLES_DIR = Path("dataset_2/examples")
DEFAULT_CHECKPOINT = Path("dataset_2/reports/multi_detector_checkpoint.jsonl")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--examples-dir", type=Path, default=DEFAULT_EXAMPLES_DIR)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--reset", action="store_true", help="descarta o checkpoint e recomeça do zero")
    parser.add_argument("--limit", type=int, default=None, help="processa só os N primeiros arquivos pendentes")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING"])
    parser.add_argument("--log-file", type=Path, default=Path("dataset_2/reports/multi_detector_run.log"))
    return parser.parse_args()


def _configure_logging(level: str, log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


async def _main() -> None:
    args = _parse_args()
    _configure_logging(args.log_level, args.log_file)

    runner = MultiDetectorDatasetRunner(
        examples_dir=args.examples_dir,
        checkpoint_path=args.checkpoint,
    )
    records = await runner.run(reset=args.reset, limit=args.limit)

    print(f"\n{len(records)} arquivo(s) no checkpoint ({args.checkpoint}):")
    for record in records:
        if "error" in record:
            print(f"  [ERRO fase {record['error']['phase']}] {record['file']}: {record['error']['message']}")
        else:
            print(f"  {record['file']}: {record['compiled']}")
    print(f"\nLog detalhado por fase em: {args.log_file}")


if __name__ == "__main__":
    asyncio.run(_main())
