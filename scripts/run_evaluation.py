"""CLI para avaliar empiricamente os três agentes do pipeline.

Roda contra a API Mistral (precisa de ``MISTRAL_API_KEY`` no ``.env``) e o pgvector.
Gera tabelas no terminal e, opcionalmente, relatórios JSON e Markdown prontos para o
relatório da disciplina.

Exemplos:
    uv run python scripts/run_evaluation.py --all
    uv run python scripts/run_evaluation.py --detector --critic
    uv run python scripts/run_evaluation.py --all --md dataset/reports/eval.md --json dataset/reports/eval.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.core.schemas import ConfusionMatrix
from app.services.evaluation_service import EvaluationService


def _pct(value: float) -> str:
    return f"{value * 100:5.1f}%"


def _confusion_block(cm: ConfusionMatrix, positive: str, negative: str) -> list[str]:
    return [
        f"  Matriz de confusão (positivo = {positive}):",
        f"    TP={cm.true_positive:<3} FN={cm.false_negative:<3}   (esperado {positive})",
        f"    FP={cm.false_positive:<3} TN={cm.true_negative:<3}   (esperado {negative})",
    ]


def format_detector(m) -> str:
    lines = ["", "=" * 68, "1) AGENTE RASTREADOR (Detector — multi-label)", "=" * 68]
    lines += _confusion_block(m.confusion, "tipo presente", "tipo ausente")
    lines += [
        "",
        f"  Decisões avaliadas: {m.confusion.total} (arquivos: {m.total_files} × 8 tipos)",
        f"  Falsos Negativos (deixou passar) : {m.confusion.false_negative}  | FNR={_pct(m.false_negative_rate)}",
        f"  Falsos Positivos (viu onde não há): {m.confusion.false_positive}  | FPR={_pct(m.false_positive_rate)}",
        "",
        f"  Precision={_pct(m.precision)}  Recall={_pct(m.recall)}  F1={_pct(m.f1)}",
        f"  Accuracy={_pct(m.accuracy)}  Specificity={_pct(m.specificity)}",
        f"  Conjunto exato por arquivo (exact match): {_pct(m.exact_match_rate)}",
        "",
        f"  {'arquivo':<46}{'exato':<7}{'faltou / sobrou'}",
        "  " + "-" * 64,
    ]
    for r in m.per_file:
        if r.get("error"):
            lines.append(f"  {r['file']:<46}{'ERRO':<7}")
            continue
        detail = ""
        if r["missing"]:
            detail += f"faltou: {', '.join(r['missing'])}"
        if r["extra"]:
            detail += ("  " if detail else "") + f"sobrou: {', '.join(r['extra'])}"
        lines.append(f"  {r['file']:<46}{'sim' if r['exact_match'] else 'não':<7}{detail}")
    return "\n".join(lines)


def format_refactor(m) -> str:
    lines = ["", "=" * 68, "2) AGENTE REFATORADOR (Recommender)", "=" * 68]
    lines += [
        f"  Problemas avaliados: {m.total}",
        f"  Accuracy (totalmente correto): {_pct(m.accuracy)}",
        f"  Pattern correto={_pct(m.pattern_accuracy)}  Sintaxe válida={_pct(m.syntax_valid_rate)}  "
        f"API preservada={_pct(m.logic_preserved_rate)}",
        f"  Aprovado pelo Critic={_pct(m.pipeline_approved_rate)}  Iterações médias={m.avg_iterations:.2f}",
        "",
        f"  {'arquivo':<34}{'pat':<4}{'syn':<4}{'api':<4}{'ok':<4}{'esperado->aplicado'}",
        "  " + "-" * 64,
    ]
    for r in m.per_file:
        if r.get("error"):
            lines.append(f"  {r['file']:<34}ERRO")
            continue
        tick = lambda b: "[x] " if b else "[ ] "  # noqa: E731
        lines.append(
            f"  {r['file']:<34}{tick(r['pattern_correct'])}{tick(r['syntax_valid'])}"
            f"{tick(r['logic_preserved'])}{tick(r['is_correct'])}"
            f"{r['expected_pattern']} -> {r['applied_pattern']}"
        )
    return "\n".join(lines)


def format_critic(m) -> str:
    lines = ["", "=" * 68, "3) AGENTE REVISOR (Critic)", "=" * 68]
    lines += _confusion_block(m.confusion, "solução correta", "solução incorreta")
    lines += [
        "",
        f"  False Accept (aprovou solução incorreta): {m.confusion.false_positive}  | FAR={_pct(m.false_accept_rate)}",
        f"  False Reject (reprovou solução correta) : {m.confusion.false_negative}  | FRR={_pct(m.false_reject_rate)}",
        "",
        f"  Accuracy={_pct(m.accuracy)}  Precision={_pct(m.precision)}  Recall={_pct(m.recall)}  F1={_pct(m.f1)}",
        "",
        f"  {'solução':<52}{'classe':<18}{'defeito'}",
        "  " + "-" * 72,
    ]
    for r in m.per_file:
        sol = r["solution_file"]
        if r.get("error"):
            lines.append(f"  {sol:<52}ERRO (resposta não-estruturada)")
            continue
        lines.append(f"  {sol:<52}{r['classification']:<18}{r.get('defect_kind') or '-'}")
    return "\n".join(lines)


def _check(value: bool) -> str:
    return "✓" if value else "✗"


def _md_detector(d: dict) -> list[str]:
    cm = d["confusion"]
    out = [
        "## 1. Agente Rastreador (Detector — multi-label)",
        "",
        f"Cada arquivo gera 8 decisões binárias (4 smells + 4 patterns) — "
        f"{d['total_files']} arquivos avaliados.",
        "",
        f"**Falsos Negativos (deixou passar):** {cm['false_negative']}  •  "
        f"**Falsos Positivos (viu onde não há):** {cm['false_positive']}",
        "",
        "| Métrica | Valor |",
        "|---|---|",
        f"| Precision | {d['precision']:.3f} |",
        f"| Recall | {d['recall']:.3f} |",
        f"| Accuracy | {d['accuracy']:.3f} |",
        f"| Specificity | {d['specificity']:.3f} |",
        f"| F1 | {d['f1']:.3f} |",
        f"| FPR (taxa de falso positivo) | {d['false_positive_rate']:.3f} |",
        f"| FNR (taxa de falso negativo) | {d['false_negative_rate']:.3f} |",
        f"| Exact match (conjunto por arquivo) | {d['exact_match_rate']:.3f} |",
        "",
        "### Matriz de confusão (pares arquivo × tipo)",
        "",
        "| | Detectou o tipo | Não detectou |",
        "|---|:---:|:---:|",
        f"| **Tipo presente** | {cm['true_positive']} (TP) | {cm['false_negative']} (FN) |",
        f"| **Tipo ausente** | {cm['false_positive']} (FP) | {cm['true_negative']} (TN) |",
        "",
        "### Detalhe por arquivo",
        "",
        "| Arquivo | Exato | Esperado | Detectado |",
        "|---|:---:|---|---|",
    ]
    for r in d["per_file"]:
        if r.get("error"):
            out.append(f"| {r['file']} | ERRO | {', '.join(r['expected_problems'])} | — |")
            continue
        out.append(
            f"| {r['file']} | {_check(r['exact_match'])} "
            f"| {', '.join(r['expected_problems']) or '—'} "
            f"| {', '.join(r['detected_problems']) or '—'} |"
        )
    out.append("")
    return out


def _md_refactor(r: dict) -> list[str]:
    out = [
        "## 2. Agente Refatorador (Recommender)",
        "",
        f"**Accuracy (totalmente correto):** {r['accuracy']:.3f} sobre {r['total']} problemas",
        "",
        "| Métrica | Valor |",
        "|---|---|",
        f"| Pattern correto | {r['pattern_accuracy']:.3f} |",
        f"| Sintaxe válida | {r['syntax_valid_rate']:.3f} |",
        f"| API pública preservada | {r['logic_preserved_rate']:.3f} |",
        f"| Aprovado pelo Critic | {r['pipeline_approved_rate']:.3f} |",
        f"| Iterações médias | {r['avg_iterations']:.2f} |",
        "",
        "### Detalhe por problema",
        "",
        "| Arquivo | Pattern | Sintaxe | API | OK | Esperado → Aplicado |",
        "|---|:---:|:---:|:---:|:---:|---|",
    ]
    for f in r["per_file"]:
        if f.get("error"):
            out.append(f"| {f['file']} | ERRO | | | | |")
            continue
        out.append(
            f"| {f['file']} | {_check(f['pattern_correct'])} | {_check(f['syntax_valid'])} "
            f"| {_check(f['logic_preserved'])} | {_check(f['is_correct'])} "
            f"| {f['expected_pattern']} → {f['applied_pattern']} |"
        )
    out.append("")
    return out


def _md_critic(c: dict) -> list[str]:
    cm = c["confusion"]
    out = [
        "## 3. Agente Revisor (Critic)",
        "",
        f"**False Accept (aprovou incorreta):** {cm['false_positive']} (FAR={c['false_accept_rate']:.3f})  •  "
        f"**False Reject (reprovou correta):** {cm['false_negative']} (FRR={c['false_reject_rate']:.3f})",
        "",
        "| Métrica | Valor |",
        "|---|---|",
        f"| Accuracy | {c['accuracy']:.3f} |",
        f"| Precision | {c['precision']:.3f} |",
        f"| Recall | {c['recall']:.3f} |",
        f"| F1 | {c['f1']:.3f} |",
        "",
        "### Matriz de confusão",
        "",
        "| | Critic aprovou | Critic reprovou |",
        "|---|:---:|:---:|",
        f"| **Solução correta** | {cm['true_positive']} (TP) | {cm['false_negative']} (FN) |",
        f"| **Solução incorreta** | {cm['false_positive']} (FP) | {cm['true_negative']} (TN) |",
        "",
        "### Detalhe por solução",
        "",
        "| Solução | Classe | Defeito |",
        "|---|:---:|---|",
    ]
    for r in c["per_file"]:
        if r.get("error"):
            out.append(f"| {r['solution_file']} | ERRO (resposta não-estruturada) | — |")
            continue
        out.append(
            f"| {r['solution_file']} | {r['classification']} | {r.get('defect_kind') or '-'} |"
        )
    out.append("")
    return out


def to_markdown(payload: dict) -> str:
    out = [
        "# Relatório de Avaliação — refactor-os",
        "",
        f"_Gerado em {datetime.now():%Y-%m-%d %H:%M}_",
        "",
        "Avaliação independente dos três agentes do pipeline "
        "(Rastreador → Refatorador → Revisor).",
        "",
    ]
    if "detector" in payload:
        out += _md_detector(payload["detector"])
    if "refactor" in payload:
        out += _md_refactor(payload["refactor"])
    if "critic" in payload:
        out += _md_critic(payload["critic"])
    return "\n".join(out)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Avaliação empírica dos agentes do refactor-os.")
    parser.add_argument("--detector", action="store_true", help="avalia o Agente Rastreador")
    parser.add_argument("--refactor", action="store_true", help="avalia o Agente Refatorador")
    parser.add_argument("--critic", action="store_true", help="avalia o Agente Revisor")
    parser.add_argument("--all", action="store_true", help="avalia os três agentes (padrão)")
    parser.add_argument("--json", type=Path, help="grava o relatório JSON neste caminho")
    parser.add_argument("--md", type=Path, help="grava o relatório Markdown neste caminho")
    args = parser.parse_args()

    run_all = args.all or not (args.detector or args.refactor or args.critic)
    service = EvaluationService()
    payload: dict = {}
    rendered: list[str] = []
    if run_all or args.detector:
        m = await service.evaluate_detector()
        payload["detector"] = m.model_dump()
        rendered.append(format_detector(m))
    if run_all or args.refactor:
        m = await service.evaluate_refactor()
        payload["refactor"] = m.model_dump()
        rendered.append(format_refactor(m))
    if run_all or args.critic:
        try:
            m = await service.evaluate_critic()
        except FileNotFoundError as exc:
            rendered.append(f"\n3) AGENTE REVISOR (Critic): pulado — {exc}")
        else:
            payload["critic"] = m.model_dump()
            rendered.append(format_critic(m))

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        rendered.append(f"\nJSON salvo em {args.json}")
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(to_markdown(payload), encoding="utf-8")
        rendered.append(f"Markdown salvo em {args.md}")

    print("\n".join(rendered))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
