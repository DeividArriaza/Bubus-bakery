export type ProductKind = "individual" | "composite";

export type Product = {
  slug: string;
  name: string;
  kind: ProductKind;
  category: string;
  presentation: "individual" | "caja6";
  description: string;
  currency: "GTQ";
  priceCents: number;
  prices?: { individual?: number; caja6?: number };
  composition: { product: string; quantity: number }[];
  optionGroups: {
    code: string;
    label: string;
    minSelections: number;
    maxSelections: number;
    options: { product: string; quantity: number }[];
  }[];
};

export type CatalogResponse = { products: Product[] };
