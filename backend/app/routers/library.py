from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import FileResponse
from app.schemas import (
    CollectionCreateRequest,
    CollectionUpdateRequest,
    CollectionResponse,
    SaveToLibraryRequest,
    SaveToLibraryResponse,
    KnowledgeItemResponse
)
from app.services.library_service import library_service
from app.services.export_service import export_service

router = APIRouter(tags=["Personal Knowledge Library & Exports"])


# --- COLLECTIONS ENDPOINTS ---

@router.post("/api/collections", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(request: CollectionCreateRequest):
    """Create a new collection category in the user's personal knowledge library."""
    try:
        return library_service.create_collection(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection: {str(e)}"
        )


@router.get("/api/collections", response_model=List[CollectionResponse])
async def list_collections(owner_id: str = Query("default_user")):
    """List all collections in the user's personal knowledge library."""
    return library_service.list_collections(owner_id=owner_id)


@router.get("/api/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: str, owner_id: str = Query("default_user")):
    """Retrieve collection details by ID."""
    collection = library_service.get_collection(collection_id, owner_id=owner_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_id}' not found or access denied."
        )
    return collection


@router.patch("/api/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(collection_id: str, request: CollectionUpdateRequest, owner_id: str = Query("default_user")):
    """Update or rename a collection."""
    collection = library_service.update_collection(collection_id, request, owner_id=owner_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_id}' not found or access denied."
        )
    return collection


@router.delete("/api/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(collection_id: str, owner_id: str = Query("default_user")):
    """Safely delete a collection. Preserves original project data and disk artifacts."""
    success = library_service.delete_collection(collection_id, owner_id=owner_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_id}' not found or access denied."
        )
    return None


@router.get("/api/collections/{collection_id}/items", response_model=List[KnowledgeItemResponse])
async def list_collection_items(collection_id: str, owner_id: str = Query("default_user")):
    """List all saved knowledge items belonging to a collection."""
    collection = library_service.get_collection(collection_id, owner_id=owner_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_id}' not found or access denied."
        )
    return library_service.list_knowledge_items(owner_id=owner_id, collection_id=collection_id)


# --- PROJECT -> LIBRARY SAVE & KNOWLEDGE ITEM ENDPOINTS ---

@router.post("/api/projects/{project_id}/save-to-library", response_model=SaveToLibraryResponse)
async def save_project_to_library(project_id: str, request: SaveToLibraryRequest):
    """
    Save a completed processed project into a personal knowledge library collection.
    Idempotent: Prevents accidental duplicate saves of the same project to the same collection.
    """
    try:
        return library_service.save_project_to_library(
            project_id=project_id,
            collection_id=request.collection_id,
            owner_id=request.owner_id or "default_user"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save project to library: {str(e)}"
        )


@router.get("/api/library/items", response_model=List[KnowledgeItemResponse])
async def list_library_items(owner_id: str = Query("default_user"), collection_id: Optional[str] = Query(None)):
    """List all saved knowledge items across collections in the user's personal knowledge library."""
    return library_service.list_knowledge_items(owner_id=owner_id, collection_id=collection_id)


@router.get("/api/library/items/{item_id}", response_model=KnowledgeItemResponse)
async def get_library_item(item_id: str, owner_id: str = Query("default_user")):
    """Retrieve full details of a saved knowledge item including provenance, multi-language code snippets, and artifacts."""
    item = library_service.get_knowledge_item(item_id, owner_id=owner_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge item '{item_id}' not found or access denied."
        )
    return item


# --- ADVANCED EXPORTS ENDPOINTS (MILESTONE 7) ---

@router.get("/api/library/items/{item_id}/export/markdown")
async def export_item_markdown(item_id: str, owner_id: str = Query("default_user")):
    """Export saved knowledge item as structured Markdown (.md)."""
    try:
        filepath, filename = export_service.export_markdown(item_id, owner_id=owner_id)
        return FileResponse(filepath, media_type="text/markdown", filename=filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/api/library/items/{item_id}/export/json")
async def export_item_json(item_id: str, owner_id: str = Query("default_user")):
    """Export saved knowledge item as versioned JSON (v1.0 schema)."""
    try:
        filepath, filename = export_service.export_json(item_id, owner_id=owner_id)
        return FileResponse(filepath, media_type="application/json", filename=filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/api/library/items/{item_id}/export/pdf")
async def export_item_pdf(item_id: str, owner_id: str = Query("default_user")):
    """Export saved knowledge item as formatted PDF document."""
    try:
        filepath, filename = export_service.export_pdf(item_id, owner_id=owner_id)
        return FileResponse(filepath, media_type="application/pdf", filename=filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/api/library/items/{item_id}/export/anki")
async def export_item_anki(item_id: str, owner_id: str = Query("default_user")):
    """Export saved knowledge item as Anki CSV flashcards."""
    try:
        filepath, filename = export_service.export_anki(item_id, owner_id=owner_id)
        return FileResponse(filepath, media_type="text/csv", filename=filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/api/library/items/{item_id}/export/zip")
async def export_item_zip(item_id: str, owner_id: str = Query("default_user")):
    """Export complete self-describing offline ZIP Knowledge Package."""
    try:
        filepath, filename = export_service.export_zip(item_id, owner_id=owner_id)
        return FileResponse(filepath, media_type="application/zip", filename=filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
