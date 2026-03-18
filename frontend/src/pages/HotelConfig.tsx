import { useEffect, useRef, useState } from "react";
import { useHotelConfig } from "../hooks/useHotelConfig";
import { useRooms } from "../hooks/useRooms";
import {
  updateHotelConfig,
  createRoom,
  updateRoom,
  deleteRoom,
  uploadHotelMedia,
  fetchHotelMedia,
  deleteHotelMedia,
} from "../api/client";
import { useTenant } from "../contexts/TenantContext";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import { useToast } from "../contexts/ToastContext";
import RoomFormModal from "../components/RoomFormModal";
import TableScroll from "../components/ui/TableScroll";
import type { Room } from "../types/api";
import type { HotelMedia } from "../types/api";

type TabId = "overview" | "info" | "policies" | "amenities" | "payment" | "rooms" | "photos";

const TABS: { id: TabId; label: string }[] = [
  { id: "overview", label: "Visão geral" },
  { id: "info", label: "Informações gerais" },
  { id: "policies", label: "Regras e políticas" },
  { id: "amenities", label: "Comodidades" },
  { id: "payment", label: "Pagamento" },
  { id: "rooms", label: "Quartos" },
  { id: "photos", label: "Fotos" },
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
  const { hotelId } = useTenant();
  const { data, error, isLoading, refetch } = useHotelConfig();
  const { data: rooms, error: roomsError, isLoading: roomsLoading, refetch: refetchRooms } = useRooms();
  const { showToast } = useToast();
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [roomModalOpen, setRoomModalOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState<Room | null>(null);
  const [roomSaving, setRoomSaving] = useState(false);

  const [hotelPhotoFile, setHotelPhotoFile] = useState<File | null>(null);
  const [hotelPhotoCaption, setHotelPhotoCaption] = useState<string>("");
  const [roomPhotoNumber, setRoomPhotoNumber] = useState<string>("");
  const [roomPhotoFile, setRoomPhotoFile] = useState<File | null>(null);
  const [roomPhotoCaption, setRoomPhotoCaption] = useState<string>("");
  const [uploadingMedia, setUploadingMedia] = useState(false);

  const [hotelMediaItems, setHotelMediaItems] = useState<HotelMedia[]>([]);
  const [roomMediaByRoomNumber, setRoomMediaByRoomNumber] = useState<Record<string, HotelMedia[]>>({});
  const [loadingHotelMedia, setLoadingHotelMedia] = useState(false);
  const [loadingAllRoomMedia, setLoadingAllRoomMedia] = useState(false);
  const roomsSignatureRef = useRef<string>("");
  const [maxRoomPhotosToLoad, setMaxRoomPhotosToLoad] = useState<number>(10);
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
    pix_key: "",
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
        pix_key: data.pix_key ?? "",
        requires_payment_for_confirmation: data.requires_payment_for_confirmation ?? false,
        allows_reservation_without_payment: data.allows_reservation_without_payment ?? true,
      });
    }
  }, [data]);

  useEffect(() => {
    if (activeTab !== "photos" || !hotelId) return;

    loadHotelPhotos();

    if (roomsLoading) return;

    const signature = (rooms || []).map((r) => r.number).join("|");
    if (signature && signature !== roomsSignatureRef.current) {
      roomsSignatureRef.current = signature;
      loadAllRoomPhotos();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, hotelId, roomsLoading, rooms, maxRoomPhotosToLoad]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveError(null);
    setSaving(true);
    try {
      if (!hotelId) {
        throw new Error("Hotel não definido. Faça login novamente.");
      }
      await updateHotelConfig(hotelId, {
        name: form.name,
        address: form.address,
        contact_phone: form.contact_phone,
        checkin_time: form.checkin_time,
        checkout_time: form.checkout_time,
        cancellation_policy: form.cancellation_policy,
        pet_policy: form.pet_policy,
        child_policy: form.child_policy,
        amenities: form.amenities,
        pix_key: form.pix_key || undefined,
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
      if (!hotelId) {
        throw new Error("Hotel não definido. Faça login novamente.");
      }
      if (editingRoom) {
        await updateRoom(hotelId, editingRoom.number, {
          room_type: formData.room_type,
          daily_rate: formData.daily_rate,
          max_guests: formData.max_guests,
        });
        showToast("Quarto atualizado com sucesso.", "success");
      } else {
        await createRoom(hotelId, formData);
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
      if (!hotelId) {
        throw new Error("Hotel não definido. Faça login novamente.");
      }
      await deleteRoom(hotelId, roomNumber);
      showToast("Quarto desativado.", "success");
      refetchRooms();
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Erro ao desativar quarto", "error");
    }
  };

  const loadHotelPhotos = async () => {
    if (!hotelId) return;
    setLoadingHotelMedia(true);
    try {
      const res = await fetchHotelMedia(hotelId, { scope: "HOTEL", limit: 50 });
      setHotelMediaItems(Array.from(res.items ?? []));
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Erro ao carregar fotos do hotel", "error");
    } finally {
      setLoadingHotelMedia(false);
    }
  };

  const loadAllRoomPhotos = async () => {
    if (!hotelId) return;
    if (!rooms || rooms.length === 0) {
      setRoomMediaByRoomNumber({});
      return;
    }

    setLoadingAllRoomMedia(true);
    try {
      const sortedRooms = [...rooms].sort((a, b) => {
        const na = Number(a.number);
        const nb = Number(b.number);
        if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
        return a.number.localeCompare(b.number);
      });

      const results = await Promise.all(
        sortedRooms.map(async (r) => {
          try {
            const res = await fetchHotelMedia(hotelId, {
              scope: "ROOM",
              room_number: r.number,
              limit: Math.max(1, maxRoomPhotosToLoad),
            });
            const items = Array.from(res.items ?? []) as HotelMedia[];
            return [r.number, items] as const;
          } catch {
            return [r.number, [] as HotelMedia[]] as const;
          }
        })
      );

      const grouped: Record<string, HotelMedia[]> = {};
      for (const [roomNumber, items] of results) {
        grouped[roomNumber] = items;
      }
      setRoomMediaByRoomNumber(grouped);
    } finally {
      setLoadingAllRoomMedia(false);
    }
  };

  const handleDeletePhoto = async (mediaId: string) => {
    if (!hotelId) return;
    try {
      await deleteHotelMedia(hotelId, mediaId);
      showToast("Foto excluída com sucesso.", "success");
      // Recarrega listas
      await loadHotelPhotos();
      if (activeTab === "photos") {
        await loadAllRoomPhotos();
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Erro ao excluir foto", "error");
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
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
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
              <TableScroll>
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
              </TableScroll>
            )}
          </div>
        )}

        {activeTab === "photos" && (
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", maxWidth: 720 }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Fotos</h2>

            <div style={{ marginBottom: "2rem" }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.75rem" }}>Hotel (geral)</h3>

              <InputField
                label="Legenda (opcional)"
                value={hotelPhotoCaption}
                onChange={(v) => setHotelPhotoCaption(v)}
                placeholder="Ex: Recepção"
              />

              <div style={{ marginBottom: "1rem" }}>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(e) => {
                    const f = e.target.files?.[0] ?? null;
                    setHotelPhotoFile(f);
                  }}
                />
              </div>

              <button
                type="button"
                disabled={uploadingMedia}
                onClick={async () => {
                  try {
                    if (!hotelId) throw new Error("Hotel não definido.");
                    if (!hotelPhotoFile) throw new Error("Selecione uma imagem para enviar.");
                    setUploadingMedia(true);
                    await uploadHotelMedia(hotelId, {
                      scope: "HOTEL",
                      caption: hotelPhotoCaption || undefined,
                      file: hotelPhotoFile,
                    });
                    showToast("Foto do hotel enviada com sucesso.", "success");
                    setHotelPhotoFile(null);
                    setHotelPhotoCaption("");
                    await loadHotelPhotos();
                  } catch (e) {
                    showToast(e instanceof Error ? e.message : "Erro ao enviar foto", "error");
                  } finally {
                    setUploadingMedia(false);
                  }
                }}
                style={{
                  padding: "0.6rem 1rem",
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  background: "var(--color-accent)",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  color: "white",
                  cursor: "pointer",
                }}
              >
                Enviar foto do hotel
              </button>
              <div style={{ marginTop: "0.5rem", fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                Limite: 5MB. Formatos: jpg/png/webp.
              </div>
            </div>

            <div style={{ marginBottom: "1.5rem" }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.75rem" }}>
                Por quarto
              </h3>

              <InputField
                label="Número do quarto"
                value={roomPhotoNumber}
                onChange={(v) => setRoomPhotoNumber(v)}
                placeholder="Ex: 101"
              />

              <InputField
                label="Legenda (opcional)"
                value={roomPhotoCaption}
                onChange={(v) => setRoomPhotoCaption(v)}
                placeholder="Ex: Quarto 101 - cama"
              />

              <div style={{ marginBottom: "1rem" }}>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(e) => {
                    const f = e.target.files?.[0] ?? null;
                    setRoomPhotoFile(f);
                  }}
                />
              </div>

              <button
                type="button"
                disabled={uploadingMedia}
                onClick={async () => {
                  try {
                    if (!hotelId) throw new Error("Hotel não definido.");
                    const roomNumber = roomPhotoNumber.trim();
                    if (!roomNumber) throw new Error("Informe o número do quarto.");
                    if (!roomPhotoFile) throw new Error("Selecione uma imagem para enviar.");
                    setUploadingMedia(true);
                    await uploadHotelMedia(hotelId, {
                      scope: "ROOM",
                      room_number: roomNumber,
                      caption: roomPhotoCaption || undefined,
                      file: roomPhotoFile,
                    });
                    showToast("Foto do quarto enviada com sucesso.", "success");
                    setRoomPhotoFile(null);
                    setRoomPhotoCaption("");
                    setRoomPhotoNumber("");
                    await loadAllRoomPhotos();
                  } catch (e) {
                    showToast(e instanceof Error ? e.message : "Erro ao enviar foto", "error");
                  } finally {
                    setUploadingMedia(false);
                  }
                }}
                style={{
                  padding: "0.6rem 1rem",
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  background: "var(--color-accent)",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  color: "white",
                  cursor: "pointer",
                }}
              >
                Enviar foto do quarto
              </button>
            </div>

            <div style={{ marginTop: "2rem" }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.75rem" }}>
                Preview e exclusão
              </h3>

              <div style={{ marginBottom: "2rem" }}>
                <h4 style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.75rem" }}>
                  Hotel (geral)
                </h4>

                {loadingHotelMedia ? (
                  <div style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                    Carregando...
                  </div>
                ) : hotelMediaItems.length === 0 ? (
                  <div style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                    Nenhuma foto cadastrada para o hotel.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
                    {hotelMediaItems.map((m) => (
                      <div
                        key={m.id}
                        style={{
                          width: 150,
                          border: "1px solid var(--color-border)",
                          borderRadius: "var(--radius-sm)",
                          padding: "0.5rem",
                        }}
                      >
                        <img
                          src={`${apiBaseUrl}/saas/hotel/${encodeURIComponent(hotelId || "")}/media-public/${encodeURIComponent(m.id)}`}
                          alt={m.caption ?? "Foto do hotel"}
                          style={{
                            width: "100%",
                            height: 90,
                            objectFit: "cover",
                            borderRadius: "var(--radius-sm)",
                            display: "block",
                            marginBottom: "0.5rem",
                            background: "var(--color-bg)",
                          }}
                        />
                        <div style={{ fontSize: "0.8125rem", fontWeight: 600, marginBottom: "0.25rem" }}>
                          {m.caption ? m.caption : "Sem legenda"}
                        </div>
                        <button
                          type="button"
                          onClick={() => handleDeletePhoto(m.id)}
                          style={{
                            padding: "0.35rem 0.5rem",
                            fontSize: "0.8125rem",
                            fontWeight: 700,
                            background: "transparent",
                            border: "1px solid var(--color-error-muted)",
                            borderRadius: "var(--radius-sm)",
                            color: "var(--color-error)",
                            cursor: "pointer",
                            width: "100%",
                          }}
                        >
                          Excluir
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={{ marginBottom: "1.5rem" }}>
                <h4 style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.75rem" }}>
                  Por quarto
                </h4>

              <div style={{ marginBottom: "1rem", display: "flex", gap: "0.75rem", alignItems: "center" }}>
                <div style={{ minWidth: 260 }}>
                  <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginBottom: "0.25rem" }}>
                    Máximo fotos por quarto (auto-carregamento)
                  </div>
                  <input
                    type="number"
                    min={1}
                    value={maxRoomPhotosToLoad}
                    onChange={(e) => {
                      const v = Number(e.target.value);
                      setMaxRoomPhotosToLoad(Number.isFinite(v) && v > 0 ? v : 1);
                    }}
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
                {loadingAllRoomMedia && (
                  <div style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                    Carregando...
                  </div>
                )}
              </div>

                {roomsLoading ? (
                  <div style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                    Carregando quartos...
                  </div>
                ) : roomsError ? (
                  <div style={{ fontSize: "0.875rem", color: "var(--color-error)" }}>
                    {roomsError}
                  </div>
                ) : rooms.length === 0 ? (
                  <div style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                    Nenhum quarto cadastrado.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                    {[...rooms]
                      .sort((a, b) => {
                        const na = Number(a.number);
                        const nb = Number(b.number);
                        if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
                        return a.number.localeCompare(b.number);
                      })
                      .map((r) => {
                        const items = roomMediaByRoomNumber[r.number] || [];
                        return (
                          <div key={r.id} style={{ paddingBottom: "0.25rem" }}>
                            <div style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.75rem" }}>
                              Quarto {r.number}
                            </div>

                            {loadingAllRoomMedia ? (
                              <div style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                                Carregando fotos...
                              </div>
                            ) : items.length === 0 ? (
                              <div style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                                Sem fotos cadastradas.
                              </div>
                            ) : (
                              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
                                {items.map((m) => (
                                  <div
                                    key={m.id}
                                    style={{
                                      width: 150,
                                      border: "1px solid var(--color-border)",
                                      borderRadius: "var(--radius-sm)",
                                      padding: "0.5rem",
                                    }}
                                  >
                                    <img
                                      src={`${apiBaseUrl}/saas/hotel/${encodeURIComponent(hotelId || "")}/media-public/${encodeURIComponent(m.id)}`}
                                      alt={m.caption ?? "Foto do quarto"}
                                      style={{
                                        width: "100%",
                                        height: 90,
                                        objectFit: "cover",
                                        borderRadius: "var(--radius-sm)",
                                        display: "block",
                                        marginBottom: "0.5rem",
                                        background: "var(--color-bg)",
                                      }}
                                    />
                                    <div style={{ fontSize: "0.8125rem", fontWeight: 600, marginBottom: "0.25rem" }}>
                                      {m.caption ? m.caption : "Sem legenda"}
                                    </div>
                                    <button
                                      type="button"
                                      onClick={() => handleDeletePhoto(m.id)}
                                      style={{
                                        padding: "0.35rem 0.5rem",
                                        fontSize: "0.8125rem",
                                        fontWeight: 700,
                                        background: "transparent",
                                        border: "1px solid var(--color-error-muted)",
                                        borderRadius: "var(--radius-sm)",
                                        color: "var(--color-error)",
                                        cursor: "pointer",
                                        width: "100%",
                                      }}
                                    >
                                      Excluir
                                    </button>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "payment" && (
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", maxWidth: 560 }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Pagamento</h2>
            <InputField
              label="Chave PIX"
              value={form.pix_key}
              onChange={(v) => setForm((f) => ({ ...f, pix_key: v }))}
              placeholder="ex: chavepix@hotel.com"
              hint="Essa chave será usada pelo bot nas mensagens de pagamento por PIX."
            />
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
