![Project Logo](./images/logo.png)

# HomeCtrl

---

HomeCtrl is a hobby home automation platform running on a Raspberry Pi with lightweight devices 
based on ESP32 (MicroPython). It aggregates device telemetry via MQTT, stores history in PostgreSQL 
and exposes a REST API and WebSocket for a React frontend.

Repository: https://github.com/dzemchmielewski/homectrl

## Architecture overview

**Backend (Raspberry Pi)**

* Language & frameworks: Python, Starlette/FastAPI (REST), PostgreSQL, Mosquitto (MQTT).
* Systemd services:

    * `homectrl-frontend.service` — launches the frontend.
    * `homectrl-restapi.service` — reads onair messages and exposes REST API for frontend.
    * `homectrl-onair.service` — core service that processes MQTT messages, publishes `onair` and contains plugins.

**MQTT topics**

* Device topics: `homectrl/device/<name>/<facility>`
* Onair topics: `homectrl/onair/<facet>/<name>`

`<name>` examples: `bathroom`, `desk`, `doors`, `pantry`, `radio`, `stairs`, `kitchen`, `socket`, `toilet`, `wardrobe`.

`<facility>`: `live`, `data`, `capabilities`, `state`, `control`.

* `live`, `data`, `capabilities`, `state` — published by devices.
* `control` — read by devices (commands from UI/controllers).

`<facet>` examples: `light`, `presence`, `live`, `temperature`, `humidity`, `darkness`, etc.

**Frontend**

* React + Bootstrap application.
* Uses REST API for initial data and a WebSocket for live `onair` updates.

**Devices**

* Hardware: ESP32 (C3 / S3 GENERIC).
* Firmware: MicroPython with a custom set of modules compiled into firmware to ease deployment.

    * `BoardApplication` (in `micropython/board/board_application.py`) - async parent class: MQTT handling, NTP sync, remote inspection entry points.
    * `microdot.websocket` — provides remote CLI-style inspection when running on device.
    * `mqtt_as` — Peter Hinch's MQTT client (modified to the project needs).
    * `boot`, `toolbox`, OTA updater, helpers and drivers.

**CLI tool**

* `homectrl` — helper command-line utility for interacting with devices and services.

Commands:

```
homectrl {connect,webrepl,ping,db,mqtt,sms,devel}
```

Example (webrepl):

```
homectrl webrepl [--file FILE | --get GET | --exit | --reboot] <device>
# devices: kitchen, radio, dev, pantry, wardrobe, bathroom, cam, socket, desk, plant, toilet, owen, lamp-rc, doors, stairs
```

---

## homectrl-onair plugins

* **devices** — ingests `homectrl/device/...` topics, translates to `homectrl/onair/...`, persists history to PostgreSQL and republishes last-known states on startup.
* **laundry** — monitors bathroom electricity usage, computes last laundry run and active power consumed, stores results and sends SMS notifications to family when laundry completes.
* **weather** — reads a local meteo station and publishes updates as a `meteo` device.

## Getting started (development)

1. Clone repo:

```bash
git clone https://github.com/dzemchmielewski/homectrl.git
cd homectrl
```

2. Backend: create venv, install dependencies and run REST API (FastAPI/Starlette).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# run REST API (example)
uvicorn homectrl.restapi:app --reload
```

3. MQTT (mosquitto) — ensure broker is running and accessible by devices and backend.
4. PostgreSQL — create DB and run migrations (if any).
5. Frontend (React):

```bash
cd frontend
npm install
npm start
```

6. Devices — build MicroPython firmware, flash ESP32 devices and configure MQTT/credentials.


## Repository Structure

```
backend/               Backend services and core logic
  services/            Plugin modules (devices, laundry, meteo, etc.)
  storage.py           Database ORM models
  restapi.py           FastAPI REST endpoints
  onair.py             Main onair service with plugin loader
  tools.py             MQTT client, WebREPL client, utilities

devices/               Individual device implementations
  stairs.py            Example: stairs lighting with presence detection
  kitchen.py, bathroom.py, etc.

micropython/           MicroPython framework for devices
  board/
    board_application.py   Base class for all devices
    board_shared.py        Shared utilities
    boot.py                Boot sequence, WiFi, NTP
    mqtt_as/               Modified MQTT client
    microdot/              WebSocket server for remote CLI
  toolbox/               Helper modules

modules/               Hardware drivers for devices (I2C sensors, GPIO, etc.)
  hcsr04.py, ads1x15.py, veml7700.py, pzem.py, etc.

frontend/              React + Bootstrap web application
  src/components/      React components

common/                Shared utilities between backend and devices
  communication.py     Socket communication abstractions
  server.py            Common server utilities

systemd/               Systemd service unit files
configuration.py       Configuration loader, MQTT topic definitions
homectrl-map.json      Device registry (IPs, ports, credentials)
secrets.json           Secrets (not in repo, referenced by ${var} in config)
```

## Configuration

* Systemd unit files live under `systemd/` and can be installed with `sudo cp` + `systemctl enable --now`.

`homectrl-map.json` contains:
- `board`: Device registry with hostnames, ports, WebREPL passwords
- `mqtt`: Broker connection (host, port, credentials)
- `database`: PostgreSQL connection
- `sms`: SMS notification settings (for laundry plugin)
- `visualcrossing`: Weather API key

## Key Patterns

### Adding a New Device

1. Create device file in `devices/<name>.py` subclassing `BoardApplication`
2. Define `Facility` objects for sensors/actuators
3. Implement `capabilities` dict with control schema (optional)
4. Add device to `homectrl-map.json` with IP/credentials
5. Flash MicroPython firmware to ESP32 with required modules compiled in
6. Deploy device file and reboot

### Adding a Backend Plugin

1. Create file in `backend/services/<name>.py`
2. Subclass `OnAirService`
3. Define `MQTT_SUBSCRIPTIONS` list
4. Implement `on_message()`, `on_connect()`, `run()` async method
5. Plugin auto-loads on onair service restart

### Adding a Database Model

1. Add Peewee model in `backend/storage.py` subclassing `HomeCtrlValueBaseModel`
2. Add field name to `data2entries()` in `backend/services/devices.py`
3. Run database migration (schema updates)


## Contributing

* Open issues and PRs on GitHub.
* Keep device-facing protocol stable: changes to `homectrl/device/...` topics should be coordinated with device firmware.


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


