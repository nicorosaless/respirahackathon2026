"""La prueba en los sujetos de reserva: el modelo congelado frente a sujetos que no ha visto.

Nada se ajusta con ellos. El script carga el modelo guardado (`modelo.pkl` y
`modelo.json`: lo esperado según los controles de desarrollo y el umbral de
daño), lo aplica a las medidas de la reserva y cuenta cuánto acierta. Escribe
`reserva.json`, con agregados, y deja constancia del uso en `reserva_usos.log`:
la reserva se mira una vez. Lo que se mide y lo que sería un fracaso está
escrito antes en `docs/protocolo-reserva.md`.

    python scripts/holdout.py mn5/cohorte.early.toml --duro outputs/cohorte_duro_v3
    python scripts/holdout.py mn5/cohorte.early.toml --duro outputs/cohorte_duro_v3 --ensayo   # con desarrollo, sin gastar la reserva
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from check_score import MAD_TO_SD, association, auc_with_interval
from evaluate import icc_agreement
from maps.classify import CLASSES
from maps.cohort import apply_region_models, damage_score, lung_volume
from maps.persist import DESCRIPTION_FILE, MODELS_FILE, load_model
from maps.validation import _model
from score_cohort import build_blocks

SCORE = "puntuacion_dano"
# Lo que se fijó por escrito antes de mirar la reserva (docs/protocolo-reserva.md).
CRITERIA = {"auc_minimo": 0.80, "auc_fracaso": 0.75, "rho_maximo": -0.5, "mediana_controles": 0.5,
            "dispersion_controles": (0.6, 1.6), "icc_minimo": 0.9}


def fraction(hits: pd.Series) -> dict:
    """Aciertos sobre el total, con el intervalo exacto del 95 % (Clopper-Pearson)."""
    if len(hits) == 0:
        return {"aciertos": 0, "de": 0, "valor": None}
    interval = stats.binomtest(int(hits.sum()), len(hits)).proportion_ci(method="exact")
    return {"aciertos": int(hits.sum()), "de": len(hits), "valor": round(float(hits.mean()), 3),
            "ic95": [round(float(interval.low), 3), round(float(interval.high), 3)]}


def spread(values: pd.Series) -> dict:
    centre = float(values.median())
    return {"mediana": round(centre, 3), "dispersion": round(MAD_TO_SD * float((values - centre).abs().median()), 3)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--duro", type=Path, help="cohorte de los mismos sujetos con otro kernel de reconstrucción")
    parser.add_argument("--ensayo", action="store_true", help="prueba el script con los sujetos de desarrollo; no gasta la reserva")
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])
    rule = config["clasificacion"]
    models, model = load_model(cohort)
    panel, threshold = tuple(model["medidas"]), model["umbral_dano"]
    covariates, categorical = model["covariables"], model["categoricas"]

    subjects = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    features = pd.read_csv(cohort / "features.csv", dtype={"subject_id": str})
    split = "desarrollo" if args.ensayo else "reserva"
    t = subjects[subjects["particion"] == split]
    if not args.ensayo and t["referencia"].astype(bool).any():
        raise SystemExit("hay sujetos de reserva en la referencia del modelo normativo: la prueba no sería limpia")

    # El modelo guardado, aplicado a las medidas de estos sujetos. Tiene que dar lo mismo que hay en
    # subjects.csv: si no, lo que se enseña en la app no es lo que se está probando.
    zscores = apply_region_models(models, features[features["subject_id"].isin(t.index)], subjects, covariates, categorical)
    score = damage_score(zscores, panel).reindex(t.index)
    outside = ~t["referencia"].astype(bool)  # los de referencia llevan en subjects.csv su z cruzado, que es otro
    gap = float((score[outside] - t.loc[outside, SCORE]).abs().max())
    if gap > 1e-6:
        raise SystemExit(f"el modelo guardado no reproduce las puntuaciones de subjects.csv (diferencia de {gap:.3g}): "
                         "vuelve a ejecutar scripts/score_cohort.py")
    if args.ensayo:
        score = t[SCORE]  # en el ensayo, los controles de desarrollo con su z cruzado

    scored = score.notna()
    case = (t[rule["caso"]] == 1)[scored]
    score, t_scored = score[scored], t[scored]
    damaged = score >= threshold
    out = {
        "cuando": time.strftime("%Y-%m-%d %H:%M"), "particion": split, "sujetos": len(t), "sin_puntuacion": int((~scored).sum()),
        "epoc": int(case.sum()), "medidas": list(panel), "umbral_dano": threshold,
        "modelo": {name: hashlib.sha256((cohort / name).read_bytes()).hexdigest()[:16] for name in (MODELS_FILE, DESCRIPTION_FILE)},
        # Lo que la TC sola dice de la obstrucción, en sujetos que el modelo no vio.
        "separa_epoc": auc_with_interval(case.astype(int), score),
        "fev1_fvc": association(score, t_scored[rule["cociente"]]),
        "sensibilidad": fraction(damaged[case]),
        "especificidad": fraction(~damaged[~case]),
        "clases": {name: int((t["clase_maps"] == name).sum()) for name in CLASSES},
    }

    # ¿Vale "lo esperado" para sujetos nuevos? Los controles de reserva no entraron en la referencia:
    # si el modelo normativo viaja, su z se centra en cero con dispersión cercana a uno.
    controls = score.index[~case]
    out["calibracion_controles"] = {"n": len(controls), "puntuacion": spread(score[controls])}
    if not args.ensayo:
        for measure in panel:
            out["calibracion_controles"][measure] = spread(damage_score(zscores, (measure,)).reindex(controls).dropna())

    # El segundo umbral, que no usa la etiqueta de EPOC: el límite superior de normalidad de la referencia.
    checks = json.loads((cohort / "comprobaciones.json").read_text())
    normal_limit = checks["limite_de_normalidad"]["umbral"]
    out["limite_de_normalidad"] = {"umbral": normal_limit, "sensibilidad": fraction((score >= normal_limit)[case]),
                                   "especificidad": fraction((score < normal_limit)[~case])}

    # ¿Añade la TC a lo que ya se sabe sin ninguna prueba? Dos modelos ajustados solo con desarrollo,
    # uno con la clínica y otro con la clínica y la TC, y su predicción del FEV1/FVC en estos sujetos.
    evidence = config.get("evidencia")
    if evidence and not args.ensayo:
        all_z = pd.read_csv(cohort / "zscores.csv", dtype={"subject_id": str})
        blocks = build_blocks(evidence["bloques"], subjects, all_z)
        train = subjects.index[subjects["particion"] == "desarrollo"]
        target = subjects[evidence["objetivo"]]
        columns, ladder = [], []
        for name, block in blocks.items():
            columns.append(block)
            x = pd.concat(columns, axis=1)
            fitted = _model(evidence["tarea"], 5, 0).fit(x.loc[train].to_numpy(dtype=float), target[train].to_numpy(dtype=float))
            prediction = pd.Series(fitted.predict(x.loc[t_scored.index].to_numpy(dtype=float)), index=t_scored.index)
            ladder.append({"hasta": name} | association(prediction, target[t_scored.index]))
        out["anade_a_la_clinica"] = ladder

    if args.duro is not None:
        # La otra reconstrucción de las mismas TC, con el mismo modelo guardado.
        hard = pd.read_csv(args.duro / "features.csv", dtype={"subject_id": str})
        hard = hard[hard["subject_id"].isin(t_scored.index)]
        hard_subjects = subjects.drop(columns="volumen_pulmon_ml").join(lung_volume(hard), how="inner")
        base = damage_score(apply_region_models(models, features[features["subject_id"].isin(t_scored.index)], subjects,
                                                covariates, categorical), panel).reindex(t_scored.index)
        other = damage_score(apply_region_models(models, hard, hard_subjects, covariates, categorical), panel).reindex(t_scored.index)
        both = base.notna() & other.notna()
        out["otra_reconstruccion"] = {
            "sujetos": int(both.sum()),
            "icc": round(icc_agreement(base[both].to_numpy(dtype=float), other[both].to_numpy(dtype=float)), 3),
            "separa_epoc": auc_with_interval(case[both].astype(int), other[both]),
            "misma_decision_de_dano": fraction((other[both] >= threshold) == (base[both] >= threshold)),
        }

    low, high = CRITERIA["dispersion_controles"]
    out["criterios"] = {
        "separa_epoc": out["separa_epoc"]["auc"] >= CRITERIA["auc_minimo"],
        "sigue_el_cociente": out["fev1_fvc"].get("rho", 0.0) <= CRITERIA["rho_maximo"],
        "controles_centrados": abs(out["calibracion_controles"]["puntuacion"]["mediana"]) <= CRITERIA["mediana_controles"],
        "controles_con_dispersion_normal": all(low <= out["calibracion_controles"][m]["dispersion"] <= high
                                               for m in panel if m in out["calibracion_controles"]),
        "fracaso": out["separa_epoc"]["auc"] < CRITERIA["auc_fracaso"]
        or abs(out["calibracion_controles"]["puntuacion"]["mediana"]) > CRITERIA["mediana_controles"],
    }
    if "otra_reconstruccion" in out:
        out["criterios"]["estable_entre_reconstrucciones"] = out["otra_reconstruccion"]["icc"] >= CRITERIA["icc_minimo"]

    print(json.dumps(out, indent=1, ensure_ascii=False))
    if args.ensayo:
        return
    (cohort / "reserva.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    with (cohort.parent / "reserva_usos.log").open("a") as log:
        log.write(f"{out['cuando']} scripts/holdout.py, modelo {out['modelo'][MODELS_FILE]}, medidas {list(panel)}, umbral {threshold:.3f}\n")


if __name__ == "__main__":
    main()
