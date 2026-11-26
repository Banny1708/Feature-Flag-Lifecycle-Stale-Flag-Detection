"""Test/build discovery and execution (Phase 4: subdir + monorepo aware).

Conservative discovery only: fixed marker filenames, capped depth, skipped
vendor dirs. Never executes arbitrary scripts — only the exact commands below.

Root markers win over subdirectories (deterministic: sorted scan). A marker
whose tool is missing yields status "unavailable" (explicit TOOL_UNAVAILABLE),
not success and not a silent skip. Repos with no markers at all yield
"skipped".
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ..config import get_settings
from ..utils.subprocess_util import run_cmd, which

settings = get_settings()

SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv",
             "__pycache__", "target", ".tox", "eggs", ".mypy_cache",
             ".pytest_cache", "vendor", ".hg", ".svn"}
MAX_SCAN_DEPTH = 3


def maven_available() -> bool:
    return bool(which(settings.MVN_BIN))


def _walk_limited(repo: Path):
    """Yield (relative dir, depth) deterministically up to MAX_SCAN_DEPTH."""
    try:
        entries = sorted(repo.iterdir(), key=lambda p: p.name)
    except OSError:
        return
    yield Path("."), 0
    stack: list[tuple[Path, int]] = [(e, 1) for e in entries if e.is_dir()
                                     and e.name not in SKIP_DIRS and not e.is_symlink()]
    while stack:
        d, depth = stack.pop(0)
        rel = d.relative_to(repo)
        yield rel, depth
        if depth >= MAX_SCAN_DEPTH:
            continue
        try:
            children = sorted(d.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        for c in children:
            if c.is_dir() and c.name not in SKIP_DIRS and not c.is_symlink():
                stack.append((c, depth + 1))


def _has_npm_test_script(pkg_json: Path) -> bool:
    try:
        data = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
        scripts = data.get("scripts", {})
        return isinstance(scripts, dict) and bool(scripts.get("test"))
    except Exception:
        return False


def detect_monorepo(repo: Path) -> dict:
    """Detect monorepo layout hints. Informational; drives nothing by itself."""
    markers: list[str] = []
    roots: list[str] = []
    try:
        pkg = repo / "package.json"
        if pkg.is_file():
            try:
                if json.loads(pkg.read_text(encoding="utf-8", errors="ignore")).get("workspaces"):
                    markers.append("package.json workspaces")
            except Exception:
                pass
        for name in ("pnpm-workspace.yaml", "pnpm-workspace.yml", "lerna.json"):
            if (repo / name).is_file():
                markers.append(name)
        for rel, depth in _walk_limited(repo):
            if depth == 0 or depth > 2:
                continue
            d = repo / rel
            if any((d / m).is_file() for m in ("pyproject.toml", "setup.py",
                                               "pom.xml", "package.json", "go.mod")):
                roots.append(str(rel))
    except Exception:
        pass
    return {"is_monorepo": bool(markers) or len(roots) > 1,
            "markers": markers, "project_roots": sorted(set(roots))[:20]}


def detect_test_command(repo: Path) -> dict | None:
    """Find the test invocation. Returns {command, workdir, source} or None.

    workdir is repo-relative ("" means repo root). `command` is an argv list.
    """
    # 1. root markers (unchanged legacy priority).
    if (repo / "pom.xml").is_file() and maven_available():
        return {"command": [settings.MVN_BIN, "-q", "-DtestFailureIgnore=false", "test"],
                "workdir": "", "source": "pom.xml"}
    pkg = repo / "package.json"
    if pkg.is_file() and _has_npm_test_script(pkg) and which("npm"):
        return {"command": ["npm", "test", "--silent"],
                "workdir": "", "source": "package.json scripts.test"}
    for marker in ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"):
        if (repo / marker).is_file() and which("pytest"):
            return {"command": ["pytest", "-q"],
                    "workdir": "", "source": marker}
    if (repo / "go.mod").is_file() and which("go"):
        return {"command": ["go", "test", "./..."],
                "workdir": "", "source": "go.mod"}
    # 2. shallow subdirectory scan (monorepos, tests/ layouts), sorted = deterministic.
    for rel, _depth in _walk_limited(repo):
        if str(rel) == ".":
            continue
        d = repo / rel
        label = str(rel)
        if (d / "pom.xml").is_file() and maven_available():
            return {"command": [settings.MVN_BIN, "-q", "-DtestFailureIgnore=false", "test"],
                    "workdir": label, "source": f"{label}/pom.xml"}
        sub_pkg = d / "package.json"
        if sub_pkg.is_file() and _has_npm_test_script(sub_pkg) and which("npm"):
            return {"command": ["npm", "test", "--silent"],
                    "workdir": label, "source": f"{label}/package.json scripts.test"}
        for marker in ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"):
            if (d / marker).is_file() and which("pytest"):
                return {"command": ["pytest", "-q"],
                        "workdir": label, "source": f"{label}/{marker}"}
        if (d / "go.mod").is_file() and which("go"):
            return {"command": ["go", "test", "./..."],
                    "workdir": label, "source": f"{label}/go.mod"}
    return None


def missing_tool_reason(repo: Path) -> str | None:
    """Name the missing tool when markers exist but the binary does not."""
    if (repo / "pom.xml").is_file() and not maven_available():
        return (f"pom.xml found but '{settings.MVN_BIN}' is not installed; "
                f"Java/Maven verification UNAVAILABLE (not a pass)")
    for rel, _depth in _walk_limited(repo):
        d = repo / rel if str(rel) != "." else repo
        if (d / "pom.xml").is_file() and not maven_available():
            return (f"{d.name or '.'}/pom.xml found but '{settings.MVN_BIN}' is not "
                    f"installed; Java/Maven verification UNAVAILABLE (not a pass)")
    return None


def run_tests(repo: Path, command: list[str] | None = None) -> dict:
    detected = None if command else detect_test_command(repo)
    if command:
        cmd, workdir, source = command, "", "explicit"
    elif detected:
        cmd, workdir, source = (detected["command"], detected["workdir"],
                                detected["source"])
    else:
        gap = missing_tool_reason(repo)
        if gap:
            return {"success": False, "status": "unavailable", "test_count": 0,
                    "failed": [], "output": f"TOOL_UNAVAILABLE: {gap}",
                    "command": "", "workdir": "", "source": "missing-tool"}
        return {"success": False, "status": "skipped", "test_count": 0, "failed": [],
                "output": "UNAVAILABLE: no supported test setup detected (pom.xml/package.json/pytest/go.mod missing or tool not installed).",
                "command": "", "workdir": "", "source": ""}
    cwd = str(repo / workdir) if workdir else str(repo)
    r = run_cmd(cmd, cwd=cwd, timeout=settings.TEST_TIMEOUT_SEC)
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
    header = f"[workdir: {workdir or '.'} | source: {source}]\n"
    return {"success": success, "status": "passed" if success else "failed",
            "test_count": count, "failed": failed, "output": header + out,
            "command": " ".join(cmd), "timed_out": r.timed_out,
            "workdir": workdir, "source": source}


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
