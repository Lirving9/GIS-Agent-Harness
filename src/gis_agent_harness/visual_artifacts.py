from __future__ import annotations

import base64
import hashlib
import mimetypes
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class VisualArtifact:
    source_path: str
    captured_path: str
    content_type: str
    sha256: str
    size_bytes: int
    thumbnail_base64: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "captured_path": self.captured_path,
            "content_type": self.content_type,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "thumbnail_base64": self.thumbnail_base64,
        }


def capture_visual_artifact(path: str | Path, *, output_dir: str | Path | None = None) -> VisualArtifact:
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(f"Visual artifact does not exist: {source_path}")
    data = source_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    content_type = mimetypes.guess_type(source_path.name)[0] or "application/octet-stream"
    destination_dir = Path(output_dir) if output_dir is not None else source_path.parent / "captures"
    destination_dir.mkdir(parents=True, exist_ok=True)
    suffix = source_path.suffix or ".bin"
    captured_path = destination_dir / f"{digest[:16]}{suffix}"
    if not captured_path.exists():
        shutil.copyfile(source_path, captured_path)
    return VisualArtifact(
        source_path=str(source_path),
        captured_path=str(captured_path),
        content_type=content_type,
        sha256=digest,
        size_bytes=len(data),
        thumbnail_base64=base64.b64encode(data[:64 * 1024]).decode("ascii"),
    )
