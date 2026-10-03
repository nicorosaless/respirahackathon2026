import { describe, expect, it } from "vitest";
import { type Cohorte, type Complejidad, coincidenciaConLaEspirometria, correlacionPrincipal, curvaDeComplejidad, type Embudo, modeloConTodas, salidaDelEmbudo, ejemplosDeClase, ejemplosDeInferencia, fraccionDeTexto, lectura, nivelTC, personaDeEjemplo, type Sujeto } from "./cohorte";

const umbrales = { umbral_dano: 0.48, umbral_normalidad: 1.23, comprobaciones: {} } as unknown as Cohorte;

describe("nivelTC", () => {
  it("parte la puntuación en tres niveles con los dos umbrales", () => {
    expect(nivelTC({ puntuacion: 0.2 }, umbrales)).toBe("esperada");
    expect(nivelTC({ puntuacion: 0.48 }, umbrales)).toBe("intermedia");
    expect(nivelTC({ puntuacion: 1.5 }, umbrales)).toBe("alta");
  });

  it("respeta el nivel que trae la exportación y no inventa uno sin puntuación", () => {
    expect(nivelTC({ puntuacion: 0.2, nivel_tc: "alta" }, umbrales)).toBe("alta");
    expect(nivelTC({ puntuacion: null }, umbrales)).toBeNull();
  });

  it("sin límite de normalidad solo distingue por el umbral", () => {
    const sinLimite = { umbral_dano: 0.48, comprobaciones: {} } as unknown as Cohorte;
    expect(nivelTC({ puntuacion: 3 }, sinLimite)).toBe("intermedia");
  });
});

describe("correlacionPrincipal", () => {
  const asociaciones = [{ variable: "FEV1/FVC", todos: { rho: -0.719, p: 1e-13, n: 80 } }];
  const fila = { medida: "via_longitud_mm", referencia: "todos los controles", rho_media: -0.726, rho_ic95: [-0.834, -0.566], rho_p: 1e-14 };

  it("da la cifra fuera de muestra cuando hay validación", () => {
    const cohorte = { comprobaciones: { asociaciones }, validacion: { sujetos: 80, resultados: [{ ...fila, referencia: "controles lejos de la obstrucción", rho_media: -0.9 }, fila] } } as unknown as Cohorte;
    expect(correlacionPrincipal(cohorte)).toMatchObject({ rho: -0.726, n: 80, ic95: [-0.834, -0.566], fueraDeMuestra: true });
  });

  it("sin validación cae a la de la cohorte y lo dice", () => {
    const cohorte = { comprobaciones: { asociaciones }, validacion: null } as unknown as Cohorte;
    expect(correlacionPrincipal(cohorte)).toMatchObject({ rho: -0.719, ic95: null, fueraDeMuestra: false });
  });
});

describe("lectura", () => {
  const cohorte = {
    discordantes: {
      dentro_de_los_casos: { puntuacion: [{ variable: "Disnea (mMRC)", rho: 0.69, p: 0.00005, q: 0.001, n: 28 }] },
      dentro_de_los_controles: { puntuacion: [{ variable: "Calibre central para su pulmón (z; más es más estrecho)", rho: 0.371, p: 0.0067, q: 0.115, n: 52 }] },
    },
  } as unknown as Cohorte;

  it("encuentra cada variable en su grupo y no la confunde con el otro", () => {
    expect(lectura(cohorte, "casos", "Disnea")?.rho).toBe(0.69);
    expect(lectura(cohorte, "controles", "Calibre central")?.q).toBe(0.115);
    expect(lectura(cohorte, "controles", "Disnea")).toBeUndefined();
  });

  it("no inventa nada si la cohorte no trae el análisis", () => {
    expect(lectura({ discordantes: null } as unknown as Cohorte, "casos", "Disnea")).toBeUndefined();
  });
});

describe("ejemplosDeClase y ejemplosDeInferencia", () => {
  const sujeto = (id: string, clase: string, puntuacion: number, mas: object = {}) =>
    ({ id, clase, puntuacion, particion: "desarrollo", imagen: id, arbol: true, cerca_umbral: false, congelado: null, ...mas }) as unknown as Sujeto;
  const sujetos = [sujeto("a", "control", -1), sujeto("b", "control", -0.3), sujeto("c", "control", 0.2, { cerca_umbral: true }), sujeto("r1", "EPOC", 2, { particion: "reserva" }), sujeto("r2", "EPOC", 1, { particion: "reserva", congelado: {} })];

  it("abre el elegido y deja las alternativas detrás", () => {
    const ejemplos = { clases: { control: { elegido: "c", alternativas: ["a"], candidatos: 3 } }, inferencia: { elegido: "r1", alternativas: [], candidatos: 2, criterio: "" } };
    const cohorte = { sujetos, ejemplos } as unknown as Cohorte;
    expect(ejemplosDeClase(cohorte, "control").map((s) => s.id)).toEqual(["c", "a"]);
    expect(ejemplosDeInferencia(cohorte).map((s) => s.id)).toEqual(["r1"]);
  });

  it("sin ejemplos elige el más cercano a la mediana de su clase y, para la inferencia, uno con la lectura del modelo probado", () => {
    const cohorte = { sujetos, ejemplos: null } as unknown as Cohorte;
    expect(ejemplosDeClase(cohorte, "control")[0].id).toBe("b");
    expect(ejemplosDeInferencia(cohorte)[0].id).toBe("r2");
  });
});

