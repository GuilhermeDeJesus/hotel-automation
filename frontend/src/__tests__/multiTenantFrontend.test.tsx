import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { TenantProvider, useTenant } from "../contexts/TenantContext";
import { useKpis } from "../hooks/useKpis";
import * as clientModule from "../api/client";

function TenantConsumer() {
  const { hotelId } = useTenant();
  return <div data-testid="hotel-id">{hotelId}</div>;
}

function KpisConsumer() {
  useKpis();
  return <div>kpis-consumer</div>;
}

function wrapWithProviders(children: React.ReactNode, initialPath = "/") {
  return (
    <MemoryRouter initialEntries={[initialPath]}>
      <TenantProvider>{children}</TenantProvider>
    </MemoryRouter>
  );
}

function createToken(payload: object): string {
  const header = { alg: "HS256", typ: "JWT" };
  const toBase64Url = (obj: object) =>
    btoa(JSON.stringify(obj)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${toBase64Url(header)}.${toBase64Url(payload)}.signature`;
}

describe("TenantContext multi-tenant resolution", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("resolve hotelId from token payload", () => {
    const token = createToken({ hotel_id: "hotel-token-123" });
    localStorage.setItem("auth_token", token);

    render(wrapWithProviders(<TenantConsumer />));
    const el = screen.getByTestId("hotel-id");
    expect(el.textContent ?? "").toBe("hotel-token-123");
  });

  it("route param overrides token hotel_id", () => {
    const token = createToken({ hotel_id: "hotel-token-123" });
    localStorage.setItem("auth_token", token);

    render(
      <MemoryRouter initialEntries={["/hotels/hotel-route-999"]}>
        <Routes>
          <Route
            path="/hotels/:hotelId"
            element={
              <TenantProvider>
                <TenantConsumer />
              </TenantProvider>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    const el = screen.getByTestId("hotel-id");
    expect(el.textContent ?? "").toBe("hotel-route-999");
  });
});

describe("Hooks useKpis multi-tenant behaviour", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.spyOn(clientModule, "fetchKpis").mockResolvedValue({} as any);
  });

  it("calls fetchKpis with hotelId from TenantContext", async () => {
    const token = createToken({ hotel_id: "hotel-hook-001" });
    localStorage.setItem("auth_token", token);

    render(wrapWithProviders(<KpisConsumer />));

    expect(clientModule.fetchKpis).toHaveBeenCalledTimes(1);
    expect((clientModule.fetchKpis as any).mock.calls[0][0]).toBe("hotel-hook-001");
  });
});

