// File: www/climate-react-card/climate-react-card.ts
import { css, html, LitElement, TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import { HomeAssistant, hasConfigOrEntityChanged } from "custom-card-helpers";

@customElement("climate-react-card")
export class ClimateReactCard extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) config: any;

  static getConfigElement() {
    return document.createElement("hui-generic-entity-row");
  }

  static getStubConfig() {
    return { title: "Climate React" };
  }

  setConfig(config: any) {
    if (!config) throw new Error("Invalid configuration");
    this.config = config;
  }

  shouldUpdate(changedProps: Map<string, unknown>): boolean {
    return hasConfigOrEntityChanged(this, changedProps, false);
  }

  render(): TemplateResult {
    if (!this.hass || !this.config) return html``;

    const getState = (key: string) => this.hass.states[this.config[key]];
    const temp = parseFloat(getState("temperature_sensor")?.state || "0");
    const enabledState = getState("enabled_entity")?.state === "on";

    const modes: string[] = this.config.modes || [];
    const fans: string[] = this.config.fans || [];

    return html`
      <ha-card header="${this.config.title || "Climate React"}">
        <div class="info">
          <div class="temp">${temp.toFixed(1)}°</div>
          <div>${enabledState ? "Active" : "Off"}</div>
        </div>
        <div class="controls">
          <button @click=${this._toggleEnabled}>
            ${enabledState ? "Desligar" : "Ligar"}
          </button>

          <div class="range">
            <label for="min-temp">Min:</label>
            <input
              id="min-temp"
              type="number"
              step="0.1"
              min="10"
              max="35"
              .value=${getState("min_temp_entity")?.state ?? "20"}
              @change=${(e: Event) =>
                this._updateNumber("min_temp_entity", (e.target as HTMLInputElement).value)}
            />

            <label for="max-temp">Max:</label>
            <input
              id="max-temp"
              type="number"
              step="0.1"
              min="10"
              max="35"
              .value=${getState("max_temp_entity")?.state ?? "26"}
              @change=${(e: Event) =>
                this._updateNumber("max_temp_entity", (e.target as HTMLInputElement).value)}
            />
          </div>

          <div class="setpoint">
            <label for="setpoint">Setpoint:</label>
            <input
              id="setpoint"
              type="number"
              step="1"
              min="10"
              max="35"
              .value=${getState("setpoint_entity")?.state ?? "24"}
              @change=${(e: Event) =>
                this._updateNumber("setpoint_entity", (e.target as HTMLInputElement).value)}
            />
          </div>

          ${modes.length
            ? html`
                <div class="mode-select">
                  <label for="mode">Mode:</label>
                  <select
                    id="mode"
                    .value=${getState("mode_entity")?.state || modes[0]}
                    @change=${(e: Event) =>
                      this._updateSelect("mode_entity", (e.target as HTMLSelectElement).value)}
                  >
                    ${modes.map(
                      (mode) => html`<option value="${mode}">${mode}</option>`
                    )}
                  </select>
                </div>
              `
            : ""}

          ${fans.length
            ? html`
                <div class="fan-select">
                  <label for="fan">Fan:</label>
                  <select
                    id="fan"
                    .value=${getState("fan_entity")?.state || fans[0]}
                    @change=${(e: Event) =>
                      this._updateSelect("fan_entity", (e.target as HTMLSelectElement).value)}
                  >
                    ${fans.map(
                      (fan) => html`<option value="${fan}">${fan}</option>`
                    )}
                  </select>
                </div>
              `
            : ""}
        </div>
      </ha-card>
    `;
  }

  private async _updateNumber(entityKey: string, value: string) {
    const entityId = this.config[entityKey];
    if (!entityId) return;
    const numericValue = parseFloat(value);
    if (isNaN(numericValue)) return;

    await this.hass.callService("input_number", "set_value", {
      entity_id: entityId,
      value: numericValue,
    });
  }

  private async _updateSelect(entityKey: string, value: string) {
    const entityId = this.config[entityKey];
    if (!entityId) return;

    await this.hass.callService("input_select", "select_option", {
      entity_id: entityId,
      option: value,
    });
  }

  private _toggleEnabled() {
    const eid = this.config.enabled_entity;
    const state = this.hass.states[eid]?.state;
    const service = state === "on" ? "turn_off" : "turn_on";
    this.hass.callService("switch", service, { entity_id: eid });
  }

  static styles = css`
    ha-card {
      padding: 16px;
    }
    .info {
      font-size: 16px;
      margin-bottom: 8px;
    }
    .temp {
      font-size: 24px;
      font-weight: bold;
    }
    .controls {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    button {
      padding: 8px;
      font-size: 16px;
      background: var(--primary-color);
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }
    .range,
    .setpoint,
    .mode-select,
    .fan-select {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    label {
      font-weight: 500;
      min-width: 60px;
    }
    select,
    input[type="number"] {
      font-size: 14px;
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid var(--divider-color);
      width: 80px;
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "climate-react-card": ClimateReactCard;
  }
}
