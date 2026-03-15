import { useState, useEffect } from "react";
import { useHotelConfig } from "../hooks/useHotelConfig";
import { useRooms } from "../hooks/useRooms";
import {
  updateHotelConfig,
  createRoom,
  updateRoom,
  deleteRoom,
} from "../api/client";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import { useToast } from "../contexts/ToastContext";
import RoomFormModal from "../components/RoomFormModal";
import type { Room } from "../types/api";

type TabId = "overview" | "info" | "policies" | "amenities" | "payment" | "rooms";

const TABS: { id: TabId; label: string }[] = [
  { id: "overview", label: "Visão geral" },
  { id: "info", label: "Informações gerais" },
  { id: "policies", label: "Regras e políticas" },
  { id: "amenities", label: "Comodidades" },
  { id: "payment", label: "Pagamento" },
  { id: "rooms", label: "Quartos" },
];

function InputField({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  hint?: string;
}) {
  return (
    <div style={{ marginBottom: "1rem" }}>
      <label style={{ display: "block", fontWeight: 500, marginBottom: "0.375rem", fontSize: "0.875rem" }}>
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          width: "100%",
          padding: "0.5rem 0.75rem",
          fontSize: "0.875rem",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-sm)",
          background: "var(--color-bg)",
          color: "var(--color-text)",
        }}
      />
      {hint && (
        <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
          {hint}
        </div>
      )}
    </div>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
  placeholder,
  hint,
  rows = 3,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  hint?: string;
  rows?: number;
}) {
  return (
    <div style={{ marginBottom: "1rem" }}>
      <label style={{ display: "block", fontWeight: 500, marginBottom: "0.375rem", fontSize: "0.875rem" }}>
        {label}
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        style={{
          width: "100%",
          padding: "0.5rem 0.75rem",
          fontSize: "0.875rem",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-sm)",
          background: "var(--color-bg)",
          color: "var(--color-text)",
          resize: "vertical",
        }}
      />
      {hint && (
        <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
          {hint}
        </div>
      )}
    </div>
  );
}

