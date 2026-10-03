"""¿El árbol bronquial corto de los posibles pre-EPOC es enfermedad o un fallo de la segmentación?

Control de calidad automático de las máscaras de TotalSegmentator, sin mirar imágenes:
fragmentación de la vía aérea, FOV cortado, volumen frente a longitud (fugas),
ramas por lóbulo, ruido y adquisición, y el acuerdo de longitud entre el kernel
estándar y el duro. Después compara las métricas entre clases y repite la
relación de la puntuación con FEV1/FVC entre los sin obstrucción quitando a los
sujetos con bandera o descontando las métricas.

    python3 scripts/qa_segmentacion.py mn5/cohorte.final.toml --duro outputs/cohorte_duro_v4 \
        --masks outputs/mascaras_v4 --out outputs/qa_segmentacion

Las máscaras de `--masks` son las de la segmentación original; `cohorte_v4` se
remidió a partir de ellas con el código actual (`remeasure.py`), así que sus
medidas antiguas no coinciden con las de v4, pero la máscara es la misma.

Escribe la tabla por sujeto en `--out` (se queda en MareNostrum) y `agregados.json`,
que solo lleva medianas, recuentos, correlaciones, p e identificadores numéricos.
"""

from __future__ import annotations

import argparse
import json
import tomllib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage, stats

CLASSES = ["control", "pre-EPOC", "EPOC"]
STRUCTURE = np.ones((3, 3, 3), dtype=bool)


def mask_metrics(folder: Path) -> dict[str, float]:
    masks = np.load(folder / "masks.npz")
    meta = json.loads((folder / "meta.json").read_text())
    voxel_ml = float(np.prod(meta["espaciado_mm"])) / 1000.0
    airway = masks["airway"].astype(bool)
    lobes = masks["lobes"]
    lung = lobes > 0
    labels, n = ndimage.label(airway, structure=STRUCTURE)
    sizes = np.bincount(labels.ravel())[1:] if n else np.array([0])
    total = float(airway.sum())
    lobe_z = np.flatnonzero(lung.any(axis=(1, 2)))
    edges = [lung[0], lung[-1], lung[:, 0], lung[:, -1], lung[:, :, 0], lung[:, :, -1]]
    return {
        "subject_id": folder.name,
        "qa_componentes": int(n),
        "qa_componentes_100vox": int((sizes >= 100).sum()),
        "qa_frac_fuera_mayor": float(1.0 - sizes.max() / total) if total else float("nan"),
        "qa_frac_via_fuera_lobulos": float((airway & ~lung).sum() / total) if total else float("nan"),
        "qa_via_ml_fuera_lobulos": float((airway & ~lung).sum()) * voxel_ml,
        "qa_via_ml_dentro_lobulos": float((airway & lung).sum()) * voxel_ml,
        "qa_pulmon_toca_z": int(bool(lung[0].any() or lung[-1].any())),
        "qa_pulmon_toca_borde": int(any(bool(e.any()) for e in edges)),
        "qa_cortes_pulmon": int(lobe_z.size),
        "qa_lobulos_presentes": int(len(set(np.unique(lobes)) - {0})),
    }


def partial_spearman(x: np.ndarray, y: np.ndarray, covariates: np.ndarray) -> tuple[float, float]:
    rank = lambda a: stats.rankdata(a, axis=0)  # noqa: E731
    design = np.column_stack([np.ones(len(x)), rank(covariates)])
    resid = [r - design @ np.linalg.lstsq(design, r, rcond=None)[0] for r in (rank(x), rank(y))]
    r, p = stats.pearsonr(*resid)
    return float(r), float(p)


