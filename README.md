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

## Things to avoid

- **Don't install `eclipse-sumo` or `libsumo` from pip.** SUMO comes from the official installer above, and on Windows, Smart App Control blocks the unsigned DLLs in those pip packages. Use `traci` instead of `libsumo`; it has the same API.
- **Don't edit the tutorial files where SUMO installed them.** Copy the examples (e.g. `docs/tutorial/traci_tls` inside the SUMO install folder) into this project first.

## Useful links

- [SUMO documentation](https://sumo.dlr.de/docs/)
- [SUMO tutorials](https://sumo.dlr.de/docs/Tutorials/index.html)
- [TraCI Python API](https://sumo.dlr.de/docs/TraCI/Interfacing_TraCI_from_Python.html)
- [SUMO Dublin scenario](https://github.com/maxime-gueriau/ITSC2020_CAV_impact)
