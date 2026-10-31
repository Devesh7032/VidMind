import os
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from app.services.artifact_service import artifact_service

router = APIRouter(prefix="/api/artifacts", tags=["Artifacts"])


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: str):
    """
    Download a generated knowledge artifact (Markdown, Code file, Manifest, or ZIP bundle).
    Protects against path traversal by resolving through validated artifact service index.
    """
    file_info = artifact_service.get_artifact_file_path(artifact_id)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{artifact_id}' not found or expired."
        )

    filepath, filename = file_info
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact file '{filename}' does not exist on disk."
        )

    # Set appropriate media types
    media_type = "application/octet-stream"
    if filename.endswith(".md"):
        media_type = "text/markdown"
    elif filename.endswith(".json"):
        media_type = "application/json"
    elif filename.endswith(".zip"):
        media_type = "application/zip"
    elif filename.endswith(".py"):
        media_type = "text/x-python"

    return FileResponse(
        path=filepath,
        filename=os.path.basename(filename),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={os.path.basename(filename)}"}
    )
