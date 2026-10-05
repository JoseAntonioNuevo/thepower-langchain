"""Resumen local de un lote S6; no llama a modelos ni a plataformas.

Genera una plantilla de revisión. Solo incorpora notas que tú aportes por CSV.
Nunca modifica resultados.json ni convierte una revisión pendiente en un cero.
"""
import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean


def numeric(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def validate(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("Se necesita una lista no vacía de resultados.")
    ids, pairs = set(), set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Cada resultado debe ser un objeto.")
        if any(not isinstance(row.get(k), str) or not row[k] for k in ("query_id", "case_id", "prompt_version")):
            raise ValueError("Faltan query_id, case_id o prompt_version válidos.")
        pair = (row["case_id"], row["prompt_version"])
        if row["query_id"] in ids or pair in pairs:
            raise ValueError("Hay resultados duplicados; no se mezclan lotes ni repeticiones.")
        ids.add(row["query_id"]); pairs.add(pair)
        if row.get("quality") is not None and (type(row["quality"]) not in (int, float) or row["quality"] not in (0, 1)):
            raise ValueError("quality debe ser 0, 1 o null.")
    return rows


def apply_reviews(rows, path):
    import copy
    rows = copy.deepcopy(rows)
    by_id = {r["query_id"]: r for r in rows}
    seen = set()
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        for review in csv.DictReader(f):
            qid = review.get("query_id", "")
            if qid not in by_id or qid in seen:
                raise ValueError("La revisión tiene un ID desconocido o repetido.")
            seen.add(qid)
            row = by_id[qid]
            if any(review.get(k) != row[k] for k in ("case_id", "prompt_version")):
                raise ValueError("La revisión no corresponde al caso y versión del lote.")
            score = review.get("quality", "").strip()
            if not score:
                continue
            if score not in {"0", "1"} or not review.get("motivo", "").strip():
                raise ValueError("Cada nota debe ser 0 o 1 y tener un motivo.")
            row["quality"] = int(score)
            row["review_reason"] = review["motivo"].strip()
    return rows


def summarize(rows):
    validate(rows)
    groups = {}
    for row in rows:
        groups.setdefault(row["prompt_version"], []).append(row)
    result = {}
    for version, group in sorted(groups.items()):
        reviewed = [r for r in group if r.get("quality") is not None]
        entry = {"total": len(group), "reviewed": len(reviewed), "correct": sum(r["quality"] for r in reviewed),
                 "pending": len(group)-len(reviewed), "errors": sum(bool(r.get("errors")) for r in group)}
        for field in ("duration_s", "total_tokens", "cost_usd"):
            values = [r[field] for r in group if numeric(r.get(field))]
            entry[field] = {"known": len(values), "mean": mean(values) if values else None,
                            "sum": sum(values) if values else None}
        result[version] = entry
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("resultados", type=Path)
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--revision", type=Path)
    args = p.parse_args()
    try:
        original = validate(json.loads(args.resultados.read_text(encoding="utf-8")))
        rows = apply_reviews(original, args.revision) if args.revision else original
        summary = summarize(rows)
        # Nunca sobreescribir un informe o una revisión anterior.
        args.salida.mkdir(parents=True, exist_ok=False)
        with (args.salida / "revision.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["query_id", "case_id", "prompt_version", "quality", "motivo"])
            w.writeheader()
            for row in rows:
                w.writerow({**{k: row[k] for k in ("query_id", "case_id", "prompt_version")},
                            "quality": "" if row.get("quality") is None else row["quality"],
                            "motivo": row.get("review_reason", "")})
        (args.salida / "resumen.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (args.salida / "resultados-revisados.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        lines = ["# Resumen de evaluación", "", "No es un benchmark: describe únicamente este lote.",
                 "No se ha ejecutado un evaluador automático ni se han enviado notas a plataformas.", "",
                 "| Versión | Aciertos / revisados | Pendientes / total | Con errores | Duración media (cobertura) | Coste conocido (cobertura) |",
                 "|---|---|---|---|---|---|"]
        for v, s in summary.items():
            d, c = s["duration_s"], s["cost_usd"]
            ds = "N/D" if d["mean"] is None else f'{d["mean"]:.3f} s'
            cs = "N/D" if c["sum"] is None else f'{c["sum"]:.7f} USD'
            safe_v = v.replace("|", "\\|").replace("\n", " ")
            lines.append(f'| {safe_v} | {s["correct"]}/{s["reviewed"]} | {s["pending"]}/{s["total"]} | {s["errors"]} | {ds} ({d["known"]}/{s["total"]}) | {cs} ({c["known"]}/{s["total"]}) |')
        lines += ["", "Los costes parciales no representan el coste total del lote. N/D no significa cero.",
                  "duration_s conserva la definición del runner; no es latencia pura del modelo.",
                  "Antes de comparar, comprueba mismos casos, modelo, parámetros y versión exacta del prompt.",
                  "Completa revision.csv con quality 0/1 y motivo; guarda el CSV como texto para evitar fórmulas."]
        (args.salida / "resumen.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
        print(args.salida)
    except (ValueError, OSError, KeyError) as exc:
        p.exit(2, f"No se ha completado el resumen: {exc}\n")


if __name__ == "__main__":
    main()
