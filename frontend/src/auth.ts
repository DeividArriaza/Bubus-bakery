export type AuthUser = { email: string; name: string; role: "customer" | "operator"; emailVerified: boolean };

type AuthResponse = { user: AuthUser };

async function request(path: string, options?: RequestInit): Promise<AuthResponse> {
  const response = await fetch(path, { ...options, credentials: "include", headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) } });
  const data = await response.json() as AuthResponse & { error?: string };
  if (!response.ok) throw new Error(data.error ?? "No pudimos completar la solicitud.");
  return data;
}

export function register(payload: { email: string; password: string; name: string }) {
  return request("/api/auth/register", { method: "POST", body: JSON.stringify(payload) });
}

export function login(payload: { email: string; password: string }) {
  return request("/api/auth/login", { method: "POST", body: JSON.stringify(payload) });
}

export function logout() {
  return fetch("/api/auth/logout", { method: "POST", credentials: "include" });
}

export async function getSession(): Promise<AuthUser | null> {
  const response = await fetch("/api/auth/session", { credentials: "include" });
  if (response.status === 401) return null;
  const data = await response.json() as AuthResponse & { error?: string };
  if (!response.ok) throw new Error(data.error ?? "No pudimos consultar tu sesión.");
  return data.user;
}
