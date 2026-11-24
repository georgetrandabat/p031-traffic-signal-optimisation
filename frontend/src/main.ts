// Basic monitor: draws the network + vehicles + signals on a canvas, prints state as text.

// ---- message types (must match backend/sim/controller.py) ----
interface NetworkMsg {
  type: "network";
  scenario: string;
  scenarios: Record<string, string>; // key -> label
  bounds: [number, number, number, number]; // xmin, ymin, xmax, ymax
  lanes: [number, number][][]; // each lane = list of [x, y]
  signals: { tl: string; index: number; x: number; y: number }[];
}

interface SnapshotMsg {
  type: "snapshot";
  scenario: string;
  status: "idle" | "paused" | "running" | "finished";
  // missing until SUMO is connected:
  time?: number;
  step?: number;
  arrived?: number;
  vehicles?: [number, number, number][]; // x, y, speed
  meanSpeed?: number;
  totalWaiting?: number;
  lights?: { id: string; program: string; phase: number; state: string; nextSwitchIn: number }[];
  approaches?: { edge: string; queue: number; meanSpeed: number; waiting: number }[];
}

// ---- page elements ----
const canvas = document.getElementById("map") as HTMLCanvasElement;
const ctx = canvas.getContext("2d")!;
const info = document.getElementById("info")!;
const conn = document.getElementById("conn")!;
const select = document.getElementById("scenario") as HTMLSelectElement;

let net: NetworkMsg | null = null;
let ws: WebSocket;

// SUMO metres -> canvas pixels (y flipped: SUMO y points up)
function toPx(x: number, y: number): [number, number] {
  const [xmin, ymin, xmax, ymax] = net!.bounds;
  const s = Math.min(canvas.width / (xmax - xmin), canvas.height / (ymax - ymin));
  return [(x - xmin) * s, canvas.height - (y - ymin) * s];
}

function dot(x: number, y: number, r: number, colour: string): void {
  const [px, py] = toPx(x, y);
  ctx.fillStyle = colour;
  ctx.beginPath();
  ctx.arc(px, py, r, 0, 2 * Math.PI);
  ctx.fill();
}

function draw(snap: SnapshotMsg): void {
  if (!net) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.strokeStyle = "#888";
  ctx.lineWidth = 3;
  for (const lane of net.lanes) {
    ctx.beginPath();
    lane.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(...toPx(x, y)) : ctx.lineTo(...toPx(x, y))));
    ctx.stroke();
  }

  for (const [x, y, speed] of snap.vehicles ?? []) dot(x, y, 3, speed < 0.1 ? "red" : "lime");

  // signal colour = this link's character in the light's state string
  for (const s of net.signals) {
    const ch = snap.lights?.find((l) => l.id === s.tl)?.state[s.index]?.toLowerCase();
    dot(s.x, s.y, 5, ch === "g" ? "lime" : ch === "y" ? "yellow" : "red");
  }
}

function showInfo(snap: SnapshotMsg): void {
  const lines = [`Scenario: ${snap.scenario}   Status: ${snap.status}`];
  if (snap.time !== undefined) {
    lines.push(
      `Time: ${snap.time} s   Step: ${snap.step}   Vehicles: ${snap.vehicles!.length}   Arrived: ${snap.arrived}`,
      `Mean speed: ${snap.meanSpeed!.toFixed(1)} m/s   Total waiting: ${snap.totalWaiting!.toFixed(0)} s`,
      "",
    );
    for (const l of snap.lights!)
      lines.push(`Light ${l.id}  program ${l.program}  phase ${l.phase}  state ${l.state}  next switch in ${l.nextSwitchIn.toFixed(0)} s`);
    lines.push("", "Edge     queue   speed   waiting");
    for (const a of snap.approaches!)
      lines.push(`${a.edge.padEnd(8)} ${String(a.queue).padEnd(7)} ${a.meanSpeed.toFixed(1).padEnd(7)} ${a.waiting.toFixed(0)}`);
  }
  info.textContent = lines.join("\n");
  conn.textContent = "connected";
}

function connect(): void {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data) as NetworkMsg | SnapshotMsg;
    if (msg.type === "network") {
      net = msg;
      select.replaceChildren(
        ...Object.entries(msg.scenarios).map(([key, label]) => new Option(label, key, false, key === msg.scenario)),
      );
    } else {
      draw(msg);
      showInfo(msg);
    }
  };
  ws.onclose = () => {
    conn.textContent = "disconnected, retrying...";
    setTimeout(connect, 2000);
  };
}

const send = (msg: object) => ws.send(JSON.stringify(msg));
for (const cmd of ["start", "pause", "step", "reset"]) document.getElementById(cmd)!.onclick = () => send({ cmd });
select.onchange = () => send({ cmd: "scenario", scenario: select.value });
const speed = document.getElementById("speed") as HTMLSelectElement;
speed.onchange = () => send({ cmd: "speed", speed: Number(speed.value) });

connect();