export default function HotelConfig() {
  const { data, error, isLoading, refetch } = useHotelConfig();
  const { data: rooms, error: roomsError, isLoading: roomsLoading, refetch: refetchRooms } = useRooms();
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [roomModalOpen, setRoomModalOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState<Room | null>(null);
  const [roomSaving, setRoomSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    address: "",
    contact_phone: "",
    checkin_time: "",
    checkout_time: "",
    cancellation_policy: "",
    pet_policy: "",
    child_policy: "",
    amenities: "",
    requires_payment_for_confirmation: false,
    allows_reservation_without_payment: true,
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setForm({
        name: data.name ?? "",
        address: data.address ?? "",
        contact_phone: data.contact_phone ?? "",
        checkin_time: data.checkin_time ?? "14:00",
        checkout_time: data.checkout_time ?? "12:00",
        cancellation_policy: data.cancellation_policy ?? "",
        pet_policy: data.pet_policy ?? "",
        child_policy: data.child_policy ?? "",
        amenities: data.amenities ?? "",
        requires_payment_for_confirmation: data.requires_payment_for_confirmation ?? false,
        allows_reservation_without_payment: data.allows_reservation_without_payment ?? true,
      });
    }
  }, [data]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveError(null);
    setSaving(true);
    try {
      await updateHotelConfig({
        name: form.name,
        address: form.address,
        contact_phone: form.contact_phone,
        checkin_time: form.checkin_time,
        checkout_time: form.checkout_time,
        cancellation_policy: form.cancellation_policy,
        pet_policy: form.pet_policy,
        child_policy: form.child_policy,
        amenities: form.amenities,
        requires_payment_for_confirmation: form.requires_payment_for_confirmation,
        allows_reservation_without_payment: form.allows_reservation_without_payment,
      });
      showToast("Configuração salva com sucesso.", "success");
      refetch();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro ao salvar";
      setSaveError(msg);
      showToast(msg, "error");
    } finally {
      setSaving(false);
    }
  };

  const handleRoomSubmit = async (formData: {
    number: string;
    room_type: string;
    daily_rate: number;
    max_guests: number;
  }) => {
    setRoomSaving(true);
    try {
      if (editingRoom) {
        await updateRoom(editingRoom.number, {
          room_type: formData.room_type,
          daily_rate: formData.daily_rate,
          max_guests: formData.max_guests,
        });
        showToast("Quarto atualizado com sucesso.", "success");
      } else {
        await createRoom(formData);
        showToast("Quarto criado com sucesso.", "success");
      }
      setRoomModalOpen(false);
      setEditingRoom(null);
      refetchRooms();
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Erro ao salvar quarto", "error");
    } finally {
      setRoomSaving(false);
    }
  };

  const handleDeleteRoom = async (roomNumber: string) => {
    if (!window.confirm(`Desativar o quarto ${roomNumber}? Ele não aparecerá mais para novas reservas.`)) {
      return;
    }
    try {
      await deleteRoom(roomNumber);
      showToast("Quarto desativado.", "success");
      refetchRooms();
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Erro ao desativar quarto", "error");
    }
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Configuração do hotel</h1>
        <LoadingState variant="chart" message="Carregando configuração..." />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 className="page-title">Configuração do hotel</h1>
        <ErrorState message={`Erro ao carregar configuração: ${error}`} onRetry={refetch} />
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div>
      <h1 className="page-title">Configuração do hotel</h1>
      <p
        style={{
          margin: "-0.75rem 0 1.5rem 0",
          color: "var(--color-text-muted)",
          fontSize: "0.9375rem",
        }}
      >
        Edite as informações gerais, regras, comodidades e políticas do hotel. O bot de WhatsApp usa
        essas configurações nas conversas com os hóspedes.
      </p>

      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
          borderBottom: "1px solid var(--color-border)",
          paddingBottom: "0.5rem",
        }}
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "0.875rem",
              fontWeight: 500,
              background: activeTab === tab.id ? "var(--color-accent)" : "transparent",
              color: activeTab === tab.id ? "white" : "var(--color-text-muted)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        {saveError && (
          <div
            style={{
              padding: "0.75rem 1rem",
              marginBottom: "1rem",
              background: "var(--color-error-muted)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-error)",
              fontSize: "0.875rem",
            }}
          >
            {saveError}
          </div>
        )}

        {activeTab === "overview" && (
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", maxWidth: 560 }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Visão geral</h2>
            <InputField
              label="Nome do hotel"
              value={form.name}
              onChange={(v) => setForm((f) => ({ ...f, name: v }))}
              placeholder="Ex: Hotel Automation"
            />
          </div>
        )}

        {activeTab === "info" && (
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", maxWidth: 560 }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>
              Informações gerais
            </h2>
            <InputField
              label="Endereço"
              value={form.address}
              onChange={(v) => setForm((f) => ({ ...f, address: v }))}
              placeholder="Ex: Avenida Central, 123, Brasília - DF"
            />
            <InputField
              label="Telefone de contato"
              value={form.contact_phone}
              onChange={(v) => setForm((f) => ({ ...f, contact_phone: v }))}
              placeholder="Ex: +55 61 99999-0000"
            />
          </div>
        )}

        {activeTab === "policies" && (
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", maxWidth: 560 }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>
              Regras e políticas
            </h2>
            <InputField
              label="Horário de check-in"
              value={form.checkin_time}
              onChange={(v) => setForm((f) => ({ ...f, checkin_time: v }))}
              placeholder="Ex: 14:00"
              hint="Formato HH:MM"
            />
            <InputField
              label="Horário de check-out"
              value={form.checkout_time}
              onChange={(v) => setForm((f) => ({ ...f, checkout_time: v }))}
              placeholder="Ex: 12:00"
              hint="Formato HH:MM"
            />
            <TextAreaField
              label="Política de cancelamento"
              value={form.cancellation_policy}
              onChange={(v) => setForm((f) => ({ ...f, cancellation_policy: v }))}
              placeholder="Ex: Cancelamento grátis até 24h antes do check-in"
            />
            <TextAreaField
              label="Política de pets"
              value={form.pet_policy}
              onChange={(v) => setForm((f) => ({ ...f, pet_policy: v }))}
              placeholder="Ex: Não aceitamos pets"
            />
            <TextAreaField
              label="Política de crianças"
              value={form.child_policy}
              onChange={(v) => setForm((f) => ({ ...f, child_policy: v }))}
              placeholder="Ex: Crianças até 6 anos não pagam"
            />
          </div>
        )}

        {activeTab === "amenities" && (
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", maxWidth: 560 }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Comodidades</h2>
            <TextAreaField
              label="Comodidades e serviços"
              value={form.amenities}
              onChange={(v) => setForm((f) => ({ ...f, amenities: v }))}
              placeholder="Ex: Wi-Fi, Piscina, Academia, Restaurante, Estacionamento"
              hint="Separe por vírgula. Ex: Wi-Fi, Piscina, Academia"
            />
          </div>
        )}

        {activeTab === "rooms" && (
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", overflowX: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>Quartos</h2>
              <button
                type="button"
                onClick={() => {
                  setEditingRoom(null);
                  setRoomModalOpen(true);
                }}
                style={{
                  padding: "0.5rem 1rem",
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  background: "var(--color-accent)",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  color: "white",
                  cursor: "pointer",
                }}
              >
                Novo quarto
              </button>
            </div>
            {roomsLoading ? (
              <LoadingState variant="chart" message="Carregando quartos..." />
            ) : roomsError ? (
              <div style={{ color: "var(--color-error)", fontSize: "0.875rem" }}>{roomsError}</div>
            ) : rooms.length === 0 ? (
              <div style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
                Nenhum quarto cadastrado. Clique em "Novo quarto" para adicionar.
              </div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left" }}>
                    <th style={{ padding: "0.5rem 0.75rem", fontWeight: 600 }}>Número</th>
                    <th style={{ padding: "0.5rem 0.75rem", fontWeight: 600 }}>Tipo</th>
                    <th style={{ padding: "0.5rem 0.75rem", fontWeight: 600 }}>Diária</th>
                    <th style={{ padding: "0.5rem 0.75rem", fontWeight: 600 }}>Capacidade</th>
                    <th style={{ padding: "0.5rem 0.75rem", fontWeight: 600 }}>Status</th>
                    <th style={{ padding: "0.5rem 0.75rem", fontWeight: 600 }}>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {rooms.map((r) => (
                    <tr key={r.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                      <td style={{ padding: "0.5rem 0.75rem" }}>{r.number}</td>
                      <td style={{ padding: "0.5rem 0.75rem" }}>{r.room_type}</td>
                      <td style={{ padding: "0.5rem 0.75rem" }}>
                        R$ {r.daily_rate.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                      </td>
                      <td style={{ padding: "0.5rem 0.75rem" }}>{r.max_guests}</td>
                      <td style={{ padding: "0.5rem 0.75rem" }}>{r.status}</td>
                      <td style={{ padding: "0.5rem 0.75rem" }}>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingRoom(r);
                            setRoomModalOpen(true);
                          }}
                          style={{
                            padding: "0.25rem 0.5rem",
                            fontSize: "0.8125rem",
                            marginRight: "0.5rem",
                            background: "transparent",
                            border: "1px solid var(--color-border)",
                            borderRadius: "var(--radius-sm)",
                            color: "var(--color-text)",
                            cursor: "pointer",
                          }}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteRoom(r.number)}
                          style={{
                            padding: "0.25rem 0.5rem",
                            fontSize: "0.8125rem",
                            background: "transparent",
                            border: "1px solid var(--color-error-muted)",
                            borderRadius: "var(--radius-sm)",
                            color: "var(--color-error)",
                            cursor: "pointer",
                          }}
                        >
                          Desativar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === "payment" && (
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", maxWidth: 560 }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Pagamento</h2>
            <div style={{ marginBottom: "1.5rem" }}>
              <label
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "0.75rem",
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={form.requires_payment_for_confirmation}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, requires_payment_for_confirmation: e.target.checked }))
                  }
                  style={{ marginTop: "0.25rem" }}
                />
                <div>
                  <div style={{ fontWeight: 500, marginBottom: "0.25rem" }}>
                    Exigir pagamento para confirmação
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                    Se ativo, a reserva só pode ser confirmada após pagamento aprovado.
                  </div>
                </div>
              </label>
            </div>
            <div style={{ marginBottom: "1.5rem" }}>
              <label
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "0.75rem",
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={form.allows_reservation_without_payment}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      allows_reservation_without_payment: e.target.checked,
                    }))
                  }
                  style={{ marginTop: "0.25rem" }}
                />
                <div>
                  <div style={{ fontWeight: 500, marginBottom: "0.25rem" }}>
                    Permitir reserva sem pagamento imediato
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                    Se ativo, o bot oferece as duas opções: "Pagar agora" e "Confirmar sem pagamento".
                  </div>
                </div>
              </label>
            </div>
          </div>
        )}

        {activeTab !== "rooms" && (
          <button
            type="submit"
            disabled={saving}
            style={{
              padding: "0.5rem 1.25rem",
              fontSize: "0.875rem",
              fontWeight: 600,
              background: "var(--color-accent)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              color: "white",
              cursor: saving ? "not-allowed" : "pointer",
              opacity: saving ? 0.7 : 1,
            }}
          >
            {saving ? "Salvando..." : "Salvar alterações"}
          </button>
        )}
      </form>

      <RoomFormModal
        isOpen={roomModalOpen}
        onClose={() => {
          setRoomModalOpen(false);
          setEditingRoom(null);
        }}
        onSubmit={handleRoomSubmit}
        room={editingRoom}
        saving={roomSaving}
      />
    </div>
  );
}
