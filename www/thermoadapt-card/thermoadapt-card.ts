/*
 * ThermoAdapt Card – v0.6 (dual-mode, polished UI)
 * ------------------------------------------------------------
 * Lovelace custom-card providing full control of ThermoAdapt zones.
 * © 2025 Marcos Sinhoreli – MIT
 */

import { css, html, LitElement, TemplateResult } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import {
  HomeAssistant,
  LovelaceCard,
  hasConfigOrEntityChanged,
} from 'custom-card-helpers';

interface ThermoAdaptCardConfig {
  type: string;
  zone: string;
  title?: string;
  temp_in: string;
  temp_out: string;
  hum_in?: string;
  climate_entity?: string;
  mode_entity?: string;
  fan_entity?: string;
  enabled_entity?: string;
  adaptive_entity?: string;
  temp_min_entity?: string;
  temp_max_entity?: string;
  setpoint_entity?: string;
  deadband_entity?: string;
  humid_entity?: string;
}

@customElement('thermoadapt-card')
export class ThermoAdaptCard extends LitElement implements LovelaceCard {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @state() private _cfg!: ThermoAdaptCardConfig;

  /* ─────────────────────────── CONFIG ─────────────────────────── */
  public setConfig(c: ThermoAdaptCardConfig): void {
    if (!c?.zone || !c.temp_in || !c.temp_out) {
      throw new Error('zone, temp_in and temp_out are required');
    }
    const z = c.zone;
    this._cfg = {
      title: `ThermoAdapt – ${z.charAt(0).toUpperCase()}${z.slice(1)}`,
      enabled_entity: `switch.thermoadapt_${z}_enabled`,
      adaptive_entity: `input_boolean.thermoadapt_${z}_dinamico`,
      temp_min_entity: `number.thermoadapt_${z}_temp_min`,
      temp_max_entity: `number.thermoadapt_${z}_temp_max`,
      setpoint_entity: `number.thermoadapt_${z}_setpoint`,
      deadband_entity: `number.thermoadapt_${z}_deadband`,
      humid_entity: `number.thermoadapt_${z}_humid_max`,
      type: 'custom:thermoadapt-card',
      ...c,
    } as ThermoAdaptCardConfig;
  }

  public getCardSize() { return 7; }
  protected shouldUpdate(changed: Map<string, unknown>) {
    return hasConfigOrEntityChanged(this, changed, false);
  }

  /* ─────────────────────────── HELPERS ────────────────────────── */
  private _st(id?: string) { return id ? this.hass.states[id] : undefined; }
  private _num(id?: string) { const s = this._st(id); return s ? Number(s.state) : undefined; }

  /* ─────────────────────────── RENDER ─────────────────────────── */
  protected render(): TemplateResult {
    if (!this.hass || !this._cfg) return html``;
    const c = this._cfg;
    const enabled = this._st(c.enabled_entity)?.state === 'on';
    const adaptive = this._st(c.adaptive_entity)?.state === 'on';

    const tIn = this._num(c.temp_in);
    const tOut = this._num(c.temp_out);
    const rhIn = this._num(c.hum_in);
    const rhOut = this._num(c.hum_in?.replace('interna', 'externa'));

    return html`
      <ha-card .header=${c.title}>
        <div class="row toggles">
          ${this._toggle(c.enabled_entity!, 'Controle', enabled)}
          ${this._toggle(c.adaptive_entity!, 'Algoritmo', adaptive)}
        </div>

        ${adaptive ? this._adaptiveSliders() : this._manualSliders()}
        ${this._renderSelects()}

        <div class="grid tiles">
          ${this._tile('Temp Interna', tIn, '°C')}
          ${this._tile('Temp Externa', tOut, '°C')}
          ${rhIn !== undefined ? this._tile('UR Interna', rhIn, '%') : ''}
          ${rhOut !== undefined ? this._tile('UR Externa', rhOut, '%') : ''}
        </div>
      </ha-card>`;
  }

