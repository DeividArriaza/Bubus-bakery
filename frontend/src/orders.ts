export type OrderLine = { slug: string; quantity: number; options?: Record<string, string> };
export type OrderRecord = { id: number; status: string; paymentStatus: string; paymentIntent: string; deliveryStatus: string; fulfillment: string; subtotalCents: number; shippingAmountCents: number | null; totalFinalCents: number | null; items: Array<{ slug: string; name: string; unitPriceCents: number; quantity: number; selectedOptions: Array<{ group: string; product: string; quantity: number }> }> };

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...options, credentials: "include", headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) } });
  const data = await response.json() as T & { error?: string };
  if (!response.ok) throw new Error(data.error ?? "No pudimos completar la solicitud.");
  return data;
}

export function createOrder(items: OrderLine[], contactReference: string, paymentIntent: "NO_DEFINIDO" | "AL_PEDIR" | "AL_RECIBIR") {
  return request<OrderRecord>("/api/orders", { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ fulfillment: "envio", contactReference, paymentIntent, items }) });
}

export function listOrders() { return request<{ orders: OrderRecord[] }>("/api/orders"); }

export function listOperatorOrders() { return request<{ orders: OrderRecord[] }>("/api/operator/orders"); }

export function updateOrder(id: number, status: string) { return request<OrderRecord>(`/api/operator/orders/${id}`, { method: "PATCH", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ status }) }); }

export function createSale(items: OrderLine[], paymentMethod: "efectivo" | "transferencia", customerName: string, customerEmail: string, receivedConfirmed: boolean) {
  return request("/api/operator/sales", { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ items, paymentMethod, customerName: customerName || undefined, customerEmail: customerEmail || undefined, receivedConfirmed }) });
}
