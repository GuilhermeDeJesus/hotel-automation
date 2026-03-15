import { useState, useEffect } from "react";
import type { Room } from "../types/api";

interface RoomFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { number: string; room_type: string; daily_rate: number; max_guests: number }) => void;
  room?: Room | null;
  saving?: boolean;
}

const ROOM_TYPES = ["SINGLE", "DOUBLE", "SUITE"];

export default function RoomFormModal({
  isOpen,
  onClose,
  onSubmit,
  room,
  saving = false,
}: RoomFormModalProps) {
  const isEdit = !!room;
  const [number, setNumber] = useState(room?.number ?? "");
  const [roomType, setRoomType] = useState(room?.room_type ?? "DOUBLE");
  const [dailyRate, setDailyRate] = useState(room?.daily_rate?.toString() ?? "");
  const [maxGuests, setMaxGuests] = useState(room?.max_guests?.toString() ?? "2");

  useEffect(() => {
    if (room) {
      setNumber(room.number);
      setRoomType(room.room_type);
      setDailyRate(room.daily_rate.toString());
      setMaxGuests(room.max_guests.toString());
    } else {
      setNumber("");
      setRoomType("DOUBLE");
      setDailyRate("");
      setMaxGuests("2");
    }
  }, [room, isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const rate = parseFloat(dailyRate);
    const guests = parseInt(maxGuests, 10);
    if (isNaN(rate) || rate <= 0 || isNaN(guests) || guests <= 0) {
      return;
    }
    onSubmit({ number: number.trim(), room_type: roomType, daily_rate: rate, max_guests: guests });
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          padding: "1.5rem",
          maxWidth: 400,
          width: "90%",
          maxHeight: "90vh",
          overflow: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "1rem" }}>
          {isEdit ? "Editar quarto" : "Novo quarto"}
        </h2>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontWeight: 500, marginBottom: "0.375rem", fontSize: "0.875rem" }}>
              Número
            </label>
            <input
              type="text"
              value={number}
              onChange={(e) => setNumber(e.target.value)}
              placeholder="Ex: 101"
              disabled={isEdit}
              required
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                fontSize: "0.875rem",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                background: "var(--color-bg)",
                color: "var(--color-text)",
                opacity: isEdit ? 0.7 : 1,
              }}
            />
          </div>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontWeight: 500, marginBottom: "0.375rem", fontSize: "0.875rem" }}>
              Tipo
            </label>
            <select
              value={roomType}
              onChange={(e) => setRoomType(e.target.value)}
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                fontSize: "0.875rem",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                background: "var(--color-bg)",
                color: "var(--color-text)",
              }}
            >
              {ROOM_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontWeight: 500, marginBottom: "0.375rem", fontSize: "0.875rem" }}>
              Diária (R$)
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={dailyRate}
              onChange={(e) => setDailyRate(e.target.value)}
              placeholder="Ex: 220"
              required
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
          </div>
          <div style={{ marginBottom: "1.5rem" }}>
            <label style={{ display: "block", fontWeight: 500, marginBottom: "0.375rem", fontSize: "0.875rem" }}>
              Capacidade (hóspedes)
            </label>
            <input
              type="number"
              min="1"
              value={maxGuests}
              onChange={(e) => setMaxGuests(e.target.value)}
              placeholder="Ex: 2"
              required
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
          </div>
          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: "0.5rem 1rem",
                fontSize: "0.875rem",
                background: "transparent",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-text)",
                cursor: "pointer",
              }}
            >
              Cancelar
            </button>
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
              {saving ? "Salvando..." : isEdit ? "Salvar" : "Criar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
