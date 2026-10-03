"""Pone a prueba la puntuación de daño: qué sigue, qué no, y si algún artefacto la explica.

Todo con los sujetos de desarrollo. Escribe `comprobaciones.json` en el directorio
de la cohorte, solo con agregados: recuentos, correlaciones, AUC y cuantiles de
grupos de 5 sujetos o más. De ahí salen la figura de evidencia y las tablas de
`docs/resultados.md`.

    python scripts/check_score.py mn5/cohorte.early.toml --duro outputs/cohorte_duro_v2
"""

from __future__ import annotations

import argparse
import ast
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import cohen_kappa_score

from evaluate import auc, components, headline, icc_agreement
from maps.classify import CLASSES, damage_threshold
from maps.cohort import damage_score, lung_volume, region_z, region_z_applied
from maps.measures import MEASURES, WHOLE_LUNG

MIN_CELL = 5
N_BOOTSTRAP = 2000
SCORE = "puntuacion_dano"
OUTCOMES = {"fev1_fvc_post_v1": "FEV1/FVC", "FEV1pp_GLI_v1": "FEV1, % del predicho", "DLCO_v1": "DLCO, % del predicho",
            "CAT_v1": "CAT", "paquetes_año_v1": "Paquetes-año"}
FOLLOW_UP = {"cambio_cociente": "Cambio del FEV1/FVC", "caida_fev1_ml_ano": "Caída del FEV1, mL/año",
             "cambio_fev1pp": "Cambio del FEV1 %", "CAT_v2": "CAT en la visita 2"}
STRATA = ["kvp", "sexo", "fuma"]
# Lo que se probó añadir a la puntuación, de una en una, y todo junto.
SEEDS = range(10)  # repartos del ajuste cruzado con los que se comprueba que el umbral no depende de uno solo
LOG_CONSTANTS = (0.001, 0.01, 0.1)  # la constante que se suma al porcentaje de enfisema antes del logaritmo
CLASS_TABLE = {"fev1_fvc_post_v1": "FEV1/FVC", "FEV1pp_GLI_v1": "FEV1, % del predicho", "DLCO_v1": "DLCO, % del predicho",
               "CAT_v1": "CAT en la visita 1", "CAT_v2": "CAT en la visita 2", "paquetes_año_v1": "Paquetes-año"}
NEAR_OBSTRUCTION = 0.75  # aproximación al límite inferior de normalidad del FEV1/FVC entre 35 y 50 años
MAD_TO_SD = 1.4826
EXTRAS = ["via_disanapsia", "via_grosor_pared_mm", "via_pi10_mm", "vasos_por_litro", "agrupamiento", "via_ramas_por_litro"]


def association(x: pd.Series, y: pd.Series) -> dict:
    ok = x.notna() & y.notna()
    if ok.sum() < 8:
        return {"n": int(ok.sum())}
    result = stats.spearmanr(x[ok], y[ok])
    return {"rho": round(float(result.statistic), 3), "p": float(result.pvalue), "n": int(ok.sum())}


def auc_with_interval(case: pd.Series, score: pd.Series) -> dict:
    labels, values = case.to_numpy(dtype=float), score.to_numpy(dtype=float)
    rng = np.random.default_rng(0)
    draws = [auc(labels[i], values[i]) for i in (rng.integers(0, len(labels), len(labels)) for _ in range(N_BOOTSTRAP))]
    low, high = np.nanpercentile(draws, [2.5, 97.5])
    return {"auc": round(auc(labels, values), 3), "ic95": [round(float(low), 3), round(float(high), 3)],
            "n": len(labels), "casos": int(labels.sum())}


def quantiles(values: pd.Series) -> dict:
    values = values.dropna()
    if len(values) < MIN_CELL:
        return {"n": f"<{MIN_CELL}"}
    q = np.percentile(values, [10, 25, 50, 75, 90])
    return {"n": len(values)} | {f"p{p}": round(float(v), 3) for p, v in zip((10, 25, 50, 75, 90), q)}


def compare(table: pd.DataFrame, group: pd.Series, columns: dict[str, str]) -> list[dict]:
    """Mediana de cada variable en los dos grupos de `group` (True y False) y su Mann-Whitney."""
    rows = []
    for column, label in columns.items():
        a, b = table.loc[group, column].dropna(), table.loc[~group, column].dropna()
        if min(len(a), len(b)) < MIN_CELL:
            continue
        rows.append({"variable": label, "con_dano": round(float(a.median()), 3), "n_con": len(a),
                     "sin_dano": round(float(b.median()), 3), "n_sin": len(b),
                     "p": float(stats.mannwhitneyu(a, b).pvalue)})
    return rows


def benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    order = np.argsort(p)
    ranked = p[order] * len(p) / np.arange(1, len(p) + 1)
    q = np.empty_like(p)
    q[order] = np.minimum.accumulate(ranked[::-1])[::-1]
    return np.clip(q, 0, 1)


def subject_z(zscores: pd.DataFrame, measure: str) -> pd.Series:
    """Un z por sujeto: la media de los lóbulos, o el del pulmón entero si la medida solo existe ahí."""
    whole = zscores["region"] == WHOLE_LUNG
    lobar = zscores[~whole].groupby("subject_id")[measure].mean()
    return lobar if lobar.notna().any() else zscores[whole].set_index("subject_id")[measure]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--duro", type=Path, help="cohorte de los mismos sujetos con otro kernel de reconstrucción")
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])
    normative = config["normativo"]
    covariates, categorical = normative["covariables"], normative.get("categoricas", [])
    panel = tuple(config["puntuacion"]["medidas"])

    subjects = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    zscores = pd.read_csv(cohort / "zscores.csv", dtype={"subject_id": str})
    features = pd.read_csv(cohort / "features.csv", dtype={"subject_id": str})
    subjects["cambio_cociente"] = subjects["fev1_fvc_post_v2"] - subjects["fev1_fvc_post_v1"]
    # Con qué sujetos se hacen las comprobaciones: los de desarrollo, salvo que la configuración diga otra cosa.
    dev = subjects.query(config.get("analisis", {}).get("filtro", "particion == 'desarrollo'"))
    case = dev["caso_v1"] == 1
    controls, cases = dev[~case], dev[case]
    out: dict = {"sujetos": len(dev), "controles": len(controls), "epoc": len(cases), "medidas": list(panel),
                 "umbral_dano": json.loads((cohort / "modelo.json").read_text())["umbral_dano"]}

    # 1. Qué sigue la puntuación: en todos, y dentro de cada grupo para que no sea solo la diferencia entre grupos.
    out["asociaciones"] = [
        {"variable": label, "todos": association(dev[SCORE], dev[column]),
         "controles": association(controls[SCORE], controls[column]), "epoc": association(cases[SCORE], cases[column])}
        for column, label in OUTCOMES.items()]

    # 2. Separa EPOC de control, y lo hace igual dentro de cada kVp, sexo y hábito de tabaco.
    out["separa_epoc"] = auc_with_interval(dev["caso_v1"], dev[SCORE])
    out["por_estrato"] = [
        {"variable": column, "nivel": str(level)} | auc_with_interval(part["caso_v1"], part[SCORE])
        for column in STRATA for level, part in dev.groupby(column)
        if min((part["caso_v1"] == 1).sum(), (part["caso_v1"] == 0).sum()) >= MIN_CELL]
    out["cada_medida_sola"] = [
        {"medida": measure} | auc_with_interval(dev["caso_v1"], damage_score(zscores, (measure,)).reindex(dev.index))
        for measure in panel]

    # 3. Controles negativos: dentro de los controles, la puntuación no debe distinguir sexo, tabaco, kVp ni corpulencia.
    out["controles_negativos"] = {
        "sexo_auc": round(auc((controls["sexo"] == "mujer").to_numpy(dtype=float), controls[SCORE].to_numpy(dtype=float)), 3),
        "fuma_auc": round(auc((controls["fuma"] == "fuma").to_numpy(dtype=float), controls[SCORE].to_numpy(dtype=float)), 3),
        "kvp_kruskal_p": float(stats.kruskal(*[part[SCORE] for _, part in controls.groupby("kvp")]).pvalue),
        "imc": association(controls[SCORE], controls["imc_v1"]),
        "imc_todos": association(dev[SCORE], dev["imc_v1"]),
    }

    # 4. La otra reconstrucción de la misma adquisición, con el mismo modelo y sin reajustar nada.
    hard = None
    if args.duro is not None:
        hard = pd.read_csv(args.duro / "features.csv", dtype={"subject_id": str})
        hard = hard[hard["subject_id"].isin(subjects.index)]
        reference = subjects["referencia"].astype(bool)
        hard_subjects = subjects.drop(columns="volumen_pulmon_ml").join(lung_volume(hard), how="inner")
        base_z = region_z_applied(features, features, subjects, subjects, reference, covariates, categorical)
        hard_z = region_z_applied(features, hard, subjects, hard_subjects, reference, covariates, categorical)
        base, other = damage_score(base_z, panel).reindex(dev.index), damage_score(hard_z, panel).reindex(dev.index)
        # Un sujeto recuperado de la otra reconstrucción no tiene dos medidas distintas que comparar.
        spare = dev.index[dev.get("de_repuesto", pd.Series(False, index=dev.index)).astype(bool)]
        other.loc[spare] = np.nan
        hard = hard[~hard["subject_id"].isin(spare)]
        out["recuperados_de_la_otra_reconstruccion"] = len(spare)
        out["otra_reconstruccion"] = {
            "icc": round(icc_agreement(base.to_numpy(dtype=float), other.to_numpy(dtype=float)), 3),
            "separa_epoc": auc_with_interval(dev.loc[other.notna(), "caso_v1"], other.dropna()),
            "fev1_fvc": association(other, dev["fev1_fvc_post_v1"]),
        }

        # 4b. ¿Y con otras medidas? Cada una sola, las de la puntuación, y lo que cambia al añadir cada candidata.
        alternatives = {measure: (measure,) for measure in panel} | {"la puntuación": panel}
        alternatives |= {f"+ {extra}": (*panel, extra) for extra in EXTRAS} | {"todas": (*panel, *EXTRAS)}
        out["paneles"] = []
        for name, measures in alternatives.items():
            trial = dev.assign(puntuacion_dano=damage_score(zscores, measures).reindex(dev.index),
                               puntuacion_base=damage_score(base_z, measures).reindex(dev.index),
                               puntuacion_duro=damage_score(hard_z, measures).reindex(dev.index).where(~dev.index.isin(spare)))
            parts = components(trial)
            out["paneles"].append({"panel": name, "auc_epoc": round((parts["separa_epoc"] + 1) / 2, 3),
                                   "rho_fev1_fvc": round(-parts["flujo_aereo"], 3), "icc_kernel": round(parts["robustez_kernel"], 3),
                                   "marcador": round(headline(parts), 3)})

        # El umbral se decide entre los controles: el acuerdo que importa es el de ellos, no el que inflan los casos.
        is_control = (dev["caso_v1"] == 0).to_numpy()
        out["otra_reconstruccion"]["icc_controles"] = round(
            icc_agreement(base.to_numpy(dtype=float)[is_control], other.to_numpy(dtype=float)[is_control]), 3)
        # Cuánto se mueve la puntuación de un sujeto al cambiar de reconstrucción: dentro de esa distancia
        # del umbral, la clase podría cambiar sin que cambie el pulmón.
        # La anchura de la zona gris es una desviación típica robusta de esa diferencia.
        gap = (base - other).dropna()
        out["zona_gris"] = round(MAD_TO_SD * float((gap - gap.median()).abs().median()), 3)
        out["otra_reconstruccion"]["diferencia_p95"] = round(float(np.percentile(gap.abs(), 95)), 3)

    # 4c. Por qué el ajuste cruzado deja fuera a un sujeto cada vez: con cinco grupos al azar, el umbral
    # y los controles marcados dependían del reparto. Aquí se mide cuánto.
    cohort_features = features[features["subject_id"].isin(subjects.index)]
    reference = subjects["referencia"].astype(bool)
    flagged_first, runs = set(dev.index[(dev[SCORE] >= out["umbral_dano"]) & ~case]), []
    for seed in SEEDS:
        score = damage_score(region_z(cohort_features, subjects, reference, covariates, categorical, n_splits=5, seed=seed), panel).reindex(dev.index)
        cut = damage_threshold(score, case)
        flagged = set(score.index[(score >= cut) & ~case])
        runs.append({"umbral": cut, "marcados": len(flagged), "auc": auc(dev["caso_v1"].to_numpy(dtype=float), score.to_numpy(dtype=float)),
                     "comunes": len(flagged & flagged_first)})
    out["estabilidad_del_umbral"] = {
        "repartos_en_cinco_grupos": len(runs), "umbral": [round(min(r["umbral"] for r in runs), 3), round(max(r["umbral"] for r in runs), 3)],
        "controles_marcados": [min(r["marcados"] for r in runs), max(r["marcados"] for r in runs)],
        "auc": [round(min(r["auc"] for r in runs), 3), round(max(r["auc"] for r in runs), 3)],
        "marcados_por_el_modelo": len(flagged_first),
        "de_ellos_marcados_en_todos": min(r["comunes"] for r in runs),
    }

    # 4d. Un umbral que no usa la etiqueta de EPOC: el límite superior de normalidad de la referencia,
    # como el límite inferior de normalidad de la espirometría (percentil 95, 1,645 desviaciones robustas).
    reference_score = dev.loc[dev["referencia"].astype(bool), SCORE]
    centre = float(reference_score.median())
    normal_limit = centre + 1.645 * MAD_TO_SD * float((reference_score - centre).abs().median())
    above = dev[SCORE] >= normal_limit
    out["limite_de_normalidad"] = {"umbral": round(normal_limit, 3), "controles_por_encima": int((above & ~case).sum()),
                                   "sensibilidad": round(float(above[case].mean()), 3),
                                   "especificidad": round(float((~above[~case]).mean()), 3)}

    # 5. Medida a medida: lo que pide el reto y lo que entra en la puntuación.
    rows = []
    for measure in [c for c in zscores.columns if c not in ("subject_id", "region")]:
        z = subject_z(zscores, measure).reindex(dev.index)
        if z.notna().sum() < 8:
            continue
        if measure not in MEASURES:
            continue
        name, _, _, worse = MEASURES[measure]
        sign = 1.0 if worse == "mayor" else -1.0  # orientado para que positivo sea peor
        row = {"medida": measure, "nombre": name, "en_la_puntuacion": measure in panel,
               "auc_epoc": round(auc(dev["caso_v1"].to_numpy(dtype=float), (sign * z).to_numpy(dtype=float)), 3)}
        for column in OUTCOMES:
            row[column] = association(sign * z, dev[column])
        row["fuma"] = round(auc((dev["fuma"] == "fuma").to_numpy(dtype=float), (sign * z).to_numpy(dtype=float)), 3)
        if hard is not None:
            a = features[features["region"] == WHOLE_LUNG].set_index("subject_id")[measure].reindex(dev.index)
            b = hard[hard["region"] == WHOLE_LUNG].set_index("subject_id")[measure].reindex(dev.index)
            row["icc_kernel"] = round(icc_agreement(a.to_numpy(dtype=float), b.to_numpy(dtype=float)), 3)
        rows.append(row)
    p = np.array([row[column].get("p", np.nan) for row in rows for column in OUTCOMES])
    q = np.full_like(p, np.nan)
    q[np.isfinite(p)] = benjamini_hochberg(p[np.isfinite(p)])
    for (row, column), value in zip(((row, column) for row in rows for column in OUTCOMES), q):
        if np.isfinite(value):
            row[column]["q"] = float(value)
    out["por_medida"] = rows

    # 6. Los controles que la TC marca: ¿se parecen más a la EPOC en algo que no sea la TC?
    high = controls["dano_tc"] == "sí"
    out["controles_por_dano"] = {"con_dano": int(high.sum()), "sin_dano": int((~high).sum()),
                                 "visita_1": compare(controls, high, OUTCOMES), "seguimiento": compare(controls, high, FOLLOW_UP)}
    out["controles_por_dano"]["cerca_de_la_obstruccion"] = {
        "criterio": f"FEV1/FVC < {NEAR_OBSTRUCTION}",
        "con_dano": int((controls.loc[high, "fev1_fvc_post_v1"] < NEAR_OBSTRUCTION).sum()),
        "sin_dano": int((controls.loc[~high, "fev1_fvc_post_v1"] < NEAR_OBSTRUCTION).sum())}
    out["seguimiento_controles"] = [{"variable": label} | association(controls[SCORE], controls[column])
                                    for column, label in FOLLOW_UP.items()]

    # 6b. ¿Lo explica la calidad de la imagen? Más ruido o píxeles más grandes podrían acortar el árbol que se segmenta.
    whole = features[features["region"] == WHOLE_LUNG].set_index("subject_id")
    quality = pd.DataFrame({
        "ruido_hu": whole["ruido_hu"].reindex(dev.index) if "ruido_hu" in whole else np.nan,
        "pixel_mm": dev["espaciado_mm"].map(lambda text: ast.literal_eval(text)[1]),
        "paso_de_corte_mm": dev["espaciado_mm"].map(lambda text: ast.literal_eval(text)[0]),
    })
    airway_z = damage_score(zscores, ("via_longitud_mm",)).reindex(dev.index)
    out["calidad_de_imagen"] = [
        {"variable": name, "puntuacion": association(dev[SCORE], quality[name]),
         "puntuacion_en_controles": association(controls[SCORE], quality.loc[controls.index, name]),
         "via_aerea": association(airway_z, quality[name]),
         "mediana_controles": round(float(quality.loc[controls.index, name].median()), 3),
         "mediana_epoc": round(float(quality.loc[cases.index, name].median()), 3)}
        for name in quality if quality[name].notna().sum() >= 8]

    # El píxel es mayor en los sujetos más corpulentos, y hay más de ellos entre los casos. ¿Sigue la
    # puntuación al FEV1/FVC cuando se descuenta el tamaño del píxel o el índice de masa corporal?
    def partial(a: pd.Series, b: pd.Series, c: pd.Series) -> dict:
        ok = a.notna() & b.notna() & c.notna()
        ranks = [stats.rankdata(v[ok]) for v in (a, b, c)]
        residual = [r - np.polyval(np.polyfit(ranks[2], r, 1), ranks[2]) for r in ranks[:2]]
        result = stats.pearsonr(*residual)
        return {"rho": round(float(result.statistic), 3), "p": float(result.pvalue), "n": int(ok.sum())}

    ratio = dev["fev1_fvc_post_v1"]
    out["descontando"] = [
        {"variable": name, "todos": partial(dev[SCORE], ratio, values),
         "controles": partial(controls[SCORE], ratio[controls.index], values[controls.index])}
        for name, values in (("pixel_mm", quality["pixel_mm"]), ("imc", dev["imc_v1"]))]

    # 6c. ¿Depende el resultado de la constante que se suma al enfisema antes del logaritmo?
    import maps.cohort as cohort_module
    original = cohort_module.LOG_FLOOR
    out["constante_del_logaritmo"] = []
    for constant in LOG_CONSTANTS:
        cohort_module.LOG_FLOOR = constant
        trial = damage_score(region_z(cohort_features, subjects, reference, covariates, categorical), panel).reindex(dev.index)
        out["constante_del_logaritmo"].append({"constante": constant, "auc_epoc": round(auc(dev["caso_v1"].to_numpy(dtype=float), trial.to_numpy(dtype=float)), 3),
                                               "rho_fev1_fvc": association(trial, dev["fev1_fvc_post_v1"]).get("rho")})
    cohort_module.LOG_FLOOR = original

    # 7. La puntuación en cada clase, y cómo es cada clase en lo demás.
    known = dev["enfisema_visual"].notna()
    out["enfisema_visual"] = {"kappa": round(float(cohen_kappa_score(dev.loc[known, "enfisema_visual"] == "sí", dev.loc[known, "dano_tc"] == "sí")), 3),
                              "n": int(known.sum())}
    out["enfisema_medido"] = {group: {measure: round(float(whole.loc[members.index, measure].median()), 3) for measure in ("laa950", "laa950_smooth")}
                              for group, members in (("controles", controls), ("epoc", cases))}
    out["clinica_por_clase"] = {}
    for name in CLASSES:
        members = dev[dev["clase_maps"] == name]
        if len(members) < MIN_CELL:
            continue
        entry = {"n": len(members), "fuman_pct": round(100 * float((members["fuma"] == "fuma").mean())),
                 "enfisema_visual_pct": round(100 * float((members["enfisema_visual"] == "sí").mean()))}
        for column, label in CLASS_TABLE.items():
            values = members[column].dropna()
            entry[label] = round(float(values.median()), 2) if len(values) >= MIN_CELL else None
        out["clinica_por_clase"][name] = entry

    out["por_clase"] = {name: quantiles(dev.loc[dev["clase_maps"] == name, SCORE]) for name in CLASSES}
    pre = dev["clase_maps"] == "pre-EPOC"
    out["pre_epoc"] = {"n": int(pre.sum()), "por_tc": int((pre & (dev["dano_tc"] == "sí")).sum()),
                       "por_fev1": int((pre & (dev["FEV1pp_GLI_v1"] < 80)).sum())}

    (cohort / "comprobaciones.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({key: value for key, value in out.items() if key not in ("por_medida", "paneles")}, indent=1, ensure_ascii=False))
    table = pd.DataFrame([{"medida": r["medida"], "en": "sí" if r["en_la_puntuacion"] else "", "AUC EPOC": r["auc_epoc"],
                           "rho FEV1/FVC": r["fev1_fvc_post_v1"].get("rho"), "q": r["fev1_fvc_post_v1"].get("q"),
                           "rho DLCO": r["DLCO_v1"].get("rho"), "rho CAT": r["CAT_v1"].get("rho"), "AUC fuma": r["fuma"],
                           "ICC": r.get("icc_kernel")} for r in rows])
    pd.set_option("display.width", 200)
    print(table.round(2).to_string(index=False))
    if "paneles" in out:
        print(pd.DataFrame(out["paneles"]).to_string(index=False))


if __name__ == "__main__":
    main()
