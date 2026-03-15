import { useState, useEffect } from "react";
import { useHotelConfig, validateConfig } from "../api/hotelConfig";

interface HotelSettingsProps {
  hotelId: string;
}

export default function HotelSettings({ hotelId }: HotelSettingsProps) {
  const { config, loading, error, updateConfig } = useHotelConfig(hotelId);
  const [activeTab, setActiveTab] = useState("basic");
  const [formData, setFormData] = useState<any>({});
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (config) {
      setFormData({
        hotel_name: config.hotel_name,
        hotel_description: config.hotel_description,
        contact_email: config.contact_email,
        contact_phone: config.contact_phone,
        default_checkin_time: config.default_checkin_time,
        default_checkout_time: config.default_checkout_time,
        early_checkin_fee: config.early_checkin_fee,
        late_checkout_fee: config.late_checkout_fee,
        cancellation_policy_hours: config.cancellation_policy_hours,
        cancellation_fee_percentage: config.cancellation_fee_percentage,
        free_cancellation_hours: config.free_cancellation_hours,
        requires_payment_for_confirmation: config.requires_payment_for_confirmation,
        payment_methods: config.payment_methods,
        payment_deadline_hours: config.payment_deadline_hours,
        max_guests_per_room: config.max_guests_per_room,
        allows_extra_beds: config.allows_extra_beds,
        extra_bed_fee: config.extra_bed_fee,
        child_policy: config.child_policy,
        pet_policy: config.pet_policy,
        smoking_policy: config.smoking_policy,
        breakfast_included: config.breakfast_included,
        breakfast_price: config.breakfast_price,
        room_service_available: config.room_service_available,
        room_service_hours: config.room_service_hours,
        auto_send_confirmation: config.auto_send_confirmation,
        auto_send_reminder: config.auto_send_reminder,
        reminder_hours_before: config.reminder_hours_before,
        whatsapp_enabled: config.whatsapp_enabled,
        whatsapp_number: config.whatsapp_number,
        whatsapp_business_hours: config.whatsapp_business_hours,
        currency: config.currency,
        language: config.language,
        timezone: config.timezone,
        auto_backup_enabled: config.auto_backup_enabled,
        backup_frequency_hours: config.backup_frequency_hours,
        backup_retention_days: config.backup_retention_days,
      });
    }
  }, [config]);

  const handleInputChange = (field: string, value: any) => {
    setFormData((prev: any) => ({ ...prev, [field]: value }));
    setValidationErrors([]);
    setSaveSuccess(false);
  };

  const handleSave = async () => {
    const validation = validateConfig(formData);
    if (!validation.isValid) {
      setValidationErrors(validation.errors);
      return;
    }

    setIsSaving(true);
    try {
      await updateConfig(formData);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setValidationErrors([err.message || "Erro ao salvar configurações"]);
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-loading">
        <div className="spinner"></div>
        <p>Carregando configurações...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="settings-error">
        <p>Erro ao carregar configurações: {error}</p>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="settings-empty">
        <p>Nenhuma configuração disponível</p>
      </div>
    );
  }

  return (
    <div className="hotel-settings">
      <div className="settings-header">
        <h1>Configurações do Hotel</h1>
        <p>{config.hotel_name}</p>
      </div>

      {/* Tabs */}
      <div className="settings-tabs">
        <button
          className={`tab ${activeTab === "basic" ? "active" : ""}`}
          onClick={() => setActiveTab("basic")}
        >
          Informações Básicas
        </button>
        <button
          className={`tab ${activeTab === "operational" ? "active" : ""}`}
          onClick={() => setActiveTab("operational")}
        >
          Operacionais
        </button>
        <button
          className={`tab ${activeTab === "policies" ? "active" : ""}`}
          onClick={() => setActiveTab("policies")}
        >
          Políticas
        </button>
        <button
          className={`tab ${activeTab === "services" ? "active" : ""}`}
          onClick={() => setActiveTab("services")}
        >
          Serviços
        </button>
        <button
          className={`tab ${activeTab === "communications" ? "active" : ""}`}
          onClick={() => setActiveTab("communications")}
        >
          Comunicações
        </button>
        <button
          className={`tab ${activeTab === "backup" ? "active" : ""}`}
          onClick={() => setActiveTab("backup")}
        >
          Backup
        </button>
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="validation-errors">
          <h4>Erros de Validação:</h4>
          <ul>
            {validationErrors.map((error: string, index: number) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Success Message */}
      {saveSuccess && (
        <div className="success-message">
          Configurações salvas com sucesso!
        </div>
      )}

      {/* Form Content */}
      <div className="settings-content">
        {activeTab === "basic" && (
          <div className="tab-content">
            <div className="form-group">
              <label>Nome do Hotel</label>
              <input
                type="text"
                value={formData.hotel_name || ""}
                onChange={(e) => handleInputChange("hotel_name", e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Descrição</label>
              <textarea
                value={formData.hotel_description || ""}
                onChange={(e) => handleInputChange("hotel_description", e.target.value)}
                rows={3}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Email de Contato</label>
                <input
                  type="email"
                  value={formData.contact_email || ""}
                  onChange={(e) => handleInputChange("contact_email", e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Telefone de Contato</label>
                <input
                  type="tel"
                  value={formData.contact_phone || ""}
                  onChange={(e) => handleInputChange("contact_phone", e.target.value)}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Moeda</label>
                <select
                  value={formData.currency || "BRL"}
                  onChange={(e) => handleInputChange("currency", e.target.value)}
                >
                  <option value="BRL">BRL - Real Brasileiro</option>
                  <option value="USD">USD - Dólar Americano</option>
                  <option value="EUR">EUR - Euro</option>
                </select>
              </div>

              <div className="form-group">
                <label>Idioma</label>
                <select
                  value={formData.language || "pt-BR"}
                  onChange={(e) => handleInputChange("language", e.target.value)}
                >
                  <option value="pt-BR">Português (Brasil)</option>
                  <option value="en-US">English (US)</option>
                  <option value="es-ES">Español</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>Fuso Horário</label>
              <select
                value={formData.timezone || "America/Sao_Paulo"}
                onChange={(e) => handleInputChange("timezone", e.target.value)}
              >
                <option value="America/Sao_Paulo">America/Sao_Paulo</option>
                <option value="America/New_York">America/New_York</option>
                <option value="Europe/London">Europe/London</option>
                <option value="Asia/Tokyo">Asia/Tokyo</option>
              </select>
            </div>
          </div>
        )}

        {activeTab === "operational" && (
          <div className="tab-content">
            <div className="form-row">
              <div className="form-group">
                <label>Horário de Check-in</label>
                <input
                  type="time"
                  value={formData.default_checkin_time || "14:00"}
                  onChange={(e) => handleInputChange("default_checkin_time", e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Horário de Check-out</label>
                <input
                  type="time"
                  value={formData.default_checkout_time || "12:00"}
                  onChange={(e) => handleInputChange("default_checkout_time", e.target.value)}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Taxa de Check-in Antecipado</label>
                <input
                  type="number"
                  value={formData.early_checkin_fee || 0}
                  onChange={(e) => handleInputChange("early_checkin_fee", parseFloat(e.target.value))}
                  min="0"
                  step="0.01"
                />
              </div>

              <div className="form-group">
                <label>Taxa de Check-out Tardio</label>
                <input
                  type="number"
                  value={formData.late_checkout_fee || 0}
                  onChange={(e) => handleInputChange("late_checkout_fee", parseFloat(e.target.value))}
                  min="0"
                  step="0.01"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Máximo de Hóspedes por Quarto</label>
                <input
                  type="number"
                  value={formData.max_guests_per_room || 4}
                  onChange={(e) => handleInputChange("max_guests_per_room", parseInt(e.target.value))}
                  min="1"
                  max="10"
                />
              </div>

              <div className="form-group">
                <label>Permite Camas Extras?</label>
                <select
                  value={formData.allows_extra_beds ? "true" : "false"}
                  onChange={(e) => handleInputChange("allows_extra_beds", e.target.value === "true")}
                >
                  <option value="true">Sim</option>
                  <option value="false">Não</option>
                </select>
              </div>
            </div>

            {formData.allows_extra_beds && (
              <div className="form-group">
                <label>Taxa de Cama Extra</label>
                <input
                  type="number"
                  value={formData.extra_bed_fee || 50}
                  onChange={(e) => handleInputChange("extra_bed_fee", parseFloat(e.target.value))}
                  min="0"
                  step="0.01"
                />
              </div>
            )}

            <div className="form-group">
              <label>Requer Pagamento para Confirmação?</label>
              <select
                value={formData.requires_payment_for_confirmation ? "true" : "false"}
                onChange={(e) => handleInputChange("requires_payment_for_confirmation", e.target.value === "true")}
              >
                <option value="true">Sim</option>
                <option value="false">Não</option>
              </select>
            </div>

            {formData.requires_payment_for_confirmation && (
              <div className="form-group">
                <label>Prazo de Pagamento (horas)</label>
                <input
                  type="number"
                  value={formData.payment_deadline_hours || 24}
                  onChange={(e) => handleInputChange("payment_deadline_hours", parseInt(e.target.value))}
                  min="1"
                  max="168"
                />
              </div>
            )}
          </div>
        )}

        {activeTab === "policies" && (
          <div className="tab-content">
            <div className="form-group">
              <label>Política de Cancelamento (horas)</label>
              <input
                type="number"
                value={formData.cancellation_policy_hours || 24}
                onChange={(e) => handleInputChange("cancellation_policy_hours", parseInt(e.target.value))}
                min="0"
                max="720"
              />
              <small>Horas antes do check-in para cancelamento gratuito</small>
            </div>

            <div className="form-group">
              <label>Percentual de Taxa de Cancelamento</label>
              <input
                type="number"
                value={formData.cancellation_fee_percentage || 0}
                onChange={(e) => handleInputChange("cancellation_fee_percentage", parseFloat(e.target.value))}
                min="0"
                max="100"
                step="0.1"
              />
              <small>Percentual cobrado em cancelamentos fora do prazo</small>
            </div>

            <div className="form-group">
              <label>Cancelamento Gratuito (horas)</label>
              <input
                type="number"
                value={formData.free_cancellation_hours || 24}
                onChange={(e) => handleInputChange("free_cancellation_hours", parseInt(e.target.value))}
                min="0"
                max="720"
              />
              <small>Horas antes do check-in para cancelamento gratuito</small>
            </div>

            <div className="form-group">
              <label>Política de Fumantes</label>
              <select
                value={formData.smoking_policy || "NON_SMOKING"}
                onChange={(e) => handleInputChange("smoking_policy", e.target.value)}
              >
                <option value="NON_SMOKING">Não Fumantes</option>
                <option value="SMOKING">Fumantes</option>
                <option value="MIXED">Misto</option>
              </select>
            </div>

            <div className="form-group">
              <label>Política de Crianças</label>
              <textarea
                value={formData.child_policy || ""}
                onChange={(e) => handleInputChange("child_policy", e.target.value)}
                rows={3}
                placeholder="Descreva a política para crianças..."
              />
            </div>

            <div className="form-group">
              <label>Política de Animais de Estimação</label>
              <textarea
                value={formData.pet_policy || ""}
                onChange={(e) => handleInputChange("pet_policy", e.target.value)}
                rows={3}
                placeholder="Descreva a política para animais de estimação..."
              />
            </div>
          </div>
        )}

        {activeTab === "services" && (
          <div className="tab-content">
            <div className="form-group">
              <label>Café da Manhã Incluído?</label>
              <select
                value={formData.breakfast_included ? "true" : "false"}
                onChange={(e) => handleInputChange("breakfast_included", e.target.value === "true")}
              >
                <option value="true">Sim</option>
                <option value="false">Não</option>
              </select>
            </div>

            {!formData.breakfast_included && (
              <div className="form-group">
                <label>Preço do Café da Manhã</label>
                <input
                  type="number"
                  value={formData.breakfast_price || 0}
                  onChange={(e) => handleInputChange("breakfast_price", parseFloat(e.target.value))}
                  min="0"
                  step="0.01"
                />
              </div>
            )}

            <div className="form-group">
              <label>Serviço de Quarto Disponível?</label>
              <select
                value={formData.room_service_available ? "true" : "false"}
                onChange={(e) => handleInputChange("room_service_available", e.target.value === "true")}
              >
                <option value="true">Sim</option>
                <option value="false">Não</option>
              </select>
            </div>

            {formData.room_service_available && (
              <div className="form-row">
                <div className="form-group">
                  <label>Horário de Início</label>
                  <input
                    type="time"
                    value={formData.room_service_hours?.start || "06:00"}
                    onChange={(e) => handleInputChange("room_service_hours", {
                      ...formData.room_service_hours,
                      start: e.target.value
                    })}
                  />
                </div>

                <div className="form-group">
                  <label>Horário de Término</label>
                  <input
                    type="time"
                    value={formData.room_service_hours?.end || "23:00"}
                    onChange={(e) => handleInputChange("room_service_hours", {
                      ...formData.room_service_hours,
                      end: e.target.value
                    })}
                  />
                </div>
              </div>
            )}

            <div className="form-group">
              <label>WhatsApp Habilitado?</label>
              <select
                value={formData.whatsapp_enabled ? "true" : "false"}
                onChange={(e) => handleInputChange("whatsapp_enabled", e.target.value === "true")}
              >
                <option value="true">Sim</option>
                <option value="false">Não</option>
              </select>
            </div>

            {formData.whatsapp_enabled && (
              <>
                <div className="form-group">
                  <label>Número do WhatsApp</label>
                  <input
                    type="tel"
                    value={formData.whatsapp_number || ""}
                    onChange={(e) => handleInputChange("whatsapp_number", e.target.value)}
                    placeholder="+55 21 99999-9999"
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Horário de Início</label>
                    <input
                      type="time"
                      value={formData.whatsapp_business_hours?.start || "08:00"}
                      onChange={(e) => handleInputChange("whatsapp_business_hours", {
                        ...formData.whatsapp_business_hours,
                        start: e.target.value
                      })}
                    />
                  </div>

                  <div className="form-group">
                    <label>Horário de Término</label>
                    <input
                      type="time"
                      value={formData.whatsapp_business_hours?.end || "22:00"}
                      onChange={(e) => handleInputChange("whatsapp_business_hours", {
                        ...formData.whatsapp_business_hours,
                        end: e.target.value
                      })}
                    />
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === "communications" && (
          <div className="tab-content">
            <div className="form-group">
              <label>Enviar Confirmação Automática?</label>
              <select
                value={formData.auto_send_confirmation ? "true" : "false"}
                onChange={(e) => handleInputChange("auto_send_confirmation", e.target.value === "true")}
              >
                <option value="true">Sim</option>
                <option value="false">Não</option>
              </select>
            </div>

            <div className="form-group">
              <label>Enviar Lembrete Automático?</label>
              <select
                value={formData.auto_send_reminder ? "true" : "false"}
                onChange={(e) => handleInputChange("auto_send_reminder", e.target.value === "true")}
              >
                <option value="true">Sim</option>
                <option value="false">Não</option>
              </select>
            </div>

            {formData.auto_send_reminder && (
              <div className="form-group">
                <label>Horas Antes do Check-in para Lembrete</label>
                <input
                  type="number"
                  value={formData.reminder_hours_before || 24}
                  onChange={(e) => handleInputChange("reminder_hours_before", parseInt(e.target.value))}
                  min="1"
                  max="168"
                />
              </div>
            )}
          </div>
        )}

        {activeTab === "backup" && (
          <div className="tab-content">
            <div className="form-group">
              <label>Backup Automático Habilitado?</label>
              <select
                value={formData.auto_backup_enabled ? "true" : "false"}
                onChange={(e) => handleInputChange("auto_backup_enabled", e.target.value === "true")}
              >
                <option value="true">Sim</option>
                <option value="false">Não</option>
              </select>
            </div>

            {formData.auto_backup_enabled && (
              <>
                <div className="form-group">
                  <label>Frequência de Backup (horas)</label>
                  <input
                    type="number"
                    value={formData.backup_frequency_hours || 24}
                    onChange={(e) => handleInputChange("backup_frequency_hours", parseInt(e.target.value))}
                    min="1"
                    max="168"
                  />
                </div>

                <div className="form-group">
                  <label>Retenção de Backup (dias)</label>
                  <input
                    type="number"
                    value={formData.backup_retention_days || 30}
                    onChange={(e) => handleInputChange("backup_retention_days", parseInt(e.target.value))}
                    min="1"
                    max="365"
                  />
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Save Button */}
      <div className="settings-actions">
        <button
          className="save-button"
          onClick={handleSave}
          disabled={isSaving}
        >
          {isSaving ? "Salvando..." : "Salvar Configurações"}
        </button>
      </div>
    </div>
  );
}

// CSS styles
