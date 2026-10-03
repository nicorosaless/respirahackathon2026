"""El marcador del proyecto: una sola cifra y sus componentes, siempre calculados igual.

Mide si la puntuación de daño hace lo que pide el reto: seguir la limitación al
flujo aéreo, la DLCO y los síntomas, separar EPOC de control, no depender de la
reconstrucción de la TC y no distinguir sexo ni tabaquismo.

    python scripts/evaluate.py mn5/cohorte.early.toml --duro outputs/cohorte_duro --etiqueta "línea base"

Por defecto evalúa solo los sujetos de desarrollo. `--reserva` evalúa los
reservados: se usa una vez, al final, y queda registrado.

Este fichero es el árbitro. Mejorar el marcador cambiando el evaluador no
cuenta: los cambios van en las medidas, en el modelo normativo o en la
puntuación.
"""

from __future__ import annotations

import argparse
import json
import time
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

from maps.cohort import DEFAULT_SCORE_MEASURES, damage_score, lung_volume, region_z_applied

N_BOOTSTRAP = 2000


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 8 or np.ptp(x[ok]) == 0 or np.ptp(y[ok]) == 0:
        return float("nan")
    return float(stats.spearmanr(x[ok], y[ok]).statistic)


def auc(labels: np.ndarray, score: np.ndarray) -> float:
    ok = np.isfinite(labels) & np.isfinite(score)
    if len(np.unique(labels[ok])) < 2:
        return float("nan")
    return float(roc_auc_score(labels[ok], score[ok]))


def icc_agreement(a: np.ndarray, b: np.ndarray) -> float:
    """ICC(A,1): acuerdo absoluto entre dos medidas del mismo sujeto. Penaliza también un desplazamiento sistemático."""
    ok = np.isfinite(a) & np.isfinite(b)
    data = np.column_stack([a[ok], b[ok]])
    n, k = data.shape
    if n < 8:
        return float("nan")
    grand = data.mean()
    ms_rows = k * ((data.mean(axis=1) - grand) ** 2).sum() / (n - 1)
    ms_cols = n * ((data.mean(axis=0) - grand) ** 2).sum() / (k - 1)
    residual = data - data.mean(axis=1, keepdims=True) - data.mean(axis=0, keepdims=True) + grand
    ms_error = (residual**2).sum() / ((n - 1) * (k - 1))
    return float((ms_rows - ms_error) / (ms_rows + (k - 1) * ms_error + k * (ms_cols - ms_error) / n))


def components(t: pd.DataFrame) -> dict[str, float]:
    """Cada componente va de -1 a 1 y es mejor cuanto mayor. `t` lleva una fila por sujeto."""
    score = t["puntuacion_dano"].to_numpy(dtype=float)
    control = (t["caso_v1"] == 0).to_numpy()
    out = {
        "flujo_aereo": -spearman(score, t["fev1_fvc_post_v1"].to_numpy(dtype=float)),
        "dlco": -spearman(score, t["DLCO_v1"].to_numpy(dtype=float)),
        "sintomas_en_controles": spearman(score[control], t.loc[control, "CAT_v1"].to_numpy(dtype=float)),
        "separa_epoc": 2 * auc(t["caso_v1"].to_numpy(dtype=float), score) - 1,
    }
    if "puntuacion_duro" in t:
        out["robustez_kernel"] = icc_agreement(t["puntuacion_base"].to_numpy(dtype=float), t["puntuacion_duro"].to_numpy(dtype=float))
    nuisance = [abs(2 * auc((t[column] == level).to_numpy(dtype=float), score) - 1)
                for column, level in (("sexo", "mujer"), ("fuma", "fuma"))]
    out["penalizacion_confusores"] = float(np.nanmean(nuisance))
    return out


