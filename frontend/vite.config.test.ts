// @vitest-environment node
import { describe, expect, it } from "vitest";
import { apiProxyTarget } from "./vite.config";

describe("proxy de la API en desarrollo", () => {
  it("usa la API publicada por Compose cuando Vite corre fuera de Compose", () => {
    expect(apiProxyTarget({})).toBe("http://127.0.0.1:8100");
  });

  it("respeta API_PROXY_TARGET, como el servicio de Compose o un uvicorn local", () => {
    expect(apiProxyTarget({ API_PROXY_TARGET: "http://api:8000" })).toBe("http://api:8000");
    expect(apiProxyTarget({ API_PROXY_TARGET: " http://127.0.0.1:8000 " })).toBe("http://127.0.0.1:8000");
  });
});
