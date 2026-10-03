"""¿Mejora algo añadir medidas, aprender pesos o juntar la TC con la clínica? Fuera de muestra.

Validación cruzada de 5 grupos, estratificada por caso y repetida. En cada vuelta,
solo con los sujetos de entrenamiento, se ajusta lo esperado, los pesos de los
modelos aprendidos y su regularización. Se comparan:

- puntuaciones de pesos iguales que van sumando medidas, de una a ocho;
- una regresión logística con todas las medidas de TC, que aprende sus pesos;
- la clínica sola (edad, sexo, talla, IMC, paquetes-año, fumar ahora);
- la clínica junto a la TC.

Para cada una: AUC para la obstrucción (FEV1/FVC < 0,70), correlación con el
FEV1/FVC y, en las de TC, acuerdo entre las dos reconstrucciones. Además mira si
la puntuación fuera de muestra anuncia la caída acelerada del FEV1 (más de 60 mL
al año), que es uno de los criterios de EPOC precoz de las investigadoras.
Escribe `complejidad.json` en el directorio de la cohorte, con agregados.

    python scripts/complexity_cv.py mn5/cohorte.final.toml --duro outputs/cohorte_duro_v4
"""

from __future__ import annotations

import argparse
import json
import tomllib
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegressionCV
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from evaluate import auc, icc_agreement
from maps.cohort import KEYS, apply_region_models, damage_score, fit_region_models, lung_volume, region_z
from maps.measures import MEASURES

warnings.filterwarnings("ignore")
# Cada escalón añade una medida a la puntuación de pesos iguales: primero la vía aérea, luego el enfisema
# (el modelo), y después las tradicionales que nombra el reto y las demás.
LADDER = ["via_longitud_mm", "laa950_smooth", "via_disanapsia", "via_grosor_pared_mm", "vasos_por_litro", "agrupamiento",
          "via_pi10_mm", "perc15"]
CLINICAL = ["edat_round_v1", "altura_v1", "imc_v1", "paquetes_año_v1"]
# El resto de la tabla que no es espirometría: síntomas, difusión, FENO y asma. El FEV1 y la FVC no
# entran como variables: la obstrucción es su cociente, y meterlos sería darle la respuesta.
EXTENDED = ["DLCO_v1", "CAT_v1", "mmrc_num_v1", "COPD_PS_v1", "FENO_v1", "asma_num_v1"]
N_SPLITS, N_REPEATS = 5, 5
DECLINE_ML_YEAR = (30, 60)  # 30 mL al año, según la investigadora del reto; 60, el de la definición publicada


def rho(a: np.ndarray, b: np.ndarray) -> float:
    ok = np.isfinite(a) & np.isfinite(b)
    return float(stats.spearmanr(a[ok], b[ok]).statistic) if ok.sum() >= 8 else float("nan")


