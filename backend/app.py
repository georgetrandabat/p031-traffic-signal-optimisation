"""Web layer. Run from the repo root:  uvicorn backend.app:app --reload

Everything runs on one asyncio loop and the controller is synchronous, so TraCI is only
ever used from one place at a time. Keep endpoints `async def` (plain `def` runs in a thread).
"""
import asyncio
import contextlib
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from backend.scenarios import DEFAULT_SCENARIO, SCENARIOS
from backend.sim.controller import SimController

STATIC = Path(__file__).resolve().parent.parent / "frontend" / "static"

sim = SimController(SCENARIOS)
clients: set[WebSocket] = set()
speed = 1  # 1 = real time (1 sim second per wall-clock second)


async def broadcast(msg: dict) -> None:
    for ws in list(clients):
        try:
            await ws.send_json(msg)
        except Exception:  # browser went away; drop it, keep the sim going
            clients.discard(ws)


async def sim_loop() -> None:
    """One 1 s step every 1/speed wall-clock seconds."""
    while True:
        if sim.status != "running":
            await asyncio.sleep(0.05)
            continue
        t0 = time.perf_counter()
        sim.step()
        await broadcast(sim.snapshot())
        await asyncio.sleep(max(0.0, 1.0 / speed - (time.perf_counter() - t0)))


async def handle(cmd: str, scenario: str | None, new_speed: int | None) -> None:
    global speed
    if cmd == "speed" and new_speed in (1, 2, 5, 10):
        speed = new_speed
    elif cmd == "start" and sim.status == "paused":
        sim.status = "running"
    elif cmd == "pause" and sim.status == "running":
        sim.status = "paused"
    elif cmd == "step" and sim.status == "paused":
        sim.step()
    elif cmd == "reset":
        sim.load(sim.key)
        await broadcast(sim.network)
    elif cmd == "scenario" and scenario in SCENARIOS:
        sim.load(scenario)
        await broadcast(sim.network)
    await broadcast(sim.snapshot())


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    sim.load(DEFAULT_SCENARIO)
    task = asyncio.create_task(sim_loop())
    yield
    task.cancel()
    sim.close()


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    clients.add(ws)
    try:
        await ws.send_json(sim.network)
        await ws.send_json(sim.snapshot())
        while True:
            msg = await ws.receive_json()  # {"cmd": "...", "scenario": "...", "speed": n}
            await handle(msg.get("cmd"), msg.get("scenario"), msg.get("speed"))
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")  # last, so /ws wins
