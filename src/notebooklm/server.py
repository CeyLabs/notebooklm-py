"""FastAPI server for NotebookLM REST API.

This module provides a REST API server that exposes NotebookLM functionality
through HTTP endpoints protected by API key authentication.

Environment Variables:
    API_SECRET_KEY: Required API key for endpoint authentication
    NOTEBOOKLM_AUTH_JSON: Google auth credentials (storage_state.json as JSON string)
    PORT: Server port (default: 8000)
    HOST: Server host (default: 0.0.0.0)

Example Usage:
    # Start server
    uvicorn notebooklm.server:app --host 0.0.0.0 --port 8000

    # Test health endpoint
    curl http://localhost:8000/health

    # Create notebook
    curl -X POST http://localhost:8000/api/notebooks/create \\
      -H "X-API-Key: your-key" \\
      -H "Content-Type: application/json" \\
      -d '{"title": "My Research"}'

    # Add source
    curl -X POST http://localhost:8000/api/sources/add \\
      -H "X-API-Key: your-key" \\
      -H "Content-Type: application/json" \\
      -d '{"notebook_id": "...", "url": "https://example.com"}'
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl

from notebooklm import NotebookLMClient
from notebooklm.auth import AuthTokens
from notebooklm.exceptions import (
    AuthError,
    NotebookLMError,
    NotebookNotFoundError,
    SourceAddError,
    ValidationError,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Configuration ---

API_SECRET_KEY = os.getenv("API_SECRET_KEY")
NOTEBOOKLM_AUTH_JSON = os.getenv("NOTEBOOKLM_AUTH_JSON")
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")


# --- Request/Response Models ---


class CreateNotebookRequest(BaseModel):
    """Request model for creating a notebook."""

    title: str = Field(..., description="Title of the notebook", min_length=1, max_length=500)


class CreateNotebookResponse(BaseModel):
    """Response model for creating a notebook."""

    notebook_id: str = Field(..., description="ID of the created notebook")
    title: str = Field(..., description="Title of the notebook")


class AddSourceRequest(BaseModel):
    """Request model for adding a source to a notebook."""

    notebook_id: str = Field(..., description="ID of the target notebook")
    url: HttpUrl = Field(..., description="URL to add as a source")


class AddSourceResponse(BaseModel):
    """Response model for adding a source."""

    source_id: str = Field(..., description="ID of the added source")
    title: str = Field(..., description="Title of the source")
    status: str = Field(..., description="Processing status of the source")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Server status")
    authenticated: bool = Field(..., description="Whether NotebookLM client is authenticated")


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Additional error details")


# --- Application Lifespan ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - initialize and cleanup NotebookLM client."""
    logger.info("Initializing NotebookLM client...")

    # Validate required environment variables
    if not API_SECRET_KEY:
        logger.error("API_SECRET_KEY environment variable is not set")
        raise RuntimeError(
            "API_SECRET_KEY environment variable is required. "
            "Set it to a secure random string (min 32 characters)."
        )

    if not NOTEBOOKLM_AUTH_JSON:
        logger.error("NOTEBOOKLM_AUTH_JSON environment variable is not set")
        raise RuntimeError(
            "NOTEBOOKLM_AUTH_JSON environment variable is required. "
            "Set it to the contents of your ~/.notebooklm/storage_state.json file."
        )

    try:
        # Parse and validate auth JSON
        auth_data = json.loads(NOTEBOOKLM_AUTH_JSON)

        # Create temporary file for auth data
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(auth_data, f)
            temp_auth_path = Path(f.name)

        try:
            # Load auth from temporary file
            auth_tokens = await AuthTokens.from_storage(path=temp_auth_path)
        finally:
            # Clean up temporary file
            temp_auth_path.unlink(missing_ok=True)

        # Initialize client
        client = NotebookLMClient(auth=auth_tokens)
        await client.__aenter__()

        # Store in app state
        app.state.client = client
        logger.info("NotebookLM client initialized successfully")

        yield

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse NOTEBOOKLM_AUTH_JSON: {e}")
        raise RuntimeError(
            f"Invalid NOTEBOOKLM_AUTH_JSON format: {e}. "
            "Ensure it contains valid JSON from storage_state.json"
        )
    except Exception as e:
        logger.error(f"Failed to initialize NotebookLM client: {e}")
        raise
    finally:
        # Cleanup client
        if hasattr(app.state, "client"):
            try:
                await app.state.client.__aexit__(None, None, None)
                logger.info("NotebookLM client closed")
            except Exception as e:
                logger.error(f"Error closing NotebookLM client: {e}")


