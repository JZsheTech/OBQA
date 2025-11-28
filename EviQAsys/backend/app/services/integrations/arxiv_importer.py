from __future__ import annotations

import logging
import re
import tempfile
from pathlib import Path
from typing import Any

import requests

from ...env_setting import UploadSettings, get_upload_settings
from ...repositories import ArxivFavoritesRepository, CollectionsRepository, DocumentsRepository
from ..ingestion import DocumentIngestor

logger = logging.getLogger(__name__)


class ArxivImportService:
    def __init__(
        self,
        *,
        favorites_repo: ArxivFavoritesRepository | None = None,
        documents_repo: DocumentsRepository | None = None,
        collections_repo: CollectionsRepository | None = None,
        upload_settings: UploadSettings | None = None,
        document_ingestor: DocumentIngestor | None = None,
    ) -> None:
        self._favorites_repo = favorites_repo or ArxivFavoritesRepository()
        self._documents_repo = documents_repo or DocumentsRepository()
        self._collections_repo = collections_repo or CollectionsRepository()
        self._upload_settings = upload_settings or get_upload_settings()
        self._ingestor = document_ingestor or DocumentIngestor(upload_settings=self._upload_settings)

    def import_to_collection(self, *, favorite_id: int, collection_id: int) -> dict[str, Any]:
        favorite = self._favorites_repo.get_by_id(favorite_id)
        if not favorite:
            raise ValueError("Favorite paper not found.")
        if favorite.get("document_id"):
            raise ValueError("Paper already imported to documents.")
        collection = self._collections_repo.get_by_id(collection_id)
        if not collection:
            raise ValueError("Target collection does not exist.")
        pdf_url = self._resolve_pdf_url(favorite)
        if not pdf_url:
            raise ValueError("PDF URL is missing for this arXiv paper.")

        temp_dir = tempfile.TemporaryDirectory(prefix="arxiv_import_")
        temp_path = Path(temp_dir.name).joinpath(self._build_temp_name(favorite))
        try:
            self._download_pdf(pdf_url, temp_path)
            document = self._ingestor.ingest_path(
                collection_id,
                temp_path,
                arxiv_favorite_id=favorite_id,
            )
            self._favorites_repo.link_document(favorite_id=favorite_id, document_id=document["id"])
            return document
        finally:
            try:
                temp_dir.cleanup()
            except Exception:  # noqa: BLE001 - cleanup best effort
                logger.warning("Failed to clean temporary arxiv download directory %s", temp_dir.name)

    def _download_pdf(self, url: str, target_path: Path) -> None:
        headers = {"User-Agent": "EviQAsys-Arxiv/0.1"}
        max_bytes = self._upload_settings.max_upload_mb * 1024 * 1024
        try:
            response = requests.get(url, stream=True, headers=headers, timeout=(5, 60))
            response.raise_for_status()
        except Exception as exc:
            raise RuntimeError(f"Failed to download PDF from arXiv ({url})") from exc
        content_type = (response.headers.get("content-type") or "").lower()
        if "pdf" not in content_type:
            logger.warning("Unexpected content-type for arXiv PDF url=%s content_type=%s", url, content_type)

        total = 0
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("Downloaded PDF exceeds MAX_UPLOAD_MB limit.")
                    handle.write(chunk)
        except Exception:
            target_path.unlink(missing_ok=True)
            raise

    def _resolve_pdf_url(self, favorite: dict[str, Any]) -> str | None:
        if favorite.get("pdf_url"):
            return str(favorite["pdf_url"])
        arxiv_id = favorite.get("arxiv_id")
        version = favorite.get("version") or ""
        if not arxiv_id:
            return None
        # arxiv pdf url uses id + optional version suffix
        return f"https://arxiv.org/pdf/{arxiv_id}{version}.pdf"

    def _build_temp_name(self, favorite: dict[str, Any]) -> str:
        arxiv_id = favorite.get("arxiv_id") or "arxiv"
        title = favorite.get("title") or "paper"
        safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("_") or "paper"
        safe_id = re.sub(r"[^A-Za-z0-9._-]+", "_", arxiv_id).strip("_") or "arxiv"
        combined = f"{safe_id}_{safe_title}"
        return f"{combined[:120]}.pdf"


__all__ = ["ArxivImportService"]
