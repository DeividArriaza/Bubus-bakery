import type { CatalogResponse } from "./types";

export async function fetchCatalog(): Promise<CatalogResponse> {
  const response = await fetch("/api/catalog");
  if (!response.ok) throw new Error("No pudimos cargar el catálogo");
  return response.json() as Promise<CatalogResponse>;
}
