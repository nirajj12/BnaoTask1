import re
import uuid
from pathlib import Path
from typing import Iterable, List
from datetime import datetime
from zoneinfo import ZoneInfo

from logger.custom_logger import CustomLogger
from exception.custom_exception_archieve import DocumentPortalException

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
log = CustomLogger().get_logger(__name__)


def generate_session_id(prefix: str = "session") -> str:
    ist = ZoneInfo("Asia/Kolkata")
    return f"{prefix}_{datetime.now(ist).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def save_uploaded_files(uploaded_files: Iterable, target_dir: Path) -> List[Path]:
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        saved = []

        for uf in uploaded_files:
            name = uf.name
            ext = Path(name).suffix.lower()

            if ext not in SUPPORTED_EXTENSIONS:
                log.warning("unsupported_file_skipped", filename=name)
                continue

            safe = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(name).stem).lower()
            fname = f"{safe}_{uuid.uuid4().hex[:8]}{ext}"
            out = target_dir / fname

            with open(out, "wb") as f:
                f.write(uf.getbuffer())

            saved.append(out)
            log.info("file_saved", original=name, saved_as=str(out))

        return saved

    except Exception as e:
        raise DocumentPortalException("Failed to save uploaded files", e) from e
