"""
Ingest Router - Document Upload and Vector Store Creation
"""

import logging
import uuid
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from app.services.openai_service import OpenAIService
from app.services.document_processor import DocumentProcessor
from app.models.responses import IngestResponse, FileUploadResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents(
    project_name: str = Form(
        ..., description="Project name for this Strategic Build Plan"
    ),
    files: List[UploadFile] = File(
        ..., description="Documents to ingest (PDF, DOCX, TXT)"
    ),
):
    """
    Ingest project documents and create a Vector Store for plan generation

    **Process:**
    1. Validate uploaded files
    2. Extract text from documents
    3. Upload files to OpenAI
    4. Create Vector Store with file search enabled
    5. Return session ID for draft generation

    **Supported file types:** PDF, DOCX, TXT
    **Max file size:** 50MB per file
    """
    try:
        # Validate inputs
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")

        if len(files) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 files per upload")

        # Initialize services
        openai_service = OpenAIService()
        doc_processor = DocumentProcessor()

        # Generate session ID
        session_id = f"session_{uuid.uuid4().hex[:12]}"

        # Process files
        file_responses: List[FileUploadResponse] = []
        uploaded_file_ids: List[str] = []
        successful = 0
        failed = 0

        for upload_file in files:
            try:
                # Read file content
                content = await upload_file.read()
                file_size = len(content)

                # Validate file
                is_valid, error_msg = doc_processor.validate_file(
                    upload_file.filename, file_size
                )

                if not is_valid:
                    logger.warning(
                        f"File validation failed: {upload_file.filename} - {error_msg}"
                    )
                    file_responses.append(
                        FileUploadResponse(
                            filename=upload_file.filename,
                            file_id="",
                            size_bytes=file_size,
                            error=error_msg,
                        )
                    )
                    failed += 1
                    continue

                # Process document to extract text (for metadata)
                import io

                file_obj = io.BytesIO(content)
                processed = await doc_processor.process_file(
                    file_obj, upload_file.filename
                )

                # Upload to OpenAI
                file_obj.seek(0)
                file_id = await openai_service.upload_file(
                    file=file_obj, filename=upload_file.filename
                )

                uploaded_file_ids.append(file_id)

                file_responses.append(
                    FileUploadResponse(
                        filename=upload_file.filename,
                        file_id=file_id,
                        size_bytes=file_size,
                        char_count=processed.get("char_count"),
                        word_count=processed.get("word_count"),
                    )
                )

                successful += 1
                logger.info(
                    f"Successfully processed: {upload_file.filename} ({file_size} bytes)"
                )

            except Exception as e:
                logger.error(f"Error processing {upload_file.filename}: {str(e)}")
                file_responses.append(
                    FileUploadResponse(
                        filename=upload_file.filename,
                        file_id="",
                        size_bytes=len(content) if "content" in locals() else 0,
                        error=str(e),
                    )
                )
                failed += 1

        # Check if any files were successfully uploaded
        if not uploaded_file_ids:
            raise HTTPException(
                status_code=400,
                detail="No files were successfully processed. Check error messages.",
            )

        # Create Vector Store
        vector_store_name = f"{project_name}_{session_id}"
        vector_store = await openai_service.create_vector_store(
            name=vector_store_name, file_ids=uploaded_file_ids
        )

        # Calculate expiration
        ttl_days = int(openai_service.vector_store_ttl_days)
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)

        logger.info(
            f"Ingestion complete for '{project_name}': "
            f"{successful} files uploaded, {failed} failed, "
            f"Vector Store: {vector_store.id}"
        )

        return IngestResponse(
            session_id=session_id,
            vector_store_id=vector_store.id,
            project_name=project_name,
            files_processed=file_responses,
            total_files=len(files),
            successful_uploads=successful,
            failed_uploads=failed,
            expires_at=expires_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/ingest/status/{session_id}")
async def get_ingest_status(session_id: str):
    """
    Get status of an ingestion session

    **Note:** This is a placeholder. In production, you'd store session data in a database.
    """
    # TODO: Implement session storage and retrieval
    return {
        "session_id": session_id,
        "status": "completed",
        "message": "Session tracking not yet implemented. Use the session_id from ingestion response.",
    }
