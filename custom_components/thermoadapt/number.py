PARAMS = {
    "temp_min":      ("Min temperature", 18.0, 25.0, 0.1, "°C", 23.0),
    "temp_max":      ("Max temperature", 25.0, 30.0, 0.1, "°C", 27.0),
    "setpoint":      ("Fixed setpoint", 20.0, 30.0, 0.1, "°C", 25.0),
    "deadband":      ("Dead-band", 0.0, 2.0, 0.1, "°C", 0.5),
    "humid_max":     ("Humidity max", 30, 80, 1, "%", 65),
    "heat_base":     ("Base for heating", 15.0, 25.0, 0.1, "°C", 20.5),
    "k_heat":        ("Slope for heating", 0.0, 1.0, 0.01, None, 0.18),
    "ua_total":      ("UA total", 50.0, 1000.0, 1.0, "W/K", 300.0),
    "q_int":         ("Internal load", 0.0, 2000.0, 1.0, "W", 800.0),
}