def tukey_high(values: pd.Series) -> float:
    q1, q3 = values.quantile([0.25, 0.75])
    return float(q3 + 1.5 * (q3 - q1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--duro", type=Path, required=True)
    parser.add_argument("--masks", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])
    ratio_col = config["clasificacion"]["cociente"]
    args.out.mkdir(parents=True, exist_ok=True)

    folders = sorted(p for p in (args.masks / "sujetos").iterdir() if (p / "masks.npz").exists())
    with ProcessPoolExecutor(args.workers) as pool:
        qa = pd.DataFrame(list(pool.map(mask_metrics, folders)))
    qa["subject_id"] = qa["subject_id"].astype(int)

    subjects = pd.read_csv(cohort / "subjects.csv")
    feats = pd.read_csv(cohort / "features.csv")
    whole = feats[feats.region == "pulmon"].set_index("subject_id")
    lobar = feats[feats.region != "pulmon"].pivot(index="subject_id", columns="region", values="via_longitud_lobar_mm")
    duro = pd.read_csv(args.duro / "features.csv")
    duro = duro[duro.region == "pulmon"].set_index("subject_id")
    z = pd.read_csv(cohort / "zscores.csv")
    z = z[z.region == "pulmon"].set_index("subject_id")

    df = subjects.set_index("subject_id")[["clase_maps", "puntuacion_dano", ratio_col, "kvp", "grosor_mm",
                                           "kernel", "modelo"]].join(qa.set_index("subject_id"))
    df["via_longitud_mm"] = whole["via_longitud_mm"]
    df["z_via_longitud"] = z["via_longitud_mm"]
    df["qa_frac_no_conectada"] = 1.0 - whole["via_longitud_conectada_mm"] / whole["via_longitud_mm"]
    df["qa_volumen_por_mm"] = 1000.0 * whole["via_volumen_ml"] / whole["via_longitud_mm"]  # mm³ por mm
    df["qa_extremos_por_m"] = 1000.0 * whole["via_extremos"] / whole["via_longitud_mm"]
    df["qa_ruido_hu"] = whole["ruido_hu"]
    df["qa_min_lobar_frac"] = lobar.min(axis=1) / lobar.sum(axis=1)
    df["qa_log_std_duro"] = np.log(whole["via_longitud_mm"] / duro["via_longitud_mm"])
    df["qa_abs_log_std_duro"] = df["qa_log_std_duro"].abs()
    for col in ("via_volumen_ml", "via_longitud_conectada_mm", "via_calibre_central_mm", "via_extremos"):
        df[col] = whole[col]
    df["grosor_mm"] = pd.to_numeric(df["grosor_mm"], errors="coerce")
    df["kvp"] = pd.to_numeric(df["kvp"], errors="coerce")

    # Banderas fijadas antes de mirar las clases: umbrales absolutos o de Tukey sobre los 80.
    thresholds = {
        "qa_frac_fuera_mayor": 0.05,
        "qa_frac_no_conectada": 0.10,
        "qa_volumen_por_mm": tukey_high(df["qa_volumen_por_mm"]),
        "qa_ruido_hu": tukey_high(df["qa_ruido_hu"]),
        "qa_abs_log_std_duro": tukey_high(df["qa_abs_log_std_duro"]),
    }
    flags = pd.DataFrame({f"b_{k}": df[k] > v for k, v in thresholds.items()})
    flags["b_pulmon_toca_z"] = df["qa_pulmon_toca_z"] == 1
    flags["b_lobulo_sin_via"] = df["qa_min_lobar_frac"] < 0.02
    flags["b_lobulos_incompletos"] = df["qa_lobulos_presentes"] < 5
    df = df.join(flags)
    df["bandera"] = flags.any(axis=1)
    df.to_csv(args.out / "qa_por_sujeto.csv")

    metrics = ["via_longitud_mm", "via_longitud_conectada_mm", "via_volumen_ml", "qa_via_ml_dentro_lobulos",
               "qa_via_ml_fuera_lobulos", "via_calibre_central_mm", "qa_componentes_100vox", "qa_frac_fuera_mayor", "qa_frac_no_conectada", "qa_frac_via_fuera_lobulos",
               "qa_volumen_por_mm", "qa_extremos_por_m", "qa_ruido_hu", "qa_min_lobar_frac", "qa_log_std_duro",
               "qa_abs_log_std_duro", "qa_cortes_pulmon", "grosor_mm", "kvp"]
    out: dict = {"n": {c: int((df.clase_maps == c).sum()) for c in CLASSES},
                 "umbrales": thresholds, "por_metrica": {}}
    for m in metrics:
        groups = [df.loc[df.clase_maps == c, m].dropna() for c in CLASSES]
        entry = {"mediana": {c: float(g.median()) for c, g in zip(CLASSES, groups)},
                 "iqr": {c: [float(g.quantile(0.25)), float(g.quantile(0.75))] for c, g in zip(CLASSES, groups)}}
        if all(g.nunique() > 1 for g in groups) or pd.concat(groups).nunique() > 1:
            entry["kruskal_p"] = float(stats.kruskal(*groups).pvalue)
            entry["mw_pre_vs_control_p"] = float(stats.mannwhitneyu(groups[1], groups[0]).pvalue)
        out["por_metrica"][m] = entry
    out["toca_z"] = {c: int(df.loc[df.clase_maps == c, "qa_pulmon_toca_z"].sum()) for c in CLASSES}
    out["toca_borde"] = {c: int(df.loc[df.clase_maps == c, "qa_pulmon_toca_borde"].sum()) for c in CLASSES}
    out["kernel"] = {c: df.loc[df.clase_maps == c, "kernel"].value_counts().to_dict() for c in CLASSES}

    sin = df[df.clase_maps.isin(["control", "pre-EPOC"])]
    corr = {}
    for m in metrics:
        ok = sin[[m, "puntuacion_dano", "z_via_longitud"]].dropna()
        if ok[m].nunique() < 2:
            continue
        rs = stats.spearmanr(ok[m], ok["puntuacion_dano"])
        rz = stats.spearmanr(ok[m], ok["z_via_longitud"])
        corr[m] = {"rho_puntuacion": float(rs.statistic), "p_puntuacion": float(rs.pvalue),
                   "rho_z_via": float(rz.statistic), "p_z_via": float(rz.pvalue)}
    out["correlacion_52"] = corr

    flag_cols = list(flags.columns)
    pre, ctl = sin[sin.clase_maps == "pre-EPOC"], sin[sin.clase_maps == "control"]
    table = [[int(pre.bandera.sum()), int((~pre.bandera).sum())], [int(ctl.bandera.sum()), int((~ctl.bandera).sum())]]
    out["banderas"] = {
        "pre_con_bandera": table[0][0], "control_con_bandera": table[1][0],
        "epoc_con_bandera": int(df.loc[df.clase_maps == "EPOC", "bandera"].sum()),
        "fisher_p": float(stats.fisher_exact(table).pvalue),
        "por_bandera": {c: {k: int(df.loc[df.clase_maps == k, c].sum()) for k in CLASSES} for c in flag_cols},
        "ids_pre_con_bandera": sorted(int(i) for i in pre.index[pre.bandera]),
        "ids_control_con_bandera": sorted(int(i) for i in ctl.index[ctl.bandera]),
    }

    def rho(frame: pd.DataFrame) -> dict:
        r = stats.spearmanr(frame["puntuacion_dano"], frame[ratio_col])
        return {"n": int(len(frame)), "rho": float(r.statistic), "p": float(r.pvalue)}

    base = sin.dropna(subset=["puntuacion_dano", ratio_col])
    cov_cols = ["qa_frac_fuera_mayor", "qa_frac_no_conectada", "qa_volumen_por_mm", "qa_ruido_hu",
                "qa_abs_log_std_duro", "grosor_mm"]
    cov = base[cov_cols].fillna(base[cov_cols].median())
    independent = ["qa_frac_fuera_mayor", "qa_ruido_hu", "qa_abs_log_std_duro", "grosor_mm"]
    out["robustez_rho_52"] = {
        "todos": rho(base),
        "sin_bandera": rho(base[~base.bandera]),
        "parcial_qa": dict(zip(["rho", "p"], partial_spearman(base.puntuacion_dano.values, base[ratio_col].values,
                                                               cov.values))),
        # Sin las métricas que llevan la longitud en el denominador (volumen por mm, fracción no conectada).
        "parcial_qa_independientes": dict(zip(["rho", "p"], partial_spearman(
            base.puntuacion_dano.values, base[ratio_col].values, cov[independent].values))),
        "parcial_por_metrica": {c: dict(zip(["rho", "p"], partial_spearman(
            base.puntuacion_dano.values, base[ratio_col].values, cov[[c]].values))) for c in cov_cols},
    }
    (args.out / "agregados.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
