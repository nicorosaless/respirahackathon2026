import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def _run(config: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")])}
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "connect.py"), str(config)],
                          capture_output=True, text=True, env=env)


def _cohort(folder: Path, n: int = 90) -> Path:
    """Cohorte ya puntuada y una tabla molecular con 40 rasgos: uno sigue la puntuación de daño y el resto es ruido."""
    rng = np.random.default_rng(0)
    ids = [f"s{i:03d}" for i in range(n)]
    score = rng.normal(0, 1, n)
    age = rng.normal(45, 4, n)
    pd.DataFrame({"subject_id": ids, "puntuacion_dano": score, "edad": age, "sexo": rng.choice(["H", "M"], n),
                  "particion": ["desarrollo"] * (n - 10) + ["reserva"] * 10}).to_csv(folder / "subjects.csv", index=False)
    pd.DataFrame({"subject_id": ids, "region": "pulmon", "via_longitud_mm": -score + rng.normal(0, 0.3, n)}).to_csv(
        folder / "zscores.csv", index=False)
    molecular = pd.DataFrame(rng.normal(0, 1, (n, 40)), columns=[f"cg{i:02d}" for i in range(40)])
    molecular["cg07"] = 0.9 * score + 0.05 * age + rng.normal(0, 0.5, n)
    molecular.insert(0, "id", ids)
    molecular.to_csv(folder / "molecular.csv", index=False)
    config = folder / "cohorte.toml"
    config.write_text(f"""
cohorte = "{folder}"
[molecular]
tabla = "{folder / 'molecular.csv'}"
id = "id"
exposiciones = ["puntuacion_dano", "tc:via_longitud_mm"]
covariables = ["edad", "sexo"]
filtro = "particion == 'desarrollo'"
permutaciones = 200
""")
    return config


def test_the_planted_trait_is_found_for_both_exposures_and_noise_is_not(tmp_path):
    result = _run(_cohort(tmp_path))

    assert result.returncode == 0, result.stderr
    table = pd.read_csv(tmp_path / "conexion.csv")
    for exposure in ("puntuacion_dano", "tc:via_longitud_mm"):
        rows = table[table["exposicion"] == exposure].sort_values("p")
        assert rows.iloc[0]["rasgo"] == "cg07"
        assert rows.iloc[0]["fdr"] < 0.01
        assert (rows.iloc[1:]["fdr"] > 0.05).all()
        assert (rows["n"] == 80).all()  # los de reserva no entran
    # el z de una medida va orientado: más daño, más cg07, igual que con la puntuación
    assert (table[table["rasgo"] == "cg07"]["coef"] > 0).all()
    summary = json.loads((tmp_path / "conexion.json").read_text())
    assert summary["exposiciones"]["puntuacion_dano"]["permutacion_p"] < 0.05
    assert summary["exposiciones"]["puntuacion_dano"]["rasgos_fdr_5"] == 1


def test_the_output_on_screen_names_no_subject(tmp_path):
    result = _run(_cohort(tmp_path))

    assert "s0" not in result.stdout
