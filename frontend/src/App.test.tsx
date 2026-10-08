import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import App from "./App";

const catalog = {
  products: [
    {
      slug: "mixta",
      name: "Caja mixta",
      kind: "composite",
      category: "brownie",
      presentation: "caja6",
      description: "Seis brownies con una elección limitada.",
      priceCents: 8500,
      composition: [
        { product: "snickers", quantity: 2 },
        { product: "m-and-m", quantity: 3 },
      ],
      optionGroups: [
        {
          code: "sixth-brownie",
          label: "Elige el sexto brownie",
          minSelections: 1,
          maxSelections: 1,
          options: [
            { product: "almendra", quantity: 1 },
            { product: "simple", quantity: 1 },
          ],
        },
      ],
    },
  ],
};

describe("landing de catálogo", () => {
  it("muestra encabezado, precio GTQ y opciones de la caja mixta", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => catalog }));
    render(<App />);
    expect(screen.getByRole("heading", { name: /Un pequeño cuadrado/i })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Q85.00")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Ver composición" }));
    expect(screen.getByText("Elige el sexto brownie")).toBeInTheDocument();
    expect(screen.getByLabelText("Almendra")).toBeInTheDocument();
  });

  it("muestra estado de error en español", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("fallo")));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos cargar el catálogo");
  });

  it("filtra presentaciones de caja", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => catalog }));
    render(<App />);
    await waitFor(() => expect(screen.getByText("Q85.00")).toBeInTheDocument());
    await userEvent.click(within(screen.getByRole("group", { name: "Filtrar catálogo" })).getByRole("button", { name: "Cajas de 6" }));
    expect(screen.getAllByRole("article")).toHaveLength(1);
  });

  it("permite abrir acceso en español y mantiene Google honesto si no está configurado", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => catalog })
      .mockResolvedValueOnce({ status: 401, ok: false, json: async () => ({ error: "Necesitas iniciar sesión." }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
    expect(screen.getByRole("heading", { name: "Bienvenido de nuevo." })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Continuar con Google/ })).toBeDisabled();
  });

  it("muestra el error de login de la API en español", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => catalog })
      .mockResolvedValueOnce({ status: 401, ok: false, json: async () => ({ error: "Necesitas iniciar sesión." }) })
      .mockResolvedValueOnce({ status: 401, ok: false, json: async () => ({ error: "Correo o contraseña incorrectos." }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
    const panel = screen.getByRole("region", { name: "Acceso de clientes" });
    await userEvent.type(within(panel).getByLabelText("Correo electrónico"), "cliente@ejemplo.com");
    await userEvent.type(within(panel).getByLabelText("Contraseña"), "UnaClaveSegura123!");
    await userEvent.click(within(panel).getByRole("button", { name: /^Iniciar sesión$/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Correo o contraseña incorrectos.");
  });
});
