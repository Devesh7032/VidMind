from typing import List
from fastapi import APIRouter, Header, HTTPException, status, Query
from app.schemas import (
    ConversationCreateRequest,
    ConversationResponse,
    PostMessageRequest,
    ChatMessageResponse
)
from app.services.conversation_service import conversation_service
from app.services.security_service import security_service

router = APIRouter(prefix="/api/conversations", tags=["Conversational Knowledge Chat"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreateRequest,
    x_user_id: str = Header(default="default_user")
):
    """Create a new grounded conversational chat session scoped to a Knowledge Item or Collection."""
    request.owner_id = x_user_id
    try:
        return conversation_service.create_conversation(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}"
        )


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(x_user_id: str = Header(default="default_user")):
    """List all active conversation sessions for the authorized user."""
    return conversation_service.list_conversations(owner_id=x_user_id)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, x_user_id: str = Header(default="default_user")):
    """Retrieve details for a specific conversation session."""
    conv = conversation_service.get_conversation(conversation_id, owner_id=x_user_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found or access denied."
        )
    return conv


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str, x_user_id: str = Header(default="default_user")):
    """Delete a conversation session and chat history. Does NOT delete library items or artifacts."""
    success = conversation_service.delete_conversation(conversation_id, owner_id=x_user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found or access denied."
        )
    return None


@router.get("/{conversation_id}/messages", response_model=List[ChatMessageResponse])
async def list_messages(conversation_id: str, x_user_id: str = Header(default="default_user")):
    """Fetch message history for a conversation session."""
    return conversation_service.list_messages(conversation_id, owner_id=x_user_id)


@router.post("/{conversation_id}/messages", response_model=ChatMessageResponse)
async def post_message(
    conversation_id: str,
    request: PostMessageRequest,
    x_user_id: str = Header(default="default_user")
):
    """
    Post a user question to the grounded chat session.
    Enforces maximum chat message length, retrieves saved knowledge context, and returns assistant message with citations.
    """
    # Enforce input size limit
    request.content = security_service.validate_chat_message(request.content)
    request.owner_id = x_user_id

    try:
        return conversation_service.post_message(conversation_id, request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}"
        )
