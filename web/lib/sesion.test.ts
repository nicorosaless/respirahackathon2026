import { describe, expect, it } from "vitest";
import { RELOJ_PARADO, SEGUNDOS_DE_DEMO, siguienteReloj } from "./sesion";

describe("siguienteReloj", () => {
  it("arranca con el primer avance y no vuelve a empezar con los siguientes", () => {
    const corriendo = siguienteReloj(RELOJ_PARADO, "arrancar", 1000);
    expect(corriendo).toEqual({ inicio: 1000, fin: null });
    expect(siguienteReloj(corriendo, "arrancar", 5000)).toEqual(corriendo);
  });

  it("se para una vez: volver del anexo y avanzar no lo reanuda", () => {
    const parado = siguienteReloj({ inicio: 1000, fin: null }, "parar", 9000);
    expect(parado).toEqual({ inicio: 1000, fin: 9000 });
    expect(siguienteReloj(parado, "parar", 12000)).toEqual(parado);
    expect(siguienteReloj(parado, "arrancar", 12000)).toEqual(parado);
  });

  it("no se para si no había arrancado", () => {
    expect(siguienteReloj(RELOJ_PARADO, "parar", 9000)).toEqual(RELOJ_PARADO);
  });

  it("vuelve a cero al borrar", () => {
    expect(siguienteReloj({ inicio: 1000, fin: 9000 }, "borrar", 12000)).toEqual(RELOJ_PARADO);
  });
});

describe("SEGUNDOS_DE_DEMO", () => {
  it("apunta a los 4:30 del guion", () => {
    expect(SEGUNDOS_DE_DEMO).toBe(4 * 60 + 30);
  });
});
