// File: www/thermoadapt-card/thermoadapt-card.ts
// A LitElement custom-card that replicates the UI shown in the screenshots
// (enable switch, adaptive toggle, conditional blocks for dynamic vs manual
// parameters and read-only tiles for temperatures / humidity).
//
// Works with the entity naming convention used by the ThermoAdapt integration:
//   switch.thermoadapt_<zone>_enabled
//   input_boolean.thermoadapt_<zone>_dinamico
//   number.thermoadapt_<zone>_temp_min / _temp_max / _setpoint …
//   sensor.<your_sensors>
//
// ─────────────────────────────────────────────────────────────────────────────

import { css, html, LitElement, TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  HomeAssistant,
  hasConfigOrEntityChanged,
  LovelaceCard,
} from "custom-card-helpers";

interface ThermoAdaptCardConfig {
  zone: string;                 // "sala", "quarto", …
  title?: string;               // optional card header
  temp_in: string;              // sensor entity-id
  temp_out: string;             // sensor entity-id
  hum_in?: string;              // optional sensor entity-id
  hum_out?: string;             // optional sensor entity-id
}

@customElement("thermoadapt-card")
export class ThermoAdaptCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property({ attribute: false }) private _config!: ThermoAdaptCardConfig;

  // Internal cache (avoid recomputation on tiny hass updates)
  @state() private _enabled = false;
  @state() private _adaptive = false;

  // ────────────────────────────────────────────────────────────────────
  // Card API
  // ────────────────────────────────────────────────────────────────────
  public setConfig(config: ThermoAdaptCardConfig): void {
    if (!config.zone || !config.temp_in || !config.temp_out) {
      throw new Error("ThermoAdapt-card: zone, temp_in and temp_out are required");
    }
    this._config = {
      title: `ThermoAdapt – ${config.zone.charAt(0).toUpperCase() + config.zone.slice(1)}`,
      ...config,
    } as ThermoAdaptCardConfig;
  }

  public getCardSize(): number {
    return 6;
  }

  protected shouldUpdate(changedProps: Map<string, unknown>): boolean {
    return hasConfigOrEntityChanged(this, changedProps, true);
  }

  // ────────────────────────────────────────────────────────────────────
  // Render helpers
  // ────────────────────────────────────────────────────────────────────
  private _state(id: string): string {
    return this.hass.states[id]?.state ?? "unavailable";
  }

  private _number(id: string): number | null {
    const s = this._state(id);
    const v = Number(s);
    return !isNaN(v) ? v : null;
  }

  // ────────────────────────────────────────────────────────────────────
  // Lifecycle
  // ────────────────────────────────────────────────────────────────────
  protected willUpdate(): void {
    const z = this._config.zone;
    this._enabled = this._state(`switch.thermoadapt_${z}_enabled`) === "on";
    this._adaptive = this._state(`input_boolean.thermoadapt_${z}_dinamico`) === "on";
  }

  // ────────────────────────────────────────────────────────────────────
  // Render
  // ────────────────────────────────────────────────────────────────────
  protected render(): TemplateResult {
    if (!this.hass) return html``;

    const z = this._config.zone;
    const n = (suf: string) => `number.thermoadapt_${z}_${suf}`;

    // Sensors / current values
    const tIn  = this._number(this._config.temp_in);
    const tOut = this._number(this._config.temp_out);
    const hIn  = this._config.hum_in  ? this._number(this._config.hum_in)  : null;
    const hOut = this._config.hum_out ? this._number(this._config.hum_out) : null;

    // Slider states
    const tempMin   = this._number(n("temp_min"));
    const tempMax   = this._number(n("temp_max"));
    const setpoint  = this._number(n("setpoint"));
    const deadband  = this._number(n("deadband"));
    const humidMax  = this._number(n("humid_max"));

    return html`
      <ha-card .header=${this._config.title}>
        <!-- ─── Enable / Adaptive toggles ──────────────────────────── -->
        <div class="row toggles">
          <ha-switch
            aria-label="Enable"
            .checked=${this._enabled}
            @click=${() => this._toggle(`switch.thermoadapt_${z}_enabled`)}
          ></ha-switch>
          <span>Controle</span>

          <ha-switch
            aria-label="Adaptive"
            .checked=${this._adaptive}
            @click=${() => this._toggle(`input_boolean.thermoadapt_${z}_dinamico`)}
          ></ha-switch>
          <span>Algoritmo</span>
        </div>

        <!-- ─── Parameter section (changes by mode) ────────────────── -->
        ${this._adaptive
          ? html`
              <div class="row sliders">
                ${this._slider(n("setpoint"), "Set-point Base", setpoint, 18, 30, 0.1)}
                ${this._slider(n("deadband"), "Dead-band", deadband, 0, 5, 0.1)}
                ${this._slider(n("humid_max"), "UR Máx", humidMax, 40, 80, 1)}
              </div>
            `
          : html`
              <div class="row sliders">
                ${this._slider(n("temp_min"), "Temp Min", tempMin, 16, 30, 0.5)}
                ${this._slider(n("temp_max"), "Temp Máx", tempMax, 20, 40, 0.5)}
                ${this._slider(n("setpoint"), "Alvo", setpoint, 18, 30, 0.1)}
              </div>
            `}

        <!-- ─── Live sensors ────────────────────────────────────────── -->
        <div class="row sensors">
          ${this._tile("Temp Interna", tIn, "°C")}
          ${this._tile("Temp Externa", tOut, "°C")}
          ${hIn !== null ? this._tile("UR Interna", hIn, "%") : ""}
          ${hOut !== null ? this._tile("UR Externa", hOut, "%") : ""}
        </div>
      </ha-card>
    `;
  }

  // ────────────────────────────────────────────────────────────────────
  // Helpers – UI widgets
  // ────────────────────────────────────────────────────────────────────
  private _slider(eid: string, label: string, value: number | null, min: number, max: number, step: number) {
    if (value === null) return html``;
    return html`
      <div class="slider-block">
        <span class="lbl">${label}</span>
        <ha-slider
          .min=${min}
          .max=${max}
          .step=${step}
          .value=${value}
          @change=${(ev: Event) =>
            this.hass.callService("input_number", "set_value", {
              entity_id: eid,
              value: (ev.target as HTMLInputElement).value,
            })}
        ></ha-slider>
        <span class="val">${value}</span>
      </div>
    `;
  }

  private _tile(label: string, val: number | null, unit: string) {
    return html`
      <div class="tile">
        <span class="tile-label">${label}</span>
        <span class="tile-val">${val !== null ? val.toFixed(1) : "–"} ${unit}</span>
      </div>
    `;
  }

  private _toggle(eid: string) {
    const st = this._state(eid);
    const svc = eid.startsWith("switch.") ? "switch" : "input_boolean";
    const action = st === "on" ? "turn_off" : "turn_on";
    this.hass.callService(svc, action, { entity_id: eid });
  }

  // ────────────────────────────────────────────────────────────────────
  // Styles
  // ────────────────────────────────────────────────────────────────────
  static styles = css`
    ha-card {
      padding: 12px 16px 16px;
      box-sizing: border-box;
    }
    .row {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 8px;
      align-items: center;
    }
    .toggles span {
      margin-right: 16px;
      font-weight: 500;
    }
    ha-switch {
      --mdc-theme-secondary: var(--primary-color);
    }
    .slider-block {
      flex: 1 1 120px;
      min-width: 110px;
    }
    .slider-block .lbl {
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
    }
    ha-slider {
      width: 100%;
    }
    .slider-block .val {
      font-size: 12px;
      color: var(--primary-text-color);
    }
    .sensors .tile {
      flex: 1 1 100px;
      background: var(--card-background-color, #f7f7f7);
      padding: 8px;
      border-radius: 8px;
      text-align: center;
    }
    .tile-label {
      font-size: 11px;
      color: var(--secondary-text-color);
    }
    .tile-val {
      font-size: 16px;
      font-weight: 600;
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "thermoadapt-card": ThermoAdaptCard;
  }
}
