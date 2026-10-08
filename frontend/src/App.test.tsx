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

const operatorCatalog = {
  ...catalog,
  products: [...catalog.products, { ...catalog.products[0], slug: "simple-caja-6", name: "Caja de 6 Simple", composition: [{ product: "simple", quantity: 6 }], optionGroups: [] }],
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

  it("bloquea doble clic del POS y muestra las dos opciones de la mixta", async () => {
    let resolveSale: ((value: unknown) => void) | undefined;
    const salePending = new Promise((resolve) => { resolveSale = resolve; });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => operatorCatalog })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ user: { email: "operador@ejemplo.com", name: "Operador", role: "operator", emailVerified: false } }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ orders: [] }) })
      .mockReturnValueOnce(salePending);
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
    expect(await screen.findByRole("heading", { name: "Registro de ventas." })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "almendra" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "simple" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: /Confirmo/ }));
    const submit = screen.getByRole("button", { name: "Registrar venta" });
    await userEvent.click(submit);
    await userEvent.click(submit);
    expect(fetchMock).toHaveBeenCalledTimes(4);
    resolveSale?.({ id: 99 });
  });

  it("envía selección mixta y no muestra opciones falsas en caja homogénea", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => operatorCatalog })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ user: { email: "operador@ejemplo.com", name: "Operador", role: "operator", emailVerified: false } }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ orders: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 100, paymentStatus: "RECIBIDO" }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
    await screen.findByRole("heading", { name: "Registro de ventas." });
    await userEvent.click(screen.getByRole("radio", { name: /^simple$/ }));
    await userEvent.click(screen.getByRole("checkbox", { name: /Confirmo/ }));
    await userEvent.click(screen.getByRole("button", { name: "Registrar venta" }));
    expect(JSON.parse(fetchMock.mock.calls[3][1].body).items[0].options).toEqual({ "sixth-brownie": "simple" });
    await userEvent.selectOptions(screen.getByLabelText("Producto"), "simple-caja-6");
    expect(screen.queryByRole("radio", { name: "almendra" })).not.toBeInTheDocument();
  });

  it("reintenta tras una falla de red con la misma operación y no crea una segunda venta", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => operatorCatalog })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ user: { email: "operador@ejemplo.com", name: "Operador", role: "operator", emailVerified: false } }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ orders: [] }) })
      .mockRejectedValueOnce(new Error("La red no respondió"))
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 101, paymentStatus: "RECIBIDO" }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
    await screen.findByRole("heading", { name: "Registro de ventas." });
    await userEvent.click(screen.getByRole("checkbox", { name: /Confirmo/ }));
    await userEvent.click(screen.getByRole("button", { name: "Registrar venta" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("La red no respondió");
    expect(screen.getByLabelText("Cantidad")).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Reintentar venta" }));
    await waitFor(() => expect(screen.getByText("Venta #101 registrada.")).toBeInTheDocument());
    expect(fetchMock.mock.calls[3][1].headers["Idempotency-Key"]).toBe(fetchMock.mock.calls[4][1].headers["Idempotency-Key"]);
  });

  it("reconcilia la selección al cambiar de caja con otra opción válida", async () => {
    const simple = { ...operatorCatalog.products[1], optionGroups: [] };
    const mixedWithOnlySimple = { ...catalog.products[0], optionGroups: [{ ...catalog.products[0].optionGroups[0], options: [{ product: "simple", quantity: 1 }] }] };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ products: [simple, mixedWithOnlySimple] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ user: { email: "cliente@ejemplo.com", name: "Cliente", role: "customer", emailVerified: false } }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
    await screen.findByRole("heading", { name: "Solicita una caja." });
    await userEvent.selectOptions(screen.getByLabelText("Caja"), "mixta");
    expect(screen.getByLabelText("Elección")).toHaveValue("simple");
  });
});
