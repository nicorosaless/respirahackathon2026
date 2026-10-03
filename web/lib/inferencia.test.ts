import { describe, expect, it } from "vitest";
import type { Cohorte, Reserva, Sujeto } from "./cohorte";
import { comparacion, criteriosDeReserva, describirPersona, desviacionEnPalabras, lecturaDeInferencia, nombreDelModelo, tablaDeContraste, veredicto } from "./inferencia";

const clinica: Sujeto["clinica"] = { edad: 43, sexo: "H", talla: 182, fuma: true, paquetes_ano: 21, fev1_fvc: 0.71, fev1_pct: 95, dlco_pct: 89, cat: 5, kvp: 100 };

describe("describirPersona", () => {
  it("dice sexo, edad, talla y tabaco", () => {
    expect(describirPersona(clinica)).toBe("un hombre de 43 años, 182 cm, fumador");
    expect(describirPersona({ ...clinica, sexo: "M", fuma: false })).toBe("una mujer de 43 años, 182 cm, exfumadora");
  });

  it("calla lo que falta en la tabla", () => {
    expect(describirPersona({ ...clinica, edad: null, talla: null })).toBe("un hombre, fumador");
  });
});

describe("comparacion", () => {
  it("no da veces entre porcentajes de menos del 1 %: dice que no hay enfisema medible", () => {
    expect(comparacion("laa950_smooth", 0.16, 0.04)).toBe("sin enfisema medible (menos del 1 %)");
    expect(comparacion("laa950_smooth", 0.03, 0.04)).toBe("sin enfisema medible (menos del 1 %)");
    expect(comparacion("laa950_smooth", 2.4, 0.3)).toBe("por encima de lo esperado");
  });

  it("cuenta el enfisema en veces cuando los dos se pueden medir, y el árbol en metros", () => {
    expect(comparacion("laa950_smooth", 6, 2)).toBe("3,0 veces lo esperado");
    expect(comparacion("laa950_smooth", 1.5, 2)).toBe("por debajo de lo esperado");
    expect(comparacion("laa950_smooth", 2, 2)).toBe("como lo esperado");
    expect(comparacion("via_longitud_mm", 4570, 5210)).toBe("0,64 m menos de lo esperado");
    expect(comparacion("via_longitud_mm", 5400, 5210)).toBe("0,19 m más de lo esperado");
  });

  it("no compara sin un valor esperado", () => {
    expect(comparacion("laa950_smooth", 0.16, null)).toBeNull();
    expect(comparacion("laa950_smooth", 0.16, 0)).toBeNull();
  });
});

describe("desviacionEnPalabras", () => {
  it("dice la dirección con palabras: en el árbol, una desviación positiva es menos árbol", () => {
    expect(desviacionEnPalabras("via", 1.32)).toEqual({ cuanto: "1,3", direccion: "desviaciones menos árbol de lo esperado" });
    expect(desviacionEnPalabras("via", -0.62)).toEqual({ cuanto: "0,6", direccion: "desviaciones más árbol de lo esperado" });
    expect(desviacionEnPalabras("enfisema", 0.3)).toEqual({ cuanto: "0,3", direccion: "desviaciones más enfisema de lo esperado" });
    expect(desviacionEnPalabras("enfisema", -1.2)).toEqual({ cuanto: "1,2", direccion: "desviaciones menos enfisema de lo esperado" });
  });

  it("no inventa una dirección para un cero ni para un dato que falta", () => {
    expect(desviacionEnPalabras("enfisema", 0.03)).toEqual({ cuanto: "0,0", direccion: "desviaciones: como lo esperado" });
    expect(desviacionEnPalabras("via", -0.04)).toEqual({ cuanto: "0,0", direccion: "desviaciones: como lo esperado" });
    expect(desviacionEnPalabras("via", null)).toBeNull();
  });
});

describe("tablaDeContraste", () => {
  it("saca las cuatro casillas de la sensibilidad y la especificidad", () => {
    const reserva = { sensibilidad: { aciertos: 4, de: 5, valor: 0.8 }, especificidad: { aciertos: 8, de: 10, valor: 0.8 } } as Reserva;
    expect(tablaDeContraste(reserva)).toEqual({ danoConObstruccion: 4, sinDanoConObstruccion: 1, danoSinObstruccion: 2, sinDanoSinObstruccion: 8 });
  });
});

describe("veredicto", () => {
  const sujeto = (dano_tc: boolean, caso: boolean) => ({ dano_tc, caso }) as Sujeto;

  it("coincide cuando la TC y la espirometría dicen lo mismo", () => {
    expect(veredicto(sujeto(true, true)).coincide).toBe(true);
    expect(veredicto(sujeto(false, false)).coincide).toBe(true);
  });

  it("no llama error a una TC parecida sin obstrucción: es lo que la regla deja como posible pre-EPOC", () => {
    const resultado = veredicto(sujeto(true, false));
    expect(resultado.coincide).toBe(false);
    expect(resultado.texto).toContain("posible pre-EPOC");
  });

  it("no dice daño: superar el umbral no demuestra una lesión", () => {
    for (const dano of [true, false]) for (const caso of [true, false]) expect(veredicto(sujeto(dano, caso)).texto).not.toMatch(/daño/);
  });

  it("dice que la TC no lo detecta cuando hay obstrucción sin daño", () => {
    const resultado = veredicto(sujeto(false, true));
    expect(resultado.coincide).toBe(false);
    expect(resultado.texto).toContain("no lo detecta");
  });
});

