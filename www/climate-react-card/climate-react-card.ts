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

    const getState = (eid: string) => this.hass.states[this.config[eid]];
    const temp = parseFloat(getState("temperature_sensor")?.state || "0");
    const enabledState = getState("enabled_entity")?.state === "on";

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
            <label>Min:</label>
            <span>${getState("min_temp_entity")?.state}</span>
            <label>Max:</label>
            <span>${getState("max_temp_entity")?.state}</span>
          </div>
          <div class="setpoint">
            <label>Setpoint:</label>
            <span>${getState("setpoint_entity")?.state}</span>
          </div>
        </div>
      </ha-card>
    `;
  }

  private _toggleEnabled = () => {
    const eid = this.config.enabled_entity;
    const state = this.hass.states[eid]?.state;
    const service = state === "on" ? "turn_off" : "turn_on";
    this.hass.callService("switch", service, { entity_id: eid });
  };

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
    .setpoint {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    label {
      font-weight: 500;
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "climate-react-card": ClimateReactCard;
  }
}