def learner() -> object:
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegressionCV(Cs=10, cv=StratifiedKFold(5, shuffle=True, random_state=0), max_iter=5000))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--duro", type=Path, required=True)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])
    normative = config["normativo"]
    covariates, categorical = normative["covariables"], normative.get("categoricas", [])
    subjects = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    all_features = pd.read_csv(cohort / "features.csv", dtype={"subject_id": str})
    measures = [m for m in MEASURES if m in all_features and all_features[m].notna().any()]
    features = all_features[[*KEYS, *measures]]
    hard = pd.read_csv(args.duro / "features.csv", dtype={"subject_id": str})
    hard = hard[hard["subject_id"].isin(subjects.index)]
    hard_subjects = subjects.drop(columns="volumen_pulmon_ml").join(lung_volume(hard), how="inner")
    hard = hard[[*KEYS, *measures]]
    paired = ~subjects["de_repuesto"].astype(bool).to_numpy()

    ids = subjects.index.to_numpy()
    case = (subjects["caso_v1"] == 1).to_numpy()
    ratio = subjects["fev1_fvc_post_v1"].to_numpy(dtype=float)
    clinical = subjects[CLINICAL].astype(float).assign(mujer=(subjects["sexo"] == "mujer").astype(float),
                                                       fuma=(subjects["fuma"] == "fuma").astype(float))
    extended = clinical.join(subjects[EXTENDED].astype(float))
    names = [f"{k} medida{'s' if k > 1 else ''}" for k in range(1, len(LADDER) + 1)] + \
            ["logística con todas las medidas de TC", "clínica sola", "clínica y las dos medidas de TC",
             "clínica ampliada sola", "clínica ampliada y las dos medidas de TC"]
    scores = {name: np.full((N_REPEATS, len(ids)), np.nan) for name in names}
    other = {name: np.full((N_REPEATS, len(ids)), np.nan) for name in names}

    def oriented(z: pd.DataFrame, index: pd.Index) -> pd.DataFrame:
        return pd.DataFrame({m: damage_score(z, (m,)).reindex(index) for m in measures})

    splitter = RepeatedStratifiedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=2026)
    for k, (train_at, test_at) in enumerate(splitter.split(ids, case)):
        repeat = k // N_SPLITS
        train, test = pd.Index(ids[train_at]), pd.Index(ids[test_at])
        reference = pd.Series(False, index=subjects.index)
        reference.loc[train[(subjects.loc[train, "caso_v1"] == 0).to_numpy()]] = True
        train_features, test_features = features[features["subject_id"].isin(train)], features[features["subject_id"].isin(test)]
        z_train = oriented(region_z(train_features, subjects, reference, covariates, categorical), train)
        models = fit_region_models(train_features, subjects, reference, covariates, categorical)
        z_test = oriented(apply_region_models(models, test_features, subjects, covariates, categorical), test)
        z_hard = oriented(apply_region_models(models, hard[hard["subject_id"].isin(test)], hard_subjects, covariates, categorical), test)

        for step in range(1, len(LADDER) + 1):
            panel = LADDER[:step]
            scores[names[step - 1]][repeat, test_at] = z_test[panel].mean(axis=1).to_numpy()
            other[names[step - 1]][repeat, test_at] = z_hard[panel].mean(axis=1).to_numpy()
        # Modelos que aprenden sus pesos con el entrenamiento: se puntúa con el logit, para comparar rangos.
        y_train = case[train_at].astype(int)
        for name, columns_train, columns_test, columns_hard in (
            ("logística con todas las medidas de TC", z_train, z_test, z_hard),
            ("clínica sola", clinical.loc[train], clinical.loc[test], None),
            ("clínica y las dos medidas de TC", clinical.loc[train].join(z_train[LADDER[:2]]),
             clinical.loc[test].join(z_test[LADDER[:2]]), clinical.loc[test].join(z_hard[LADDER[:2]])),
            ("clínica ampliada sola", extended.loc[train], extended.loc[test], None),
            ("clínica ampliada y las dos medidas de TC", extended.loc[train].join(z_train[LADDER[:2]]),
             extended.loc[test].join(z_test[LADDER[:2]]), extended.loc[test].join(z_hard[LADDER[:2]])),
        ):
            fitted = learner().fit(columns_train.to_numpy(dtype=float), y_train)
            scores[name][repeat, test_at] = fitted.decision_function(columns_test.to_numpy(dtype=float))
            if columns_hard is not None:
                other[name][repeat, test_at] = fitted.decision_function(columns_hard.to_numpy(dtype=float))

    rows = []
    for name in names:
        per_repeat = [(auc(case.astype(float), scores[name][r]), rho(scores[name][r], ratio), rho(scores[name][r][~case], ratio[~case]))
                      for r in range(N_REPEATS)]
        values = np.array(per_repeat)
        icc = [icc_agreement(scores[name][r][paired], other[name][r][paired]) for r in range(N_REPEATS)] \
            if np.isfinite(other[name]).any() else [np.nan]
        # EPOC que se escapan si cada modelo deja por debajo al 75 % de los controles: el mismo punto de la ROC para todos.
        missed = []
        for r in range(N_REPEATS):
            s = scores[name][r]
            ok = np.isfinite(s)
            cut = np.quantile(s[ok & ~case], 0.75)
            missed.append(int(np.sum(ok & case & (s < cut))))
        rows.append({"modelo": name, "epoc_escapan_esp75": round(float(np.mean(missed)), 1),
                     "auc": round(float(np.nanmean(values[:, 0])), 3), "auc_dt": round(float(np.nanstd(values[:, 0])), 3),
                     "rho_fev1_fvc": round(float(np.nanmean(values[:, 1])), 3), "rho_sin_obstruccion": round(float(np.nanmean(values[:, 2])), 3),
                     "icc": round(float(np.nanmean(icc)), 3) if np.isfinite(icc).any() else None,
                     "medidas": LADDER[:names.index(name) + 1] if names.index(name) < len(LADDER) else None})

    # ¿Anuncia la puntuación fuera de muestra la caída acelerada del FEV1 (criterio de EPOC precoz)?
    unseen = pd.read_csv(cohort / "fuera_de_muestra.csv", dtype={"subject_id": str}).set_index("subject_id")["puntuacion_fuera_de_muestra"]
    decline = subjects["caida_fev1_ml_ano"]
    follow = {}
    for limit in DECLINE_ML_YEAR:
        for group, keep in (("todos", subjects.index), ("sin obstrucción", subjects.index[~case])):
            x, y = unseen.reindex(keep), decline.reindex(keep)
            ok = x.notna() & y.notna()
            fast = y[ok] > limit
            follow[f"{limit} mL al año, {group}"] = {
                "con_seguimiento": int(ok.sum()), "caida_acelerada": int(fast.sum()),
                "auc": round(auc(fast.to_numpy(dtype=float), x[ok].to_numpy(dtype=float)), 3) if 0 < fast.sum() < ok.sum() else None,
                "p_mann_whitney": float(stats.mannwhitneyu(x[ok][fast], x[ok][~fast]).pvalue) if 0 < fast.sum() < ok.sum() else None,
                "rho_con_la_caida": round(rho(x[ok].to_numpy(), y[ok].to_numpy()), 3)}
    out = {"sujetos": len(ids), "repeticiones": N_REPEATS, "modelos": rows, "caida_acelerada_del_fev1": follow}
    (cohort / "complejidad.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    pd.set_option("display.width", 200)
    print(pd.DataFrame(rows).drop(columns="medidas").to_string(index=False))
    print(json.dumps(follow, ensure_ascii=False))


if __name__ == "__main__":
    main()
