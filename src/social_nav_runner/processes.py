"""Own a process group in the supervisor session. Terminate the group; do not pkill by name."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path


class ProcessGroup:
    def __init__(self) -> None:
        self._pgid: int | None = None
        self._children: list[subprocess.Popen] = []
        self._logs: list[object] = []

    def _enter_group(self) -> None:
        if self._pgid is None:
            os.setpgid(0, 0)
        else:
            os.setpgid(0, self._pgid)

    def start(
        self,
        argv: list[str],
        *,
        env: dict[str, str],
        log_path: Path,
        cwd: Path | None = None,
    ) -> subprocess.Popen:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logf = open(log_path, "ab")
        self._logs.append(logf)
        proc = subprocess.Popen(
            argv,
            env=env,
            cwd=str(cwd) if cwd is not None else None,
            stdout=logf,
            stderr=subprocess.STDOUT,
            preexec_fn=self._enter_group,
        )
        if self._pgid is None:
            try:
                self._pgid = os.getpgid(proc.pid)
            except ProcessLookupError:
                self._pgid = proc.pid
        self._children.append(proc)
        return proc

    @property
    def pgid(self) -> int | None:
        return self._pgid

    def terminate(self, grace_s: float = 20.0) -> None:
        pgid = self._pgid
        if pgid is not None:
            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                pgid = None
        for p in self._children:
            if p.poll() is None:
                try:
                    p.terminate()
                except OSError:
                    pass
        deadline = time.time() + grace_s
        while time.time() < deadline:
            if all(p.poll() is not None for p in self._children):
                break
            time.sleep(0.15)
        if pgid is not None and any(p.poll() is None for p in self._children):
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for p in self._children:
            if p.poll() is None:
                try:
                    p.kill()
                except OSError:
                    pass
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        for logf in self._logs:
            try:
                logf.close()
            except Exception:
                pass
        self._logs.clear()
