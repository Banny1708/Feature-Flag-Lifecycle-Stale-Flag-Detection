"""Safe subprocess helpers: arg arrays only, never shell=True."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class CmdResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def which(binary: str) -> str:
    return shutil.which(binary) or ""


def run_cmd(args: list[str], cwd: str | None = None, timeout: int = 120) -> CmdResult:
    try:
        proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return CmdResult(proc.returncode, proc.stdout[-20000:], proc.stderr[-20000:])
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        err = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return CmdResult(124, out[-20000:], (err + "\nTIMEOUT").strip()[-20000:], True)
    except FileNotFoundError as exc:
        return CmdResult(127, "", f"binary not found: {exc}")
    except Exception as exc:  # defensive: never crash caller
        return CmdResult(1, "", f"subprocess error: {exc}")
