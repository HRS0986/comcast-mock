import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from openai import OpenAI, OpenAIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comcast_mock.config import settings
from comcast_mock.database import get_session
from comcast_mock.models import Embedding, KnowledgeBase
from comcast_mock.schemas import (
    EmbeddingCreateRequest,
    EmbeddingOut,
    ErrorResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["embeddings"])


def _get_openai_client() -> OpenAI:
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI API key not configured",
        )
    return OpenAI(api_key=settings.openai_api_key)


async def _create_embedding(text: str, client: OpenAI) -> list[float]:
    """Create embedding using OpenAI's text-embedding-3-small model."""
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding
    except OpenAIError as e:
        logger.exception("OpenAI embedding creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create embedding: {str(e)}",
        ) from e


@router.post(
    "/embeddings/upload",
    response_model=EmbeddingOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def upload_embedding(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Upload a markdown file and create an embedding.

    Args:
        file: Markdown file to embed
        session: Database session

    Returns:
        EmbeddingOut: Created embedding record with vector

    Raises:
        HTTPException: If file is not readable or embedding fails
    """
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".md"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .md files are accepted",
        )

    # Read file content
    try:
        content = await file.read()
        text_content = content.decode("utf-8")
    except Exception as e:
        logger.exception("Failed to read uploaded file")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}",
        ) from e

    # Create embedding
    client = _get_openai_client()
    embedding_vector = await _create_embedding(text_content, client)

    embedding = Embedding(
        filename=file.filename,
        content=text_content,
        embedding=embedding_vector,
        model="text-embedding-3-small",
    )
    session.add(embedding)
    await session.commit()
    await session.refresh(embedding)

    return embedding


@router.post(
    "/embeddings",
    response_model=EmbeddingOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_embedding(
    request: EmbeddingCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Create an embedding from markdown content.

    Args:
        request: Contains filename and content (markdown)
        session: Database session

    Returns:
        EmbeddingOut: Created embedding record with vector
    """
    client = _get_openai_client()

    embedding_vector = await _create_embedding(request.content, client)

    embedding = Embedding(
        filename=request.filename,
        content=request.content,
        embedding=embedding_vector,
        model="text-embedding-3-small",
    )
    session.add(embedding)
    await session.commit()
    await session.refresh(embedding)

    return embedding


@router.get(
    "/embeddings",
    response_model=list[EmbeddingOut],
    responses={
        200: {"description": "List of embeddings"},
    },
)
async def list_embeddings(
    session: AsyncSession = Depends(get_session),
    limit: int = 50,
    offset: int = 0,
) -> Any:
    """List all stored embeddings with pagination.

    Args:
        session: Database session
        limit: Number of embeddings to return (default 50, max 200)
        offset: Number of embeddings to skip (default 0)

    Returns:
        List of EmbeddingOut objects
    """
    query = select(Embedding).limit(limit).offset(offset)
    result = await session.execute(query)
    embeddings = result.scalars().all()
    return embeddings


@router.get(
    "/embeddings/{embedding_id}",
    response_model=EmbeddingOut,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def get_embedding(
    embedding_id: str,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Get a specific embedding by ID.

    Args:
        embedding_id: The embedding ID
        session: Database session

    Returns:
        EmbeddingOut: The embedding record

    Raises:
        HTTPException: If embedding not found
    """
    query = select(Embedding).where(Embedding.id == embedding_id)
    result = await session.execute(query)
    embedding = result.scalar_one_or_none()

    if not embedding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Embedding {embedding_id} not found",
        )

    return embedding


@router.delete(
    "/embeddings/{embedding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_embedding(
    embedding_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a specific embedding by ID.

    Args:
        embedding_id: The embedding ID
        session: Database session

    Raises:
        HTTPException: If embedding not found
    """
    query = select(Embedding).where(Embedding.id == embedding_id)
    result = await session.execute(query)
    embedding = result.scalar_one_or_none()

    if not embedding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Embedding {embedding_id} not found",
        )

    await session.delete(embedding)
    await session.commit()


@router.post(
    "/knowledge-base",
    response_model=KnowledgeBaseOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_knowledge_base_entry(
    request: KnowledgeBaseCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Create a knowledge base entry with embedding.

    Args:
        request: Contains sub_category_id, content, and optional metadata
        session: Database session

    Returns:
        KnowledgeBaseOut: Created knowledge base record with vector
    """
    client = _get_openai_client()
    embedding_vector = await _create_embedding(request.content, client)

    kb_entry = KnowledgeBase(
        sub_category_id=request.sub_category_id,
        content=request.content,
        embedding=embedding_vector,
        extra_metadata=request.metadata,
    )
    session.add(kb_entry)
    await session.commit()
    await session.refresh(kb_entry)

    return kb_entry


@router.get(
    "/knowledge-base",
    response_model=list[KnowledgeBaseOut],
    responses={
        200: {"description": "List of knowledge base entries"},
    },
)
async def list_knowledge_base(
    session: AsyncSession = Depends(get_session),
    sub_category_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Any:
    """List knowledge base entries with optional filtering.

    Args:
        session: Database session
        sub_category_id: Filter by integer sub-category id (optional)
        limit: Number of entries to return (default 50, max 200)
        offset: Number of entries to skip (default 0)

    Returns:
        List of KnowledgeBaseOut objects
    """
    query = select(KnowledgeBase)
    if sub_category_id is not None:
        query = query.where(KnowledgeBase.sub_category_id == sub_category_id)
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    entries = result.scalars().all()
    return entries


@router.get(
    "/knowledge-base/{entry_id}",
    response_model=KnowledgeBaseOut,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def get_knowledge_base_entry(
    entry_id: int,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Get a specific knowledge base entry by ID.

    Args:
        entry_id: The knowledge base entry ID
        session: Database session

    Returns:
        KnowledgeBaseOut: The knowledge base entry

    Raises:
        HTTPException: If entry not found
    """
    query = select(KnowledgeBase).where(KnowledgeBase.id == entry_id)
    result = await session.execute(query)
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base entry {entry_id} not found",
        )

    return entry


@router.delete(
    "/knowledge-base/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_knowledge_base_entry(
    entry_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a specific knowledge base entry by ID.

    Args:
        entry_id: The knowledge base entry ID
        session: Database session

    Raises:
        HTTPException: If entry not found
    """
    query = select(KnowledgeBase).where(KnowledgeBase.id == entry_id)
    result = await session.execute(query)
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base entry {entry_id} not found",
        )

    await session.delete(entry)
    await session.commit()


