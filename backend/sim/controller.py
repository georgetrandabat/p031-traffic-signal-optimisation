"""All TraCI code lives here. app.py only calls load / step / snapshot / close."""
import xml.etree.ElementTree as ET
from pathlib import Path

import sumolib
import traci


class SimController:
    def __init__(self, scenarios: dict):
        self.scenarios = scenarios
        self.key = None
        self.status = "idle"  # idle | paused | running | finished
        self.network = None  # static geometry, sent once per scenario
        self.approaches = []  # incoming edges of the traffic lights
        self.step_count = 0
        self.arrived = 0
        self.connected = False

    def load(self, key: str) -> None:
        """Close any running sim and launch scenario `key` (also used for reset)."""
        self.close()
        cfg = Path(self.scenarios[key]["cfg"])
        # output-prefix stops web runs overwriting the analysis outputs (relative to the cfg folder)
        traci.start([sumolib.checkBinary("sumo"), "-c", str(cfg), "--output-prefix", f"output/web_{key}_"])
        self.connected = True
        self.key = key
        self.step_count = 0
        self.arrived = 0
        net_file = cfg.parent / ET.parse(cfg).find("input/net-file").get("value")
        self.network = self._read_network(sumolib.net.readNet(str(net_file)))
        self.status = "paused"

    def close(self) -> None:
        if self.connected:
            traci.close()
            self.connected = False

    def step(self) -> None:
        if self.status not in ("paused", "running"):
            return
        traci.simulationStep()
        self.step_count += 1
        self.arrived += traci.simulation.getArrivedNumber()
        if traci.simulation.getMinExpectedNumber() == 0:
            self.status = "finished"

    def _read_network(self, net) -> dict:
        lanes = [[list(p) for p in lane.getShape()] for edge in net.getEdges() for lane in edge.getLanes()]
        signals, self.approaches = [], []
        for tl in traci.trafficlight.getIDList():
            for index, links in enumerate(traci.trafficlight.getControlledLinks(tl)):
                if not links:
                    continue
                lane = net.getLane(links[0][0])  # incoming lane of this link
                x, y = lane.getShape()[-1]  # stop line = end of the incoming lane
                signals.append({"tl": tl, "index": index, "x": x, "y": y})
                if lane.getEdge().getID() not in self.approaches:
                    self.approaches.append(lane.getEdge().getID())
        xmin, ymin, xmax, ymax = net.getBoundary()
        return {
            "type": "network",
            "scenario": self.key,
            "scenarios": {k: v["label"] for k, v in self.scenarios.items()},
            "bounds": [xmin, ymin, xmax, ymax],
            "lanes": lanes,
            "signals": signals,
        }

    def snapshot(self) -> dict:
        snap = {"type": "snapshot", "scenario": self.key, "status": self.status}
        if not self.connected:
            return snap
        t = traci.simulation.getTime()
        vehicles = [(*traci.vehicle.getPosition(v), traci.vehicle.getSpeed(v)) for v in traci.vehicle.getIDList()]
        snap.update({
            "time": t,
            "step": self.step_count,
            "arrived": self.arrived,
            "vehicles": vehicles,  # [x, y, speed]
            "meanSpeed": sum(v[2] for v in vehicles) / len(vehicles) if vehicles else 0,
            "totalWaiting": sum(traci.vehicle.getWaitingTime(v) for v in traci.vehicle.getIDList()),
            "lights": [{
                "id": tl,
                "program": traci.trafficlight.getProgram(tl),
                "phase": traci.trafficlight.getPhase(tl),
                "state": traci.trafficlight.getRedYellowGreenState(tl),
                "nextSwitchIn": traci.trafficlight.getNextSwitch(tl) - t,
            } for tl in traci.trafficlight.getIDList()],
            "approaches": [{
                "edge": e,
                "queue": traci.edge.getLastStepHaltingNumber(e),
                "meanSpeed": traci.edge.getLastStepMeanSpeed(e),
                "waiting": traci.edge.getWaitingTime(e),
            } for e in self.approaches],
        })
        return snap
