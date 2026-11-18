#!/usr/bin/env python3
"""Record one session of this agent's shared skill state."""

import argparse
import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


STATE_PATH = Path(__file__).resolve().parents[1] / "state.json"
LOCK_PATH = STATE_PATH.with_name("state.json.lock")


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stage_for(sessions):
    return "发作期" if sessions == 1 else "扩散期" if sessions == 2 else "爆发期"


def load_state():
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"version": 1, "agents": {}}
    except json.JSONDecodeError as exc:
        raise SystemExit(f"状态文件 JSON 损坏，未修改：{exc}") from exc

    if not isinstance(state, dict) or state.get("version") != 1 or not isinstance(state.get("agents"), dict):
        raise SystemExit("状态文件格式不受支持，未修改。")
    for name, record in state["agents"].items():
        sessions = record.get("sessions") if isinstance(record, dict) else None
        if not isinstance(name, str) or not isinstance(sessions, int) or isinstance(sessions, bool) or sessions < 0:
            raise SystemExit("状态文件记录格式错误，未修改。")
    return state


def save_state(state):
    fd, temporary = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=STATE_PATH.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(state, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, STATE_PATH)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description="Record this agent's session in the shared skill state.")
    parser.add_argument("agent_name", help="Resolved canonical product name; do not pass a placeholder")
    args = parser.parse_args()
    name = args.agent_name.strip()
    if "<" in name or ">" in name:
        parser.error("agent_name must be resolved; placeholders are not accepted")
    if not name or len(name) > 64 or any(ord(char) < 32 for char in name):
        parser.error("agent_name must contain 1–64 printable characters")

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = load_state()
        first_infection = name not in state["agents"]
        record = state["agents"].get(name, {"sessions": 0, "first_seen": now()})
        record["sessions"] += 1
        record["stage"] = stage_for(record["sessions"])
        record["last_seen"] = now()
        state["agents"][name] = record
        save_state(state)

    print(json.dumps({
        "agent": name,
        "first_infection": first_infection,
        "sessions": record["sessions"],
        "stage": record["stage"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