app = FastAPI(
    title="NotebookLM API",
    description="REST API for Google NotebookLM automation",
    version="1.0.0",
    lifespan=lifespan,
)


# --- Authentication ---


async def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    """Verify API key from request header.

    Args:
        x_api_key: API key from X-API-Key header

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header.",
        )

    if x_api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


# --- Helper Functions ---


def get_client() -> NotebookLMClient:
    """Get NotebookLM client from app state.

    Returns:
        NotebookLMClient instance

    Raises:
        HTTPException: If client is not initialized
    """
    if not hasattr(app.state, "client"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NotebookLM client not initialized",
        )
    return app.state.client


def error_response(error: Exception, status_code: int = 500) -> JSONResponse:
    """Create error response from exception.

    Args:
        error: Exception to convert
        status_code: HTTP status code

    Returns:
        JSONResponse with error details
    """
    error_msg = str(error)
    detail = None

    # Extract additional details for known error types
    if isinstance(error, NotebookLMError):
        detail = error.__class__.__name__

    return JSONResponse(
        status_code=status_code,
        content={"error": error_msg, "detail": detail},
    )


# --- Health Check Endpoint ---


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> dict[str, Any]:
    """Check server health and authentication status.

    Returns:
        Health status with authentication state

    Example:
        ```bash
        curl http://localhost:8000/health
        ```
    """
    authenticated = False

    try:
        client = get_client()
        # Test authentication by fetching notebooks
        await client.notebooks.list()
        authenticated = True
    except Exception as e:
        logger.warning(f"Health check authentication test failed: {e}")

    return {"status": "ok", "authenticated": authenticated}


# --- Notebook Endpoints ---


@app.post(
    "/api/notebooks/create",
    response_model=CreateNotebookResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
    tags=["Notebooks"],
)
async def create_notebook(request: CreateNotebookRequest) -> dict[str, Any]:
    """Create a new notebook.

    Args:
        request: Notebook creation request with title

    Returns:
        Created notebook details

    Raises:
        HTTPException: If creation fails

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/notebooks/create \\
          -H "X-API-Key: your-key" \\
          -H "Content-Type: application/json" \\
          -d '{"title": "My Research"}'
        ```
    """
    try:
        client = get_client()
        notebook = await client.notebooks.create(title=request.title)

        return {
            "notebook_id": notebook.id,
            "title": notebook.title,
        }

    except ValidationError as e:
        logger.error(f"Validation error creating notebook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except AuthError as e:
        logger.error(f"Authentication error creating notebook: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NotebookLM authentication failed. Check NOTEBOOKLM_AUTH_JSON.",
        )
    except NotebookLMError as e:
        logger.error(f"Error creating notebook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# --- Source Endpoints ---


@app.post(
    "/api/sources/add",
    response_model=AddSourceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
    tags=["Sources"],
)
async def add_source(request: AddSourceRequest) -> dict[str, Any]:
    """Add a URL source to a notebook.

    Args:
        request: Source addition request with notebook_id and url

    Returns:
        Added source details

    Raises:
        HTTPException: If addition fails

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/sources/add \\
          -H "X-API-Key: your-key" \\
          -H "Content-Type: application/json" \\
          -d '{"notebook_id": "abc123", "url": "https://example.com"}'
        ```
    """
    try:
        client = get_client()
        source = await client.sources.add_url(
            notebook_id=request.notebook_id,
            url=str(request.url),
        )

        return {
            "source_id": source.id,
            "title": source.title,
            "status": source.status.value if hasattr(source.status, "value") else str(source.status),
        }

    except NotebookNotFoundError as e:
        logger.error(f"Notebook not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notebook not found: {request.notebook_id}",
        )
    except SourceAddError as e:
        logger.error(f"Error adding source: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValidationError as e:
        logger.error(f"Validation error adding source: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except AuthError as e:
        logger.error(f"Authentication error adding source: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NotebookLM authentication failed. Check NOTEBOOKLM_AUTH_JSON.",
        )
    except NotebookLMError as e:
        logger.error(f"Error adding source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# --- Root Endpoint ---


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information.

    Returns:
        API name and documentation URL
    """
    return {
        "name": "NotebookLM API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "notebooklm.server:app",
        host=HOST,
        port=PORT,
        reload=False,
    )
