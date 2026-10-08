import { describe, expect, it, vi } from "vitest";
import { createOrder, createSale } from "./orders";

describe("operaciones idempotentes", () => {
  it("reutiliza la misma clave para reintentar una solicitud", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 7 }) });
    vi.stubGlobal("fetch", fetchMock);
    await createOrder([{ slug: "mixta-caja-6", quantity: 1, options: { "sixth-brownie": "almendra" } }], "contacto", "AL_RECIBIR", "orden-estable");
    await createOrder([{ slug: "mixta-caja-6", quantity: 1, options: { "sixth-brownie": "almendra" } }], "contacto", "AL_RECIBIR", "orden-estable");
    expect(fetchMock.mock.calls[0][1].headers["Idempotency-Key"]).toBe("orden-estable");
    expect(fetchMock.mock.calls[1][1].headers["Idempotency-Key"]).toBe("orden-estable");
  });

  it("envía opciones reales de la mixta y clave de venta estable", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 8, paymentStatus: "RECIBIDO" }) });
    vi.stubGlobal("fetch", fetchMock);
    const items = [{ slug: "mixta-caja-6", quantity: 1, options: { "sixth-brownie": "simple" } }];
    await createSale(items, "efectivo", "", "", "", true, "venta-estable");
    await createSale(items, "efectivo", "", "", "", true, "venta-estable");
    expect(fetchMock.mock.calls[0][1].headers["Idempotency-Key"]).toBe("venta-estable");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).items[0].options).toEqual({ "sixth-brownie": "simple" });
    expect(fetchMock.mock.calls[1][1].headers["Idempotency-Key"]).toBe("venta-estable");
  });
});