describe("personaDeEjemplo y fraccionDeTexto", () => {
  it("elige a alguien con obstrucción, con la TC clara y cerca de 0,61", () => {
    const base = { caso: true, dano_tc: true, ciego: { grupo: "alto" }, z: { via: 2.2 }, clinica: { fev1_fvc: 0.61, talla: 170 }, esperado: { via_longitud_mm: 5200 }, valores: { via_longitud_mm: 4300 } };
    const sujetos = [
      { ...base, id: "sin-obstruccion", puntuacion: 1, caso: false },
      { ...base, id: "lejos", puntuacion: 1, clinica: { fev1_fvc: 0.48, talla: 170 } },
      { ...base, id: "buena", puntuacion: 1 },
      { ...base, id: "tc-por-debajo", puntuacion: 0.1, dano_tc: false },
    ];
    expect(personaDeEjemplo({ sujetos } as unknown as Cohorte)?.id).toBe("buena");
  });

  it("lee una fracción escrita como texto", () => {
    expect(fraccionDeTexto("64 de 80")).toEqual({ aciertos: 64, de: 80 });
    expect(fraccionDeTexto("muchos")).toBeNull();
  });
});

describe("salidaDelEmbudo", () => {
  // Cuatro filas de `docs/figuras/embudo.json`, una por cada salida.
  const embudo = { criterios: { acuerdo_minimo: 0.9, q_maximo: 0.05, p_descontando_maximo: 0.05 }, elegidas: ["via_extremos", "laa950_smooth"] } as Pick<Embudo, "criterios" | "elegidas">;
  const paso = (medida: string, icc: number, q: number) => ({ medida, nombre: medida, icc, rho: -0.4, p: q / 10, q, resultado: "" });

  it("saca primero a la inestable aunque se asocie, como el %LAA-950 clásico", () => {
    expect(salidaDelEmbudo(paso("laa950", 0.184, 0.0029), embudo)).toBe("inestable");
  });

  it("después a la estable que no se asocia, y deja dentro solo a las elegidas", () => {
    expect(salidaDelEmbudo(paso("densidad_g_l", 0.992, 0.316), embudo)).toBe("sin asociación");
    expect(salidaDelEmbudo(paso("vasos_por_litro", 0.932, 0.00034), embudo)).toBe("redundante");
    expect(salidaDelEmbudo(paso("laa950_smooth", 0.926, 0.00034), embudo)).toBe("dentro");
  });
});

describe("curvaDeComplejidad", () => {
  const complejidad = {
    sujetos: 80,
    repeticiones: 5,
    modelos: [
      { modelo: "2 medidas", auc: 0.909, rho_fev1_fvc: -0.715, icc: 0.981, medidas: [] },
      { modelo: "clínica sola", auc: 0.625, rho_fev1_fvc: -0.232, icc: null, medidas: null },
      { modelo: "1 medida", auc: 0.916, rho_fev1_fvc: -0.666, icc: 0.972, medidas: [] },
      { modelo: "logística con todas las medidas de TC", auc: 0.846, rho_fev1_fvc: -0.605, icc: 0.427, medidas: null },
    ],
  } as Complejidad;

  it("se queda con los modelos por número de medidas, en orden", () => {
    expect(curvaDeComplejidad(complejidad).map((m) => [m.n, m.auc])).toEqual([
      [1, 0.916],
      [2, 0.909],
    ]);
  });

  it("encuentra aparte el de los pesos aprendidos con todas", () => {
    expect(modeloConTodas(complejidad)?.icc).toBe(0.427);
    expect(modeloConTodas(null)).toBeUndefined();
  });
});

describe("coincidenciaConLaEspirometria", () => {
  it("cuenta a los que la línea de la TC deja del lado de su espirometría", () => {
    const sujeto = (caso: boolean, dano_tc: boolean) => ({ caso, dano_tc, puntuacion: dano_tc ? 1 : 0 });
    const cohorte = { sujetos: [sujeto(true, true), sujeto(true, false), sujeto(false, false), sujeto(false, true), sujeto(false, false)] } as unknown as Cohorte;
    expect(coincidenciaConLaEspirometria(cohorte)).toEqual({ epocPorEncima: 1, epoc: 2, controlesPorDebajo: 2, controles: 3 });
  });
});
