#!/usr/bin/env python3
import argparse
import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


PHASE_TO_AGENT = {
    "themes": "agent01",
    "articles": "agent02",
    "audit": "agent03",
    "similarity": "agent04",
    "image-prompts": "agent05",
    "images": "agent05",
    "publish": "agent06",
    "pipeline": "orchestrator",
}

AGENT_ORDER = ["orchestrator", "agent01", "agent02", "agent03", "agent04", "agent05", "agent06"]


@dataclass
class AgentView:
    agent: str
    phases: List[str]
    event_count: int
    status_counter: Dict[str, int]
    last_timestamp: str
    last_phase: str
    last_status: str
    last_id: str


def _safe_json_lines(path: Path) -> List[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _latest_batch_id(log_rows: List[dict]) -> str:
    latest = None
    for r in log_rows:
        if r.get("phase") == "pipeline" and r.get("status") == "start":
            latest = r
    return (latest or {}).get("batch_id", "")


def _running_pipeline_processes() -> List[dict]:
    cmd = ["ps", "-eo", "pid,etimes,args"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return []
    out = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if "run_pipeline.py" not in line and "run_pipeline_from_themes.py" not in line:
            continue
        if "agent_status.py" in line or "serve_agent_status.py" in line:
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, etimes, args = parts
        try:
            elapsed = int(etimes)
        except Exception:
            elapsed = 0
        out.append({"pid": int(pid), "elapsed_s": elapsed, "cmd": args})
    return out


def _to_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_status(base: Path, batch_id: str = "") -> dict:
    logs_file = base / "data/logs/logs.jsonl"
    logs = _safe_json_lines(logs_file)
    if not batch_id:
        batch_id = _latest_batch_id(logs)

    scoped = [r for r in logs if r.get("batch_id") == batch_id] if batch_id else []
    by_agent: Dict[str, List[dict]] = {a: [] for a in AGENT_ORDER}
    for row in scoped:
        ph = row.get("phase", "")
        agent = PHASE_TO_AGENT.get(ph)
        if not agent:
            continue
        by_agent[agent].append(row)

    agent_views: List[AgentView] = []
    for agent in AGENT_ORDER:
        rows = by_agent.get(agent, [])
        if rows:
            phase_set = sorted({str(r.get("phase", "")) for r in rows if r.get("phase")})
            status_counter = Counter(str(r.get("status", "")) for r in rows)
            last = rows[-1]
            agent_views.append(
                AgentView(
                    agent=agent,
                    phases=phase_set,
                    event_count=len(rows),
                    status_counter=dict(status_counter),
                    last_timestamp=str(last.get("timestamp", "")),
                    last_phase=str(last.get("phase", "")),
                    last_status=str(last.get("status", "")),
                    last_id=str(last.get("id", "")),
                )
            )
        else:
            agent_views.append(
                AgentView(
                    agent=agent,
                    phases=[],
                    event_count=0,
                    status_counter={},
                    last_timestamp="",
                    last_phase="",
                    last_status="",
                    last_id="",
                )
            )

    summary_counter = Counter(str(r.get("phase", "")) for r in scoped)
    result = {
        "generated_at": _to_iso_now(),
        "batch_id": batch_id,
        "phase_counts": dict(summary_counter),
        "total_events": len(scoped),
        "running_processes": _running_pipeline_processes(),
        "agents": [a.__dict__ for a in agent_views],
    }
    return result


def _print_table(status: dict) -> None:
    print(f"Generated at: {status.get('generated_at','')}")
    print(f"Batch: {status.get('batch_id','(none)')}")
    print(f"Phase counts: {status.get('phase_counts',{})}")
    runs = status.get("running_processes", [])
    if runs:
        print("Running pipeline processes:")
        for r in runs:
            print(f"  PID={r['pid']} elapsed={r['elapsed_s']}s cmd={r['cmd']}")
    else:
        print("Running pipeline processes: none")
    print("")
    header = f"{'AGENT':<13} {'EVENTS':>6}  {'PHASES':<24} {'LAST_STATUS':<10} {'LAST_PHASE':<12} {'LAST_ID':<32} {'LAST_TIMESTAMP'}"
    print(header)
    print("-" * len(header))
    for a in status.get("agents", []):
        phases = ",".join(a.get("phases", [])[:3])
        if len(a.get("phases", [])) > 3:
            phases += ",+"
        print(
            f"{a.get('agent',''):<13} "
            f"{int(a.get('event_count',0)):>6}  "
            f"{phases:<24} "
            f"{a.get('last_status',''):<10} "
            f"{a.get('last_phase',''):<12} "
            f"{a.get('last_id','')[:32]:<32} "
            f"{a.get('last_timestamp','')}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Live status for the SOWADS orchestrator pipeline")
    parser.add_argument("--base", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    base = Path(args.base).resolve()
    status = build_status(base, batch_id=args.batch_id.strip())
    if args.format == "json":
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        _print_table(status)


if __name__ == "__main__":
    main()
