from typing import Optional
from fastapi import APIRouter, Header, HTTPException, status, Query
from app.schemas import SearchResponse
from app.services.search_service import search_service
from app.services.security_service import security_service

router = APIRouter(prefix="/api", tags=["Search & Retrieval"])


@router.get("/search", response_model=SearchResponse)
async def search_knowledge(
    q: str = Query(..., min_length=1, description="Search query string"),
    collection_id: Optional[str] = Query(None, description="Optional collection ID to scope search"),
    language: Optional[str] = Query(None, description="Optional programming language filter (e.g. java, cpp, python)"),
    topic: Optional[str] = Query(None, description="Optional topic title filter"),
    page: int = Query(1, ge=1, description="Page index (1-based)"),
    page_size: int = Query(20, ge=1, le=50, description="Results per page (max 50)"),
    x_user_id: str = Header(default="default_user")
):
    """
    Global search over saved personal knowledge items.
    Applies bounded pagination, relevance ranking, term highlighting, snippets, and filters.
    Respects ownership isolation boundaries.
    """
    safe_page, safe_size = security_service.validate_pagination(page, page_size)
    try:
        return search_service.search(
            query=q,
            owner_id=x_user_id,
            collection_id=collection_id,
            language=language,
            topic=topic,
            page=safe_page,
            page_size=safe_size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search request failed: {str(e)}"
        )


@router.get("/collections/{collection_id}/search", response_model=SearchResponse)
async def search_collection_knowledge(
    collection_id: str,
    q: str = Query(..., min_length=1, description="Search query string"),
    language: Optional[str] = Query(None, description="Optional programming language filter"),
    topic: Optional[str] = Query(None, description="Optional topic filter"),
    page: int = Query(1, ge=1, description="Page index"),
    page_size: int = Query(20, ge=1, le=50, description="Results per page (max 50)"),
    x_user_id: str = Header(default="default_user")
):
    """Collection-scoped search. Searches knowledge items within a specific collection."""
    safe_page, safe_size = security_service.validate_pagination(page, page_size)
    try:
        return search_service.search(
            query=q,
            owner_id=x_user_id,
            collection_id=collection_id,
            language=language,
            topic=topic,
            page=safe_page,
            page_size=safe_size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collection search failed: {str(e)}"
        )
