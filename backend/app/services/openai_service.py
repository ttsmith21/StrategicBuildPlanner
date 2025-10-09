"""
OpenAI Service - Vector Store and Responses API Integration
"""

import os
import logging
from typing import List, Optional, BinaryIO
from datetime import datetime, timedelta
from openai import OpenAI
from openai.types.beta.vector_store import VectorStore
from openai.types.beta.threads.run import Run

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for managing OpenAI Vector Stores and Responses API calls"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL_PLAN", "gpt-4o-2024-08-06")
        self.vector_store_ttl_days = int(os.getenv("VECTOR_STORE_TTL_DAYS", "7"))
        
    async def create_vector_store(
        self,
        name: str,
        file_ids: Optional[List[str]] = None
    ) -> VectorStore:
        """
        Create a new Vector Store for file search
        
        Args:
            name: Name for the vector store (e.g., project name)
            file_ids: Optional list of already-uploaded file IDs
            
        Returns:
            VectorStore object with ID
        """
        try:
            # Calculate expiration (auto-delete after TTL days)
            expires_after_days = self.vector_store_ttl_days
            
            # Create vector store
            vector_store = self.client.beta.vector_stores.create(
                name=name,
                file_ids=file_ids or [],
                expires_after={
                    "anchor": "last_active_at",
                    "days": expires_after_days
                }
            )
            
            logger.info(
                f"Created Vector Store: {vector_store.id} "
                f"(expires in {expires_after_days} days)"
            )
            
            return vector_store
            
        except Exception as e:
            logger.error(f"Failed to create Vector Store: {str(e)}")
            raise
    
    async def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        purpose: str = "assistants"
    ) -> str:
        """
        Upload a file to OpenAI
        
        Args:
            file: File object (binary mode)
            filename: Original filename
            purpose: Purpose for upload (default: "assistants")
            
        Returns:
            File ID string
        """
        try:
            uploaded_file = self.client.files.create(
                file=(filename, file),
                purpose=purpose
            )
            
            logger.info(f"Uploaded file: {filename} -> {uploaded_file.id}")
            return uploaded_file.id
            
        except Exception as e:
            logger.error(f"Failed to upload file {filename}: {str(e)}")
            raise
    
    async def add_files_to_vector_store(
        self,
        vector_store_id: str,
        file_ids: List[str]
    ) -> None:
        """
        Add files to an existing Vector Store
        
        Args:
            vector_store_id: Vector Store ID
            file_ids: List of file IDs to add
        """
        try:
            batch = self.client.beta.vector_stores.file_batches.create(
                vector_store_id=vector_store_id,
                file_ids=file_ids
            )
            
            logger.info(
                f"Added {len(file_ids)} files to Vector Store {vector_store_id}"
            )
            
            # Wait for processing to complete
            while batch.status == "in_progress":
                batch = self.client.beta.vector_stores.file_batches.retrieve(
                    vector_store_id=vector_store_id,
                    batch_id=batch.id
                )
                
            if batch.status == "failed":
                logger.error(f"File batch processing failed: {batch}")
                raise Exception("File batch processing failed")
                
            logger.info(f"File batch processing complete: {batch.status}")
            
        except Exception as e:
            logger.error(f"Failed to add files to Vector Store: {str(e)}")
            raise
    
    async def generate_plan(
        self,
        vector_store_id: str,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[dict] = None,
        max_tokens: int = 16000
    ) -> dict:
        """
        Generate a Strategic Build Plan using Responses API
        
        Args:
            vector_store_id: Vector Store ID containing project documents
            system_prompt: System instructions for the model
            user_prompt: User query (e.g., project details)
            response_format: Optional JSON schema for structured output
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated plan as dictionary (parsed JSON)
        """
        try:
            # Create a thread
            thread = self.client.beta.threads.create(
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [vector_store_id]
                    }
                }
            )
            
            # Add user message
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_prompt
            )
            
            # Run with assistant capabilities
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=None,  # We'll use inline assistant config
                model=self.model,
                instructions=system_prompt,
                tools=[{"type": "file_search"}],
                response_format=response_format or {"type": "text"},
                max_prompt_tokens=max_tokens,
                max_completion_tokens=max_tokens
            )
            
            # Wait for completion
            while run.status in ["queued", "in_progress"]:
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            if run.status != "completed":
                logger.error(f"Run failed with status: {run.status}")
                raise Exception(f"Run failed: {run.status}")
            
            # Get the response
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id,
                order="desc",
                limit=1
            )
            
            response_content = messages.data[0].content[0].text.value
            
            logger.info(f"Generated plan (thread: {thread.id})")
            
            # Parse JSON if structured output was requested
            if response_format and response_format.get("type") == "json_object":
                import json
                return json.loads(response_content)
            
            return {"content": response_content}
            
        except Exception as e:
            logger.error(f"Failed to generate plan: {str(e)}")
            raise
    
    async def delete_vector_store(self, vector_store_id: str) -> None:
        """
        Manually delete a Vector Store
        
        Args:
            vector_store_id: Vector Store ID to delete
        """
        try:
            self.client.beta.vector_stores.delete(vector_store_id)
            logger.info(f"Deleted Vector Store: {vector_store_id}")
        except Exception as e:
            logger.error(f"Failed to delete Vector Store: {str(e)}")
            raise
    
    async def list_vector_stores(self) -> List[VectorStore]:
        """List all Vector Stores"""
        try:
            stores = self.client.beta.vector_stores.list()
            return list(stores.data)
        except Exception as e:
            logger.error(f"Failed to list Vector Stores: {str(e)}")
            raise
