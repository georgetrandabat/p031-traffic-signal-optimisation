# P031: Human-in-the-Loop Traffic Signal Optimisation

A web platform, powered by the SUMO traffic simulator, that detects junctions where badly timed traffic lights cause congestion, recommends better signal timings, and lets a human operator approve or reject each change.

## Setup

You need four things: SUMO 1.28.0, this repo, a Python virtual environment, and the Python packages.

**Use SUMO 1.28.0 exactly.** Both of us need the same version so simulations give identical results and match the pinned `traci`/`sumolib` versions.

### 1. Install SUMO 1.28.0

Downloads: https://sumo.dlr.de/docs/Downloads.php

1. Download and run [`sumo-win64-1.28.0.msi`](https://sumo.dlr.de/releases/1.28.0/sumo-win64-1.28.0.msi).
2. Open a **new** PowerShell window and check it worked:
   ```powershell
   sumo --version
   echo $env:SUMO_HOME
   ```
3. If `sumo` isn't recognised or `SUMO_HOME` is blank, run this once (adjust the path if you installed somewhere else), then open a new terminal:
   ```powershell
   $sumo = "C:\Program Files (x86)\SUMO"
   [Environment]::SetEnvironmentVariable("SUMO_HOME", "$sumo\", "User")
   [Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path","User") + ";$sumo\bin", "User")
   ```

### 2. Clone the repo

```powershell
git clone https://github.com/georgetrandabat/p031-traffic-signal-optimisation.git
cd p031-traffic-signal-optimisation
```

### 3. Create a virtual environment

Needs Python 3.9 or newer.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

In PyCharm you can do this instead: **Settings → Python → Interpreter → Add Interpreter → Add Local Interpreter → Virtualenv**, location `<project>/.venv`.

### 4. Install the Python packages

```bash
pip install -r requirements.txt
```

### 5. Check everything works

```bash
python -c "import traci, sumolib; print('ok')"
sumo --version
sumo-gui
```

You should see `ok`, then `Eclipse SUMO sumo 1.28.0`, then the SUMO GUI window.

## Web monitor (Deliverable 2)

A browser UI that runs SUMO headless through TraCI and shows the junction live: vehicles, signal states, queues and waiting times.

```
backend/scenarios.py        scenario list (the only place paths live)
backend/sim/controller.py   all TraCI code: load, step, snapshot
backend/app.py              FastAPI: WebSocket /ws, real-time loop, serves frontend/static
frontend/src/main.ts        TypeScript source (message types at the top)
frontend/static/            index.html; tsc writes js/ here
```

### Extra prerequisites

- [Node.js](https://nodejs.org/) LTS (only needed to compile the TypeScript). Check with `node --version`.
- The Python packages above. `requirements.txt` now also includes `fastapi` and `uvicorn`, so run `pip install -r requirements.txt` again.

### Build and run

```powershell
cd frontend
npm install        # first time only
npm run build      # compiles src/*.ts -> static/js/ (or: npm run watch)
cd ..
uvicorn backend.app:app --reload
```

Then open http://localhost:8000. Pick a scenario and press **Start**. Speed 1× is real time (1 sim second per wall second). Step only works while paused. Reset relaunches the current scenario.

Web runs write their SUMO outputs to `scenarios/<name>/output/web_<key>/`, so they don't overwrite the analysis runs.

### Adding a scenario

Add an entry to `SCENARIOS` in `backend/scenarios.py`:

```python
"heavy_tuned": {"label": "Heavy tuned", "cfg": CROSS4 / "s7_heavy_tuned.sumocfg"},
```

Traffic lights, approaches and geometry are discovered from TraCI and sumolib, so nothing else needs changing.

### WebSocket messages

Types are at the top of `frontend/src/main.ts`.

Server → browser:
- `{"type": "network", scenario, scenarios: {key: label}, bounds: [xmin, ymin, xmax, ymax], lanes: [[[x, y], ...]], signals: [{tl, index, x, y}]}`: sent on connect, scenario change and reset. A signal's `index` picks its character in the light's `state` string.
- `{"type": "snapshot", scenario, status, time, step, arrived, vehicles: [[x, y, speed]], meanSpeed, totalWaiting, lights: [{id, program, phase, state, nextSwitchIn}], approaches: [{edge, queue, meanSpeed, waiting}]}`: sent every step and after every command. `status` is `idle | paused | running | finished`. For actuated lights, `nextSwitchIn` is the *earliest* switch and can be pushed back.

Browser → server: `{"cmd": "start" | "pause" | "step" | "reset"}`, `{"cmd": "scenario", "scenario": key}`, `{"cmd": "speed", "speed": 1 | 2 | 5 | 10}`.

## Things to avoid

- **Don't install `eclipse-sumo` or `libsumo` from pip.** SUMO comes from the official installer above, and on Windows, Smart App Control blocks the unsigned DLLs in those pip packages. Use `traci` instead of `libsumo`; it has the same API.
- **Don't edit the tutorial files where SUMO installed them.** Copy the examples (e.g. `docs/tutorial/traci_tls` inside the SUMO install folder) into this project first.

## Useful links

- [SUMO documentation](https://sumo.dlr.de/docs/)
- [SUMO tutorials](https://sumo.dlr.de/docs/Tutorials/index.html)
- [TraCI Python API](https://sumo.dlr.de/docs/TraCI/Interfacing_TraCI_from_Python.html)
- [SUMO Dublin scenario](https://github.com/maxime-gueriau/ITSC2020_CAV_impact)
