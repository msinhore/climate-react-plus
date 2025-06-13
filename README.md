# ThermoAdapt – Adaptive Thermal Comfort for Home Assistant

**An implementation of the Dear & Brager adaptive-comfort model (1998 / 2001)**
that keeps your rooms comfortable year-round while saving energy. Works with any
`climate.*` (split-AC / heat-pump) and, optionally, smart TRVs.

---

## ✨ Highlights

| Feature | Description |
|---------|-------------|
| Adaptive Set-point | Calculates a dynamic target temperature from the current outdoor condition (ASHRAE 55 / EN 16798-1). |
| Dual Season | Cools in summer, heats with a smart TRV in winter — same logic. |
| Dead-band & Humidity | Configurable neutral zone and max RH (auto *dry* mode). |
| Full UI Setup | Config-Flow wizard + helper sliders/switch – **no YAML** required. |
| Lovelace Card | Single card shows enable/adaptive toggles, live sensors and sliders. |
| Multi-Zone | Add as many rooms as you like (each one is an HA Config-Entry). |
| Local-first | Runs 100 % locally; no cloud calls. |

---

## 🛠 Installation (HACS)

1. **HACS → Integrations →** *Custom Repositories* → add:
   ```text
   https://github.com/msinhore/thermo-adapt
   ```
   *Category:* **Integration**
2. Search & install **ThermoAdapt**.
3. Restart Home Assistant.
4. Add a *ThermoAdapt* zone via **Settings → Devices & Services → Add Integration**.

The Lovelace card resource (`/hacsfiles/thermoadapt-card/dist/thermo-adapt-card.js`) is
added automatically.

---

## ⚙️ Config-Flow Parameters

| Step | Field | Notes |
|------|-------|-------|
| **Devices** | *Zone name* | free text (e.g. *Sala*). |
|            | *Split-AC (climate)* | any `climate.*` entity. |
|            | *TRV (number)* | optional smart radiator valve. |
|            | *Indoor Temp* | sensor with `device_class: temperature`. |
|            | *Outdoor Temp* | idem – used by adaptive model. |
|            | *Indoor RH* | optional – triggers *dry* mode. |
| **Comfort**| *Temp min / max* | static thresholds when adaptive OFF. |
|            | *Set-point base* | central value for adaptive curve. |
|            | *Dead-band* | neutral zone before switching. |
|            | *UR max* | relative-humidity limit (%). |
|            | *Heat base / k_heat* | coefficients for adaptive heating. |

All sliders can be tweaked later via **Options** or the Lovelace card.

---

## 📐 Adaptive Equations

```
t_set,cool  = T_c,base  – k_cool × (T_out – T_balance)          (Dear & Brager 1998)
T_balance   = T_c,base  – Q_int / UA_total

t_set,heat  = T_h,base  + k_heat × (T_balance – T_out)          (Dear & Brager 2001)
```
*Defaults:*  UA = 30 W/K,  Q_int = 200 W,  k_heat = 0.18.

---

## 🖼 Lovelace Card

```yaml
type: 'custom:thermoadapt-card'
zone: sala
temp_in: sensor.temperatura_sala_temperature
temp_out: sensor.sensor_externo_temperature
hum_in: sensor.temperatura_sala_humidity   # opcional
```

Features:
* Enable / disable control loop
* Toggle adaptive algorithm
* Conditional sliders (manual × adaptive)
* Live tiles for indoor/outdoor T & RH

---

## 🙋 FAQ

* **Preciso de YAML?** Não. Toda configuração é feita na interface.
* **Funciona com Broadlink + SmartIR?** Sim, pois exige só uma entidade
  `climate.*`.
* **Suporta °F?**   Ative *Use Fahrenheit* no Config-Flow.
* **Compatível com Heat-Pump que aquece e esfria?** Sim – o modo muda
automaticamente conforme a estação.

---

## 📜 License & Author

Copyright © 2025 Marcos S. ([@msinhore](https://github.com/msinhore))  ·  MIT