describe("criteriosDeReserva", () => {
  const reserva = {
    separa_epoc: { auc: 0.852, ic95: [0.611, 1], n: 15, casos: 6 },
    fev1_fvc: { rho: -0.807, p: 0.0003, n: 15 },
    sensibilidad: { aciertos: 6, de: 6, valor: 1 },
    especificidad: { aciertos: 5, de: 9, valor: 0.556 },
    calibracion_controles: { n: 9, puntuacion: { mediana: 0.015, dispersion: 1.1 } },
    otra_reconstruccion: { icc: 0.991, separa_epoc: { auc: 0.889, ic95: [0.667, 1], n: 15, casos: 6 }, misma_decision_de_dano: { aciertos: 15, de: 15, valor: 1 } },
    anade_a_la_clinica: [
      { hasta: "clínica", rho: 0.061, p: 0.83, n: 15 },
      { hasta: "TC", rho: 0.889, p: 0.00001, n: 15 },
    ],
    criterios: { separa_epoc: true, sigue_el_cociente: true, controles_centrados: true, controles_con_dispersion_normal: true, fracaso: false, estable_entre_reconstrucciones: true },
  } as unknown as Reserva;

  it("dice que el umbral cumple por poco cuando un control más lo habría hecho fallar", () => {
    const umbral = criteriosDeReserva(reserva).find((c) => c.pregunta.includes("umbral"));
    expect(umbral).toMatchObject({ resultado: "Por encima: 6 de 6 EPOC, 4 de 9 controles", cumple: true, porPoco: true });
  });

  it("informa de lo que añade a la clínica sin criterio", () => {
    const clinica = criteriosDeReserva(reserva).at(-1);
    expect(clinica).toMatchObject({ resultado: "Clínica sola 0,06; con la TC 0,89", esperado: null, cumple: null });
  });

  it("no afirma que cumple si la exportación no trae los criterios", () => {
    const sinCriterios = { ...reserva, criterios: undefined } as unknown as Reserva;
    expect(criteriosDeReserva(sinCriterios).every((c) => c.cumple === null)).toBe(true);
  });
});

describe("lecturaDeInferencia", () => {
  const final = { puntuacion: 0.6, dano_tc: true, cerca_umbral: true, nivel_tc: "intermedia", z: { enfisema: 0.5, via: 0.7 }, valores: { laa950_smooth: 0.1, via_longitud_mm: 5000 }, esperado: { laa950_smooth: 0.04, via_longitud_mm: 5200 } };
  const congelado = { ...final, puntuacion: 0.3, dano_tc: false, cerca_umbral: true, nivel_tc: "esperada", clase: "control", motivo: "" };
  const cohorte = { umbral_dano: 0.48, umbral_normalidad: 1.23, comprobaciones: { sujetos: 80 }, congelado: { umbral_dano: 0.376, umbral_normalidad: 1.286, zona_gris: 0.186, sujetos_de_ajuste: 62 } } as unknown as Cohorte;

  it("en un sujeto de reserva usa solo el modelo que no lo vio, con sus umbrales", () => {
    const lectura = lecturaDeInferencia({ ...final, congelado } as unknown as Sujeto, cohorte);
    expect(lectura).toMatchObject({ delModeloProbado: true, puntuacion: 0.3, dano_tc: false, nivel: "esperada", umbral: 0.376, normalidad: 1.286, sujetosDeAjuste: 62 });
  });

  it("sin esa lectura cae al modelo final y lo dice", () => {
    const lectura = lecturaDeInferencia({ ...final, congelado: null } as unknown as Sujeto, cohorte);
    expect(lectura).toMatchObject({ delModeloProbado: false, puntuacion: 0.6, dano_tc: true, umbral: 0.48, normalidad: 1.23, sujetosDeAjuste: 80 });
    const sinModelo = lecturaDeInferencia({ ...final, congelado } as unknown as Sujeto, { ...cohorte, congelado: null } as unknown as Cohorte);
    expect(sinModelo.delModeloProbado).toBe(false);
  });

  it("nombra el modelo de los umbrales que se enseñan: congelado en la reserva, final con los 80", () => {
    expect(nombreDelModelo(lecturaDeInferencia({ ...final, congelado } as unknown as Sujeto, cohorte))).toBe("Umbrales del modelo congelado, probado en la reserva (62 sujetos)");
    expect(nombreDelModelo(lecturaDeInferencia({ ...final, congelado: null } as unknown as Sujeto, cohorte))).toBe("Umbrales del modelo final, 80 sujetos");
  });
});
