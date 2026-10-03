"""Validación cruzada anidada de la puntuación de daño, con todos los sujetos.

En cada vuelta, solo con los sujetos de entrenamiento: se ajusta lo esperado, se
mide el acuerdo entre reconstrucciones, se elige la medida de vía aérea y se
fijan los umbrales. Los sujetos de prueba reciben la puntuación de ese modelo,
que no los vio en ningún paso. Así el rendimiento que se informa incluye el
optimismo de elegir medidas, que la validación anterior dejaba fuera.

Los candidatos y la regla de elección están fijados en `docs/protocolo-mejora.md`.
Escribe `validacion_anidada.json` en el directorio de la cohorte, con agregados.

    python scripts/nested_cv.py mn5/cohorte.final.toml --duro outputs/cohorte_duro_v4
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import RepeatedStratifiedKFold

from check_score import MAD_TO_SD
from evaluate import auc, icc_agreement
from maps.classify import damage_threshold
from maps.cohort import KEYS, apply_region_models, damage_score, fit_region_models, lung_volume, region_z

EMPHYSEMA = "laa950_smooth"
CURRENT = "via_longitud_mm"
# Los candidatos para la medida de vía aérea, fijados antes de mirar.
CANDIDATES = [CURRENT, "via_longitud_fina_mm", "via_fraccion_fina", "via_extremos", "via_ramas", "via_longitud_lobar_mm"]
# Controles: no compiten, se informan. La vía gruesa no debería separar tanto.
CONTROLS = {"via gruesa": (EMPHYSEMA, "via_longitud_gruesa_mm"), "solo vía aérea": (CURRENT,), "solo enfisema": (EMPHYSEMA,),
            "solo vía fina": ("via_longitud_fina_mm",), "solo vía gruesa": ("via_longitud_gruesa_mm",)}
# Comparaciones directas entre dos puntuaciones, con el mismo remuestreo de sujetos para las dos.
CONTRASTS = [("via_longitud_fina_mm", "via gruesa"), ("solo vía fina", "solo vía gruesa")]
N_PERMUTATIONS = 20000
REFERENCES = {"todos los controles": "caso_v1 == 0",
              "controles lejos de la obstrucción": "caso_v1 == 0 and fev1_fvc_post_v1 >= 0.75 and FEV1pp_GLI_v1 >= 80"}
MIN_ICC = 0.90
N_SPLITS, N_REPEATS, N_BOOTSTRAP = 5, 10, 2000


def rho(a: np.ndarray, b: np.ndarray) -> float:
    ok = np.isfinite(a) & np.isfinite(b)
    return float(stats.spearmanr(a[ok], b[ok]).statistic) if ok.sum() >= 8 else float("nan")


def permutation_p(a: np.ndarray, b: np.ndarray, rng: np.random.Generator) -> float:
    """p de la correlación de Spearman, permutando una de las dos variables.

    Vale aquí sin repetir el ajuste: la puntuación fuera de muestra de un sujeto
    no usa su FEV1/FVC ni el de nadie, así que bajo la hipótesis nula los
    cocientes son intercambiables entre los sujetos del grupo.
    """
    ok = np.isfinite(a) & np.isfinite(b)
    ranks_a, ranks_b = stats.rankdata(a[ok]), stats.rankdata(b[ok])
    observed = abs(np.corrcoef(ranks_a, ranks_b)[0, 1])
    centred = ranks_a - ranks_a.mean()
    shuffled = np.array([rng.permutation(ranks_b) for _ in range(N_PERMUTATIONS)])
    null = np.abs(shuffled @ centred) / (np.linalg.norm(centred) * np.linalg.norm(ranks_b - ranks_b.mean()))
    return float((1 + np.count_nonzero(null >= observed - 1e-12)) / (N_PERMUTATIONS + 1))


def normal_limit(reference_scores: pd.Series) -> float:
    centre = float(reference_scores.median())
    return centre + 1.645 * MAD_TO_SD * float((reference_scores - centre).abs().median())


def panels() -> dict[str, tuple[str, ...]]:
    return {measure: (EMPHYSEMA, measure) for measure in CANDIDATES} | CONTROLS


def metrics(score: np.ndarray, ratio: np.ndarray, case: np.ndarray) -> dict[str, float]:
    return {"rho": rho(score, ratio), "rho_controles": rho(score[~case], ratio[~case]),
            "auc": auc(case.astype(float), score)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--duro", type=Path, required=True, help="cohorte de los mismos sujetos con otro kernel de reconstrucción")
    parser.add_argument("--repeticiones", type=int, default=N_REPEATS)
    parser.add_argument("--sin-recuperados", action="store_true",
                        help="deja fuera a los sujetos medidos con la otra reconstrucción; escribe el resultado aparte")
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])
    normative = config["normativo"]
    covariates, categorical = normative["covariables"], normative.get("categoricas", [])

    subjects = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    if args.sin_recuperados:
        subjects = subjects[~subjects.get("de_repuesto", pd.Series(False, index=subjects.index)).astype(bool)]
    measures = sorted({m for panel in panels().values() for m in panel})
    features = pd.read_csv(cohort / "features.csv", dtype={"subject_id": str})[[*KEYS, *measures]]
    features = features[features["subject_id"].isin(subjects.index)]
    hard = pd.read_csv(args.duro / "features.csv", dtype={"subject_id": str})
    hard = hard[hard["subject_id"].isin(subjects.index)]
    hard_subjects = subjects.drop(columns="volumen_pulmon_ml").join(lung_volume(hard), how="inner")
    hard = hard[[*KEYS, *measures]]
    # Los sujetos recuperados de la otra reconstrucción no tienen dos medidas distintas que comparar.
    paired = ~subjects.get("de_repuesto", pd.Series(False, index=subjects.index)).astype(bool)

    ids = subjects.index.to_numpy()
    case = (subjects["caso_v1"] == 1).to_numpy()
    ratio = subjects["fev1_fvc_post_v1"].to_numpy(dtype=float)
    names = [(panel, reference) for reference in REFERENCES for panel in panels()]
    competing = [(measure, reference) for reference in REFERENCES for measure in CANDIDATES]
    choice = ("elegido en cada vuelta", "")
    # Puntuación fuera de muestra de cada sujeto, por repetición; y decisiones con los dos umbrales.
    scores = {name: np.full((args.repeticiones, len(ids)), np.nan) for name in [*names, choice]}
    other = {name: np.full((args.repeticiones, len(ids)), np.nan) for name in [*names, choice]}
    above = {(name, cut): np.full((args.repeticiones, len(ids)), np.nan) for name in [*names, choice] for cut in ("youden", "normalidad")}
    chosen: dict[str, int] = {}

    def subject_z(z: pd.DataFrame, index: pd.Index) -> dict[str, pd.Series]:
        return {m: damage_score(z, (m,)).reindex(index) for m in measures}

    splitter = RepeatedStratifiedKFold(n_splits=N_SPLITS, n_repeats=args.repeticiones, random_state=2026)
    for k, (train_at, test_at) in enumerate(splitter.split(ids, case)):
        repeat = k // N_SPLITS
        train, test = pd.Index(ids[train_at]), pd.Index(ids[test_at])
        best = (-np.inf, None)
        fold = {}
        for reference_name, query in REFERENCES.items():
            reference = pd.Series(False, index=subjects.index)
            reference.loc[subjects.loc[train].query(query).index] = True
            train_features, test_features = features[features["subject_id"].isin(train)], features[features["subject_id"].isin(test)]
            # Entrenamiento: los de referencia, con el z de un modelo ajustado sin ellos; los demás, con el de todos.
            z_train = subject_z(region_z(train_features, subjects, reference, covariates, categorical), train)
            models = fit_region_models(train_features, subjects, reference, covariates, categorical)
            z_test = subject_z(apply_region_models(models, test_features, subjects, covariates, categorical), test)
            z_train_same = subject_z(apply_region_models(models, train_features, subjects, covariates, categorical), train)
            z_train_hard = subject_z(apply_region_models(models, hard[hard["subject_id"].isin(train)], hard_subjects, covariates, categorical), train)
            z_test_hard = subject_z(apply_region_models(models, hard[hard["subject_id"].isin(test)], hard_subjects, covariates, categorical), test)

            for panel_name, panel in panels().items():
                name = (panel_name, reference_name)
                mean = lambda z: pd.concat([z[m] for m in panel], axis=1).mean(axis=1)  # noqa: E731
                train_score, test_score = mean(z_train), mean(z_test)
                youden = damage_threshold(train_score, pd.Series(case[train_at], index=train))
                limit = normal_limit(train_score[reference.loc[train].to_numpy()])
                scores[name][repeat, test_at] = test_score.to_numpy()
                other[name][repeat, test_at] = mean(z_test_hard).to_numpy()
                # Sin puntuación no hay decisión: se queda en NaN y no cuenta ni como acierto ni como fallo.
                above[(name, "youden")][repeat, test_at] = (test_score >= youden).where(test_score.notna()).to_numpy(dtype=float)
                above[(name, "normalidad")][repeat, test_at] = (test_score >= limit).where(test_score.notna()).to_numpy(dtype=float)
                fold[name] = (test_score, mean(z_test_hard), youden, limit)
                if name in competing:
                    both = paired.loc[train].to_numpy()
                    agreement = icc_agreement(mean(z_train_same).to_numpy()[both], mean(z_train_hard).to_numpy()[both])
                    strength = abs(rho(train_score.to_numpy(), ratio[train_at]))
                    if agreement >= MIN_ICC and strength > best[0]:
                        best = (strength, name)
        winner = best[1] or (CURRENT, "todos los controles")
        chosen[" / ".join(winner)] = chosen.get(" / ".join(winner), 0) + 1
        test_score, test_hard, youden, limit = fold[winner]
        scores[choice][repeat, test_at] = test_score.to_numpy()
        other[choice][repeat, test_at] = test_hard.to_numpy()
        above[(choice, "youden")][repeat, test_at] = (test_score >= youden).where(test_score.notna()).to_numpy(dtype=float)
        above[(choice, "normalidad")][repeat, test_at] = (test_score >= limit).where(test_score.notna()).to_numpy(dtype=float)

    # Resumen: cada métrica, por repetición, con los sujetos de prueba de sus cinco vueltas juntos.
    baseline = (CURRENT, "todos los controles")
    rng = np.random.default_rng(0)
    draws = rng.integers(0, len(ids), (N_BOOTSTRAP, len(ids)))
    mean_score = {name: np.nanmean(values, axis=0) for name, values in scores.items()}
    both = paired.to_numpy()
    rows = []
    for name in [*names, choice]:
        per_repeat = [metrics(scores[name][r], ratio, case) for r in range(args.repeticiones)]
        row = {"medida": name[0], "referencia": name[1]}
        for key in ("rho", "rho_controles", "auc"):
            values = np.array([m[key] for m in per_repeat])
            row[key] = round(float(np.nanmean(values)), 3)
            row[f"{key}_dt"] = round(float(np.nanstd(values)), 3)
        # Con la puntuación media de cada sujeto entre repeticiones: la correlación, su intervalo y su p.
        for key, keep in (("rho", np.ones(len(ids), dtype=bool)), ("rho_controles", ~case)):
            a, y = mean_score[name][keep], ratio[keep]
            ok = np.isfinite(a) & np.isfinite(y)
            test = stats.spearmanr(a[ok], y[ok])
            resampled = [rho(a[d], y[d]) for d in rng.integers(0, keep.sum(), (N_BOOTSTRAP, keep.sum()))]
            row[f"{key}_media"] = round(float(test.statistic), 3)
            row[f"{key}_ic95"] = [round(float(v), 3) for v in np.nanpercentile(resampled, [2.5, 97.5])]
            row[f"{key}_p"] = permutation_p(a, y, rng)
        row["sin_puntuacion"] = int(np.isnan(scores[name]).sum())
        row["icc"] = round(float(np.mean([icc_agreement(scores[name][r][both], other[name][r][both]) for r in range(args.repeticiones)])), 3)
        for cut in ("youden", "normalidad"):
            flagged = above[(name, cut)]
            row[f"sensibilidad_{cut}"] = round(float(np.nanmean(flagged[:, case])), 3)
            row[f"especificidad_{cut}"] = round(float(1 - np.nanmean(flagged[:, ~case])), 3)
            # Cuántas veces cambia la decisión de un mismo sujeto entre repeticiones: 0 es un umbral estable.
            share = np.nanmean(flagged, axis=0)
            row[f"inestabilidad_{cut}"] = round(float(np.nanmean(2 * share * (1 - share))), 3)
        # ¿Mejora al modelo actual? Diferencia de |rho| con el mismo remuestreo de sujetos para los dos.
        if name != baseline:
            deltas, deltas_controls = [], []
            for draw in draws:
                a, b, y, c = mean_score[name][draw], mean_score[baseline][draw], ratio[draw], case[draw]
                deltas.append(abs(rho(a, y)) - abs(rho(b, y)))
                deltas_controls.append(abs(rho(a[~c], y[~c])) - abs(rho(b[~c], y[~c])))
            row["mejora_rho"] = round(abs(rho(mean_score[name], ratio)) - abs(rho(mean_score[baseline], ratio)), 3)
            row["mejora_rho_ic95"] = [round(float(v), 3) for v in np.nanpercentile(deltas, [2.5, 97.5])]
            row["mejora_rho_controles"] = round(abs(rho(mean_score[name][~case], ratio[~case])) - abs(rho(mean_score[baseline][~case], ratio[~case])), 3)
            row["mejora_rho_controles_ic95"] = [round(float(v), 3) for v in np.nanpercentile(deltas_controls, [2.5, 97.5])]
        rows.append(row)

    # ¿Sigue más al cociente una puntuación que otra? Diferencia de |rho| entre las dos, con su intervalo.
    contrasts = []
    for first, second in CONTRASTS:
        a, b = mean_score[(first, "todos los controles")], mean_score[(second, "todos los controles")]
        entry = {"primera": first, "segunda": second}
        for key, keep in (("todos", np.ones(len(ids), dtype=bool)), ("controles", ~case)):
            x, z, y = a[keep], b[keep], ratio[keep]
            deltas = [abs(rho(x[d], y[d])) - abs(rho(z[d], y[d])) for d in rng.integers(0, keep.sum(), (N_BOOTSTRAP, keep.sum()))]
            entry[key] = {"diferencia": round(abs(rho(x, y)) - abs(rho(z, y)), 3),
                          "ic95": [round(float(v), 3) for v in np.nanpercentile(deltas, [2.5, 97.5])]}
        contrasts.append(entry)

    out = {"sujetos": len(ids), "epoc": int(case.sum()), "controles": int((~case).sum()),
           "recuperados_de_la_otra_reconstruccion": int((~paired).sum()),
           "vueltas": N_SPLITS, "repeticiones": args.repeticiones, "acuerdo_minimo": MIN_ICC,
           "referencias": {name: int(len(subjects.query(query))) for name, query in REFERENCES.items()},
           "resultados": rows, "comparaciones": contrasts, "elegido_en_cada_vuelta": dict(sorted(chosen.items(), key=lambda item: -item[1]))}
    suffix = "_sin_recuperados" if args.sin_recuperados else ""
    (cohort / f"validacion_anidada{suffix}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    if not args.sin_recuperados:
        # La puntuación fuera de muestra de cada sujeto: son datos de sujetos, se quedan con la cohorte.
        table = {"subject_id": ids, "puntuacion_fuera_de_muestra": mean_score[baseline],
                 "veces_por_encima_youden": np.nanmean(above[(baseline, "youden")], axis=0),
                 "veces_por_encima_normalidad": np.nanmean(above[(baseline, "normalidad")], axis=0)}
        table |= {f"fuera_de_muestra:{panel}": mean_score[(panel, "todos los controles")] for panel in panels()}
        pd.DataFrame(table).to_csv(cohort / "fuera_de_muestra.csv", index=False)
    pd.set_option("display.width", 250, "display.max_columns", 30)
    table = pd.DataFrame(rows)
    print(json.dumps({k: v for k, v in out.items() if k != "resultados"}, indent=1, ensure_ascii=False))
    print(table[["medida", "referencia", "rho", "rho_controles", "auc", "icc", "sensibilidad_youden", "especificidad_youden",
                 "inestabilidad_youden", "sensibilidad_normalidad", "especificidad_normalidad", "inestabilidad_normalidad"]].to_string(index=False))
    print(table[["medida", "referencia", "rho_media", "rho_ic95", "rho_controles_media", "rho_controles_ic95", "rho_controles_p", "sin_puntuacion"]].to_string(index=False))
    print(json.dumps(contrasts, ensure_ascii=False))
    print(table[["medida", "referencia", "mejora_rho", "mejora_rho_ic95", "mejora_rho_controles", "mejora_rho_controles_ic95"]].dropna().to_string(index=False))


if __name__ == "__main__":
    main()
