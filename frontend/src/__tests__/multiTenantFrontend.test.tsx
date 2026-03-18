import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { TenantProvider, useTenant } from "../contexts/TenantContext";
import { useKpis } from "../hooks/useKpis";
import { useTimeseries } from "../hooks/useTimeseries";
import * as clientModule from "../api/client";

function TenantConsumer() {
  const { hotelId } = useTenant();
  return <div data-testid="hotel-id">{hotelId}</div>;
}

function KpisConsumer() {
  useKpis();
  return <div>kpis-consumer</div>;
}

function TimeseriesConsumerSwitch() {
  const { hotelId, setHotelId } = useTenant();
  const { data } = useTimeseries({
    from: "2026-01-01",
    to: "2026-01-01",
    source: "meta",
    status: "NEW",
    granularity: "day",
  });

  return (
    <div>
      <div data-testid="hotel-id">{hotelId ?? ""}</div>
      <button data-testid="set-hotel-1" onClick={() => setHotelId("hotel-1")}>
        set-hotel-1
      </button>
      <button data-testid="set-hotel-2" onClick={() => setHotelId("hotel-2")}>
        set-hotel-2
      </button>
      <div data-testid="timeseries-date">
        {data?.points?.[0]?.date ?? "none"}
      </div>
    </div>
  );
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

describe("Hooks useTimeseries multi-tenant behaviour", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.spyOn(clientModule, "fetchTimeseries").mockImplementation(() => {
      return Promise.reject(new Error("not mocked"));
    });
  });

  it("discards stale useTimeseries responses when hotelId switches quickly", async () => {
    const token = createToken({ hotel_id: "hotel-1" });
    localStorage.setItem("auth_token", token);

    const resolves: Record<string, (v: any) => void> = {};
    (clientModule.fetchTimeseries as any).mockImplementation(
      (hotelId: string) =>
        new Promise((resolve) => {
          resolves[hotelId] = resolve;
        })
    );

    render(wrapWithProviders(<TimeseriesConsumerSwitch />));

    // Garante que a troca de hotel dispara nova requisição.
    screen.getByTestId("set-hotel-2").click();

    const respHotel2 = {
      granularity: "day",
      period: { from: "2026-01-01", to: "2026-01-01", source: "meta", status: "NEW" },
      points: [
        {
          date: "hotel-2-day",
          leads: 1,
          inbound_messages: 1,
          outbound_messages: 0,
          confirmed_reservations: 0,
          checkins: 0,
          avg_response_time_seconds: 0,
        },
      ],
    };

    const respHotel1 = {
      granularity: "day",
      period: { from: "2026-01-01", to: "2026-01-01", source: "meta", status: "NEW" },
      points: [
        {
          date: "hotel-1-day",
          leads: 1,
          inbound_messages: 1,
          outbound_messages: 0,
          confirmed_reservations: 0,
          checkins: 0,
          avg_response_time_seconds: 0,
        },
      ],
    };

    // Resolve primeiro a resposta do hotel-2
    resolves["hotel-2"](respHotel2);
    await screen.findByText("hotel-2-day");

    // Depois resolve uma resposta atrasada do hotel-1 (stale)
    resolves["hotel-1"](respHotel1);

    // A UI deve continuar com hotel-2-day
    expect(screen.getByTestId("timeseries-date").textContent).toBe("hotel-2-day");
  });
});

