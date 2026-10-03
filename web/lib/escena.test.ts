import { describe, expect, it } from "vitest";
import type { Cohorte, Sujeto } from "./cohorte";
import { DANO, enjambre, geometria, puntos } from "./escena";

// Ocho sujetos: cuatro con obstrucción y cuatro sin ella. El reparto ciego falla en uno de cada lado.
function sujeto(id: string, caso: boolean, cociente: number, puntuacion: number, grupo: "alto" | "bajo", dano_tc = puntuacion >= 0.5): Sujeto {
  return {
    id,
    caso,
    dano_tc,
    puntuacion,
    clase: caso ? "EPOC" : dano_tc ? "pre-EPOC" : "control",
    z: { enfisema: puntuacion, via: puntuacion + 1 },
    valores: { laa950_smooth: 0.1, via_longitud_mm: 5000 - 400 * puntuacion },
    esperado: { laa950_smooth: 0.04, via_longitud_mm: 5200 },
    clinica: { fev1_fvc: cociente, talla: 160 + Number(id.slice(1)) * 3 },
    ciego: { puntuacion: puntuacion * 0.6, grupo },
  } as unknown as Sujeto;
}
const sujetos = [
  sujeto("s1", true, 0.55, 2.4, "alto"),
  sujeto("s2", true, 0.61, 1.8, "alto"),
  sujeto("s3", true, 0.66, 1.1, "alto"),
  sujeto("s4", true, 0.69, 0.2, "bajo"),
  sujeto("s5", false, 0.72, 0.9, "alto"),
  sujeto("s6", false, 0.76, -0.2, "bajo"),
  sujeto("s7", false, 0.8, -0.5, "bajo"),
  sujeto("s8", false, 0.84, -0.9, "bajo"),
];
const cohorte = { sujetos, umbral_cociente: 0.7, umbral_dano: 0.5, umbral_natural: { dos_grupos_por_la_tc: { umbral_de_puntuacion: 0.5 } } } as unknown as Cohorte;
const g = geometria(cohorte);

describe("los puntos de la presentación", () => {
  it("en la primera diapositiva sale primero una persona sola y después toda la cohorte", () => {
    expect(puntos(g, "soplar", 0).filter((p) => p.opacidad > 0).map((p) => p.id)).toEqual([g.persona?.id]);
    expect(puntos(g, "soplar", 2).filter((p) => p.opacidad > 0)).toHaveLength(8);
  });

  it("cada sujeto vuelve en la 5 al sitio que tenía sobre el eje de la espirometría en la 1", () => {
    const [antes, despues] = [puntos(g, "soplar", 2), puntos(g, "ciego", 2)];
    despues.forEach((p, i) => expect([p.x, p.y]).toEqual([antes[i].x, antes[i].y]));
  });

  it("al final del experimento ciego quedan en contorno los que no coinciden con su espirometría", () => {
    expect(puntos(g, "ciego", 3).filter((p) => p.hueco).map((p) => p.id)).toEqual(["s4", "s5"]);
    expect(puntos(g, "ciego", 1).filter((p) => p.color === DANO)).toHaveLength(4);
  });

  it("la nube y los cuadrantes son el mismo dibujo: cada sujeto, por su cociente y por su puntuación", () => {
    const [nube, cuadrantes] = [puntos(g, "nube", 1), puntos(g, "cuadrantes", 0)];
    cuadrantes.forEach((p, i) => expect([p.x, p.y]).toEqual([nube[i].x, nube[i].y]));
    // Más cociente, más a la derecha; más puntuación, más arriba.
    expect(nube[7].x).toBeGreaterThan(nube[0].x);
    expect(nube[0].y).toBeLessThan(nube[7].y);
  });

  it("en los cuadrantes, primero en contorno los que la línea de la TC deja al otro lado; después, los posibles pre-EPOC", () => {
    expect(puntos(g, "cuadrantes", 2).filter((p) => p.hueco).map((p) => p.id)).toEqual(["s4", "s5"]);
    expect(puntos(g, "cuadrantes", 3).filter((p) => p.color === DANO).map((p) => p.id)).toEqual(["s5"]);
  });

  it("fuera de los dibujos con puntos, todos se apagan", () => {
    expect(puntos(g, null, 0).every((p) => p.opacidad === 0)).toBe(true);
  });
});

describe("enjambre", () => {
  it("no deja dos puntos pisándose ni cruza la frontera", () => {
    const sitios = enjambre([100, 100, 100, 101, 99, 100], 10, 12, 96);
    for (let a = 0; a < sitios.length; a++) for (let b = a + 1; b < sitios.length; b++) expect(Math.hypot(sitios[a].x - sitios[b].x, sitios[a].y - sitios[b].y)).toBeGreaterThanOrEqual(22);
    expect(sitios.every((sitio) => sitio.x >= 96)).toBe(true);
  });
});
