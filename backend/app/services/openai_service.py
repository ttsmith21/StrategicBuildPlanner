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
        Generate a Strategic Build Plan using Chat Completions with file_search

        Args:
            vector_store_id: Vector Store ID containing project documents
            system_prompt: System instructions for the model
            user_prompt: User query (e.g., project details)
            response_format: Optional JSON schema for structured output
            max_tokens: Maximum tokens in response

        Returns:
            Generated plan as dictionary (parsed JSON)
        """
        import json

        try:
            # Use Chat Completions API with file_search tool
            logger.info(f"Generating plan with model: {self.model}")

            # Build the request
            request_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "tools": [
                    {
                        "type": "file_search",
                        "file_search": {
                            "vector_store_ids": [vector_store_id]
                        }
                    }
                ],
                "max_tokens": max_tokens
            }

            # Add response format if specified
            if response_format:
                request_params["response_format"] = response_format

            response = self.client.chat.completions.create(**request_params)

            response_content = response.choices[0].message.content

            logger.info(f"Generated plan successfully (model: {self.model})")

            # Parse JSON if structured output was requested
            if response_format and response_format.get("type") == "json_object":
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
