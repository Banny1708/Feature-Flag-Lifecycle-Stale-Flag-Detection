"""Maven/JaCoCo test integration. Real subprocess runs; honest 'unavailable' otherwise."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ..config import get_settings
from ..utils.subprocess_util import run_cmd, which

settings = get_settings()


def maven_available() -> bool:
    return bool(which(settings.MVN_BIN))


def detect_test_command(repo: Path) -> list[str] | None:
    if (repo / "pom.xml").exists() and maven_available():
        return [settings.MVN_BIN, "-q", "-DtestFailureIgnore=false", "test"]
    if (repo / "package.json").exists():
        return ["npm", "test", "--silent"]
    if (repo / "pytest.ini").exists() or (repo / "pyproject.toml").exists():
        return ["pytest", "-q"]
    if (repo / "go.mod").exists():
        return ["go", "test", "./..."]
    return None


def run_tests(repo: Path, command: list[str] | None = None) -> dict:
    cmd = command or detect_test_command(repo)
    if not cmd:
        return {"success": False, "status": "skipped", "test_count": 0, "failed": [],
                "output": "UNAVAILABLE: no supported test setup detected (pom.xml/package.json/pytest/go.mod missing or tool not installed).",
                "command": ""}
    r = run_cmd(cmd, cwd=str(repo), timeout=settings.TEST_TIMEOUT_SEC)
    out = ((r.stdout or "") + "\n" + (r.stderr or ""))[-20000:]
    count = 0
    m = re.search(r"Tests run:\s*(\d+)", out)
    if m:
        count = int(m.group(1))
    else:
        m2 = re.search(r"(\d+)\s+passed", out)
        if m2:
            count = int(m2.group(1))
    failed = re.findall(r"FAIL(?:ED)?:?\s+([^\n]{0,200})", out)[:20]
    success = r.returncode == 0 and not r.timed_out
    return {"success": success, "status": "passed" if success else "failed",
            "test_count": count, "failed": failed, "output": out,
            "command": " ".join(cmd), "timed_out": r.timed_out}


def find_jacoco_xml(repo: Path) -> Path | None:
    for cand in [repo / "target/site/jacoco/jacoco.xml", repo / "target/site/jacoco-ut/jacoco.xml"]:
        if cand.exists():
            return cand
    matches = sorted(repo.glob("**/jacoco.xml"))
    return matches[0] if matches else None


def parse_jacoco_summary(xml_path: Path) -> dict:
    """Parse real JaCoCo XML; return UNAVAILABLE fields on any problem."""
    try:
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
        counters = {c.get("type"): c for c in root.iter("counter")}
        def pct(c) -> str:
            if c is None:
                return "UNAVAILABLE"
            missed = int(c.get("missed", 0)); covered = int(c.get("covered", 0))
            tot = missed + covered
            return f"{(100.0 * covered / tot):.1f}%" if tot else "UNAVAILABLE"
        return {"line_coverage": pct(counters.get("LINE")),
                "branch_coverage": pct(counters.get("BRANCH")), "available": True}
    except Exception as exc:
        return {"line_coverage": "UNAVAILABLE", "branch_coverage": "UNAVAILABLE",
                "available": False, "error": str(exc)[:500]}
