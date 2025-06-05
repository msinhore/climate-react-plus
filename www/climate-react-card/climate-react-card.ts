// File: www/climate-react-card/climate-react-card.ts
import { css, html, LitElement, TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { HomeAssistant, hasConfigOrEntityChanged } from "custom-card-helpers";

@customElement("climate-react-card")
export class ClimateReactCard extends LitElement {
  @property() hass!: HomeAssistant;
  @property() config: any;

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
    return hasConfigOrEntityChanged(this, changedProps);
  }

  render(): TemplateResult {
    if (!this.hass || !this.config) return html``;

    const entity = (eid: string) => this.hass.states[this.config[eid]];
    const temp = parseFloat(entity("sensor")?.state || "0");

    return html`
      <ha-card header="${this.config.title || "Climate React"}">
        <div class="info">
          <div class="temp">${temp.toFixed(1)}°C</div>
          <div>${entity("enabled")?.state === "on" ? "Active" : "Off"}</div>
        </div>
        <div class="controls">
          <button @click=${() => this._toggleEnabled()}>${entity("enabled")?.state === "on" ? "Desligar" : "Ligar"}</button>
          <div class="range">
            <label>Min:</label>
            <span>${entity("min")?.state}</span>
            <label>Max:</label>
            <span>${entity("max")?.state}</span>
          </div>
          <div class="setpoint">
            <label>Setpoint:</label>
            <span>${entity("setpoint")?.state}</span>
          </div>
        </div>
      </ha-card>
    `;
  }

  private _toggleEnabled() {
    const enabled = this.config.enabled;
    const state = this.hass.states[enabled]?.state;
    this.hass.callService("input_boolean", "turn_" + (state === "on" ? "off" : "on"), {
      entity_id: enabled,
    });
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
    .range, .setpoint {
      display: flex;
      gap: 8px;
      align-items: center;
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "climate-react-card": ClimateReactCard;
  }
}

