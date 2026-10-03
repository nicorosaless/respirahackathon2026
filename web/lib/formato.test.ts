import { describe, expect, it } from "vitest";
import { mediano, num, porcentaje, pValor } from "./formato";

describe("pValor", () => {
  it("escribe la p como las cifras de la demo: dos decimales", () => {
    expect(pValor(0.03397)).toBe("0,03");
    expect(pValor(0.6045)).toBe("0,60");
    expect(pValor(0.251)).toBe("0,25");
  });

  it("da el tercer decimal cuando la p es muy pequeña o está pegada a 0,05", () => {
    expect(pValor(0.0549)).toBe("0,055");
    expect(pValor(0.014076)).toBe("0,014");
    expect(pValor(0.0266)).toBe("0,03");
    expect(pValor(0.002)).toBe("0,002");
    expect(pValor(0.0000003)).toBe("< 0,001");
  });

  it("no inventa una p que falta", () => {
    expect(pValor(null)).toBe("–");
  });
});

describe("num", () => {
  it("redondea el 5 final hacia arriba, como las cifras de la demo", () => {
    expect(num(0.745, 2)).toBe("0,75");
    expect(num(0.015, 2)).toBe("0,02");
    expect(num(0.665, 2)).toBe("0,67");
  });

  it("usa coma decimal, el menos tipográfico y no escribe menos cero", () => {
    expect(num(-0.728, 2)).toBe("−0,73");
    expect(num(-0.001, 2)).toBe("0,00");
    expect(num(0.03, 1, true)).toBe("0,0");
    expect(num(6.725, 1, true)).toBe("+6,7");
  });
});

describe("mediano y porcentaje", () => {
  it("no redondea a 6 una mediana de 5,5", () => {
    expect(mediano(5.5)).toBe("5,5");
    expect(mediano(9)).toBe("9");
  });

  it("escribe una proporción como porcentaje entero", () => {
    expect(porcentaje(0.821)).toBe("82 %");
    expect(porcentaje(0.543)).toBe("54 %");
  });
});
