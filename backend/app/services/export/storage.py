"""
Private storage for generated exports (PDF now, DOCX / PPTX next).

Security model (Sprint 6.1 hardening, required before hosting):
  * files live in settings.EXPORTS_DIR, which is NEVER mounted statically;
  * each export gets an unguessable key "<project_id>/<uuid4hex>.<ext>",
    stored in Export.file_path (a storage key, not a URL);
  * reading a key back is confined to that project's folder: absolute
    paths, "..", backslashes or another project's folder resolve to None;
  * files are written atomically (temp file + os.replace), so a crash
    never leaves a half-written document behind.

The HTTP layer (app/routers/export.py) adds the ownership check.
"""

from __future__ import annotations

import os
import re
import tempfile
import unicodedata
import uuid
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from app.config import settings

# Extension -> HTTP media type. Also the whitelist of producible formats.
MEDIA_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

# Prefix used by the pre-hardening public URLs stored in old Export rows.
_LEGACY_PREFIX = "/exports/"


def exports_root() -> Path:
    """Resolved private export folder (read at call time: testable)."""
    return Path(settings.EXPORTS_DIR).resolve()


def new_storage_key(project_id: int, extension: str) -> str:
    """Fresh, unguessable key for one export of one project."""
    ext = str(extension).lower().lstrip(".")
    if ext not in MEDIA_TYPES:
        raise ValueError(f"Unsupported export format: {extension!r}")
    return f"{int(project_id)}/{uuid.uuid4().hex}.{ext}"


def path_for_key(key: str) -> Path:
    """Absolute path of a key produced by new_storage_key()."""
    return exports_root() / key


def resolve_storage_path(stored: str, *, project_id: int) -> Path | None:
    """
    Map an Export.file_path back to an existing file of THIS project.

    Accepts new keys ("31/<hex>.pdf") and legacy public paths
    ("/exports/31/business_plan.pdf"). Anything else -> None.
    """
    value = str(stored or "")
    if value.startswith(_LEGACY_PREFIX):
        value = value[len(_LEGACY_PREFIX):]

    # Reject separators and forms that could escape the project folder
    # before touching the filesystem.
    if not value or "\\" in value or value.startswith("/"):
        return None
    parts = PurePosixPath(value).parts
    if len(parts) != 2 or parts[0] != str(int(project_id)) or parts[1] in {"", ".", ".."}:
        return None

    root = exports_root()
    candidate = (root / parts[0] / parts[1]).resolve()
    # Defense in depth against symlinks pointing outside the folder.
    if candidate.parent != root / parts[0] or not candidate.is_file():
        return None
    return candidate


def extension_of(path: Path) -> str:
    return path.suffix.lower().lstrip(".")


def download_filename(project_title: str, document: str, extension: str) -> str:
    """
    Human-readable, header-safe file name, e.g.
    "ForgeAI_Tawla_Pro_ete_business_plan.pdf".
    Accents are folded to ASCII so every browser/OS handles it.
    """
    folded = unicodedata.normalize("NFKD", str(project_title or "")).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "_", folded).strip("_")[:60] or "projet"
    return f"ForgeAI_{slug}_{document}.{extension}"


def write_atomically(target: Path, build: Callable[[str], None]) -> None:
    """
    Run ``build(temp_path)`` then move the result onto ``target``.

    Synchronous on purpose: callers run it inside asyncio.to_thread() so
    CPU-bound renderers (ReportLab, python-docx, python-pptx) never block
    the event loop.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=target.parent, prefix=".tmp-", suffix=target.suffix)
    os.close(fd)
    try:
        build(temp_name)
        os.replace(temp_name, target)
    except BaseException:
        # Never leave a partial document behind.
        Path(temp_name).unlink(missing_ok=True)
        raise
