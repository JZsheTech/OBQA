from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

router = APIRouter(tags=["debug"])
logger = logging.getLogger(__name__)


DEMO_PDF_PATH = Path(
    "/data2/jproject/OBQA/sample_data/test_convert/1-Cui et al. - 2019 - Class-Balanced Loss Based on Effective Number of Samples/auto/1-Cui et al. - 2019 - Class-Balanced Loss Based on Effective Number of Samples_origin.pdf",
)


@router.get("/debug/pdf-evidence-demo", response_class=FileResponse)
def serve_pdf_highlight_demo() -> FileResponse:
    """
    Return the fixed demo PDF for front-end evidence highlight debugging.
    """
    resolved_path = DEMO_PDF_PATH.resolve()
    if not resolved_path.is_file():
        logger.error("Demo PDF not found at expected path: %s", resolved_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo PDF not found.",
        )
    return FileResponse(
        path=resolved_path,
        media_type="application/pdf",
        filename=resolved_path.name,
    )


__all__ = ["router"]
