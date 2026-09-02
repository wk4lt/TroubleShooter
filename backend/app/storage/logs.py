import time
from collections import deque
from typing import Dict, List, Optional


class LogStore:
    def __init__(self, maxlen: int = 3000):
        self._logs: deque = deque(maxlen=maxlen)
        self._seq = 0

    def add(self, entry: Dict) -> None:
        entry.setdefault("ts", time.time())
        entry["seq"] = self._seq
        self._seq += 1
        self._logs.append(entry)

    def current_seq(self) -> int:
        return self._seq

    def list(
        self,
        session_id: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict]:
        out: List[Dict] = []
        for e in reversed(self._logs):
            if session_id and e.get("session_id") != session_id:
                continue
            if level and e.get("level") != level.upper():
                continue
            out.append(e)
            if len(out) >= limit:
                break
        out.reverse()
        return out

    def list_after(self, seq: int) -> List[Dict]:
        return [e for e in self._logs if e["seq"] >= seq]


log_store = LogStore()
