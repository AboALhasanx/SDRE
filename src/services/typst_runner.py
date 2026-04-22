from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TypstResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    cmd: list[str]


def find_typst() -> str | None:
    return shutil.which("typst")


def compile_to_pdf(
    *,
    typst_bin: str,
    main_typ: Path,
    out_pdf: Path,
    cwd: Path,
    root: Path,
    timeout_s: int = 60,
) -> TypstResult:
    cmd = [typst_bin, "compile", "--root", str(root), str(main_typ), str(out_pdf)]
    try:
        cp = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
        ok = cp.returncode == 0
        return TypstResult(
            ok=ok,
            returncode=cp.returncode,
            stdout=cp.stdout or "",
            stderr=cp.stderr or "",
            cmd=cmd,
        )
    except FileNotFoundError:
        return TypstResult(
            ok=False,
            returncode=127,
            stdout="",
            stderr=f"Typst binary not found: {typst_bin}",
            cmd=cmd,
        )
    except subprocess.TimeoutExpired as e:
        def _coerce(v) -> str:
            if v is None:
                return ""
            if isinstance(v, bytes):
                return v.decode("utf-8", errors="replace")
            return str(v)
        return TypstResult(
            ok=False,
            returncode=124,
            stdout=_coerce(e.stdout),
            stderr=_coerce(e.stderr) or "Typst compile timed out",
            cmd=cmd,
        )
