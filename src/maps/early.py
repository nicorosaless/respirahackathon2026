"""Variables derivadas y grupos de la cohorte EARLY COPD del reto."""

from __future__ import annotations

import numpy as np
import pandas as pd

GROUPS = ("control sin criterios", "control con síntomas o DLCO baja", "control con enfisema", "EPOC")


def derive(table: pd.DataFrame) -> pd.DataFrame:
    """Añade lo que se deduce de la tabla: cociente FEV1/FVC, obstrucción, PRISm y cambio entre visitas."""
    t = table.copy()
    for visit in ("v1", "v2"):
        ratio = t[f"FEV1postBDlitros_{visit}"] / t[f"FVCpostBDlitros_{visit}"]
        t[f"fev1_fvc_post_{visit}"] = ratio
        t[f"obstruccion_{visit}"] = (ratio < 0.7).where(ratio.notna())
        t[f"prism_{visit}"] = ((ratio >= 0.7) & (t[f"FEV1pp_GLI_{visit}"] < 80)).where(ratio.notna())
    t["anos_seguimiento"] = t["edat_v2"] - t["edat_round_v1"]
    t["caida_fev1_ml_ano"] = 1000 * (t["FEV1postBDlitros_v1"] - t["FEV1postBDlitros_v2"]) / t["anos_seguimiento"]
    t["cambio_fev1pp"] = t["FEV1pp_GLI_v2"] - t["FEV1pp_GLI_v1"]
    t["grupo"] = profile_group(t)
    return t


def profile_group(t: pd.DataFrame) -> pd.Series:
    """Cuatro grupos descriptivos de la visita 1.

    Sirven para explorar y para la app. El de enfisema sale de la lectura
    visual de la TC, así que no vale como objetivo para validar medidas de TC.
    """
    symptomatic = (t["DLCO_v1"] < 80) | (t["CAT_v1"] >= 10) | (t["mmrc_num_v1"] >= 2)
    group = np.select(
        [t["caso_v1"] == 1, t["enfisema_SI_v1"] == 1, symptomatic],
        [GROUPS[3], GROUPS[2], GROUPS[1]],
        default=GROUPS[0],
    )
    return pd.Series(pd.Categorical(group, categories=GROUPS, ordered=True), index=t.index)