  /* ──────────────── UI fragments ──────────────── */
  private _toggle(eid: string, lbl: string, on: boolean) {
    return html`<ha-switch ?checked=${on} @change=${() => this.hass.callService('switch', on ? 'turn_off' : 'turn_on', { entity_id: eid })}></ha-switch><span class="toggle-label">${lbl}</span>`;
  }

  private _slider(eid: string, val: number | undefined, lbl: string, unit: string, min: number, max: number, step: number) {
    return html`<div class="slider"><span>${lbl}</span><ha-slider min=${min} max=${max} step=${step} .value=${val ?? ''} @change=${(e: any) => this.hass.callService('input_number','set_value',{ entity_id: eid, value: Number(e.target.value)})}></ha-slider><b>${val!==undefined?val.toFixed(step<1?1:0):'–'} ${unit}</b></div>`;
  }

  private _manualSliders() {
    const c = this._cfg;
    return html`<div class="grid sliders">${this._slider(c.temp_min_entity!,this._num(c.temp_min_entity),'Temp Min','°C',16,26,0.5)}${this._slider(c.temp_max_entity!,this._num(c.temp_max_entity),'Temp Max','°C',20,40,0.5)}${this._slider(c.setpoint_entity!,this._num(c.setpoint_entity),'Set-point Fix','°C',18,30,0.1)}</div>`;
  }

  private _adaptiveSliders() {
    const c = this._cfg;
    const dyn = this._num(`sensor.react_${c.zone}_setpoint_dinamico`);
    return html`<div class="grid sliders">${this._slider(c.setpoint_entity!,this._num(c.setpoint_entity),'Set-point Base','°C',18,30,0.1)}${this._slider(c.deadband_entity!,this._num(c.deadband_entity),'Dead-band','°C',0,5,0.1)}${this._slider(c.humid_entity!,this._num(c.humid_entity),'UR Máx','%',40,80,1)}</div><div class="dyn"><span>Set-point Dinâmico</span><b>${dyn?.toFixed(1)??'–'} °C</b></div>`;
  }

  private _tile(lbl: string, v?: number, u='') {
    return html`<div class="tile"><span>${lbl}</span><b>${v!==undefined?`${v.toFixed(1)} ${u}`:'–'}</b></div>`;
  }

  private _select(eid: string, lbl: string, st: any) {
    const opts: string[] = st.attributes.options||[];
    return html`<ha-select .label=${lbl} .value=${st.state} @selected=${(e:any)=>this.hass.callService('input_select','select_option',{entity_id:eid,option:e.target.value})}>${opts.map(o=>html`<mwc-list-item .value=${o}>${o}</mwc-list-item>`)}</ha-select>`;
  }

  private _renderSelects() {
    const { mode_entity, fan_entity } = this._cfg;
    const m = this._st(mode_entity); const f = this._st(fan_entity);
    return !m && !f ? html`` : html`<div class="row selects">${m?this._select(mode_entity!,'Modo',m):''}${f?this._select(fan_entity!,'Fan',f):''}</div>`;
  }

  /* ─────────────────────────── CSS ─────────────────────────── */
  static styles = css`
    ha-card { padding:18px 20px 22px; box-sizing:border-box; }
    .row { display:flex; align-items:center; gap:12px; margin-bottom:16px; }
    .toggles { gap:40px; }
    .toggle-label { font-weight:500; margin-right:8px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(120px,1fr)); gap:12px 24px; margin-bottom:16px; }
    .slider span { font-size:12px; color:var(--secondary-text-color); }
    .slider b { display:block; margin-top:4px; font-weight:600; text-align:center; }
    .dyn { text-align:center; margin:8px 0 18px; }
    .dyn span { color:var(--secondary-text-color); font-size:13px; margin-right:6px; }
    .dyn b { font-size:20px; font-weight:600; }
    .tile { text-align:center; }
    .tile span { display:block; font-size:12px; color:var(--secondary-text-color); }
    .tile b { font-size:18px; font-weight:600; margin-top:2px; }
    .selects { gap:24px; margin-bottom:16px; }
    ha-select { width:120px; }
  `;
}