def headline(parts: dict[str, float]) -> float:
    good = [value for key, value in parts.items() if key != "penalizacion_confusores"]
    return float(np.nanmean(good) - parts["penalizacion_confusores"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--duro", type=Path, help="cohorte de los mismos sujetos con otro kernel de reconstrucción")
    parser.add_argument("--etiqueta", default="", help="qué cambio se está evaluando")
    parser.add_argument("--reserva", action="store_true", help="evalúa los sujetos reservados; solo al final")
    args = parser.parse_args()

    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])
    subjects = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    zscores = pd.read_csv(cohort / "zscores.csv", dtype={"subject_id": str})
    features = pd.read_csv(cohort / "features.csv", dtype={"subject_id": str})
    measures = tuple(config.get("puntuacion", {}).get("medidas", DEFAULT_SCORE_MEASURES))
    normative = config["normativo"]
    covariates, categorical = normative["covariables"], normative.get("categoricas", [])

    if args.duro is not None:
        # Mismo modelo normativo, sin reajustar, sobre las dos reconstrucciones de cada sujeto.
        hard = pd.read_csv(args.duro / "features.csv", dtype={"subject_id": str})
        hard = hard[hard["subject_id"].isin(subjects.index)]
        reference = subjects["referencia"].astype(bool)
        hard_subjects = subjects.drop(columns="volumen_pulmon_ml").join(lung_volume(hard), how="inner")
        base_z = region_z_applied(features, features, subjects, subjects, reference, covariates, categorical)
        hard_z = region_z_applied(features, hard, subjects, hard_subjects, reference, covariates, categorical)
        subjects["puntuacion_base"] = damage_score(base_z, measures)
        subjects["puntuacion_duro"] = damage_score(hard_z, measures)

    split = "reserva" if args.reserva else "desarrollo"
    t = subjects[subjects["particion"] == split]
    parts = components(t)
    rng = np.random.default_rng(0)
    resampled = [headline(components(t.iloc[rng.integers(0, len(t), len(t))])) for _ in range(N_BOOTSTRAP)]
    result = {
        "cuando": time.strftime("%Y-%m-%d %H:%M"), "etiqueta": args.etiqueta, "particion": split, "sujetos": len(t),
        "marcador": round(headline(parts), 4), "error_estandar": round(float(np.nanstd(resampled)), 4),
        "componentes": {key: round(value, 4) for key, value in parts.items()}, "medidas": list(measures),
        "covariables": [*covariates, *categorical],
    }
    with (cohort.parent / "marcador.jsonl").open("a") as log:
        log.write(json.dumps(result, ensure_ascii=False) + "\n")
    if args.reserva:
        with (cohort.parent / "reserva_usos.log").open("a") as log:
            log.write(f"{result['cuando']} {args.etiqueta}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Diagnóstico por medida, para decidir qué entra en la puntuación. Solo desarrollo.
    if not args.reserva:
        whole = zscores[zscores["region"] == "pulmon"].set_index("subject_id")
        lobes = zscores[zscores["region"] != "pulmon"].drop(columns="region").groupby("subject_id").mean()
        rows = []
        for measure in [c for c in zscores.columns if c not in ("subject_id", "region")]:
            z = whole[measure] if whole[measure].notna().any() else lobes[measure]
            z = lobes[measure].reindex(t.index) if lobes[measure].notna().any() else z.reindex(t.index)
            control = (t["caso_v1"] == 0).to_numpy()
            row = {"medida": measure,
                   "rho FEV1/FVC": spearman(z.to_numpy(dtype=float), t["fev1_fvc_post_v1"].to_numpy(dtype=float)),
                   "rho DLCO": spearman(z.to_numpy(dtype=float), t["DLCO_v1"].to_numpy(dtype=float)),
                   "rho CAT controles": spearman(z.to_numpy(dtype=float)[control], t.loc[control, "CAT_v1"].to_numpy(dtype=float)),
                   "AUC EPOC": auc(t["caso_v1"].to_numpy(dtype=float), z.to_numpy(dtype=float))}
            if args.duro is not None:
                a = features[features["region"] == "pulmon"].set_index("subject_id")[measure].reindex(t.index)
                b = hard[hard["region"] == "pulmon"].set_index("subject_id")[measure].reindex(t.index)
                row["ICC entre kernels"] = icc_agreement(a.to_numpy(dtype=float), b.to_numpy(dtype=float))
            rows.append(row)
        pd.set_option("display.width", 200)
        print("\nz medio de los lóbulos (o del pulmón entero si la medida solo existe ahí), sujetos de desarrollo:")
        print(pd.DataFrame(rows).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
