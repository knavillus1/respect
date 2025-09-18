"""Document Template Management for ReSpecT

This module provides document templates, prompts, and resources for creating
structured ReSpecT documents (PRD, TASKPRD, TASK, etc.).
"""

import os
from pathlib import Path
from typing import Dict, Optional
import logging

from .artifact_type_manager import get_artifact_type_manager

logger = logging.getLogger(__name__)


class DocumentTemplateManager:
    """Manages document templates for ReSpecT documents."""
    
    def __init__(self, template_store_path: Optional[str] = None):
        """Initialize the template manager.
        
        Args:
            template_store_path: Path to the template store directory. 
                If None, defaults to the package's templates directory.
        """
        if template_store_path is None:
            # Default to the templates directory relative to this file
            template_store_path = os.path.normpath(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates')
            )
        self.template_store_path = Path(template_store_path)
        if not self.template_store_path.exists():
            raise ValueError(f"Template store path does not exist: {self.template_store_path}")
        logger.info(f"Initialized DocumentTemplateManager with template store: {self.template_store_path}")
        
    def get_document_template(self, artifact_name: str) -> str:
        """Get a document template by artifact name.
        
        Args:
            artifact_name: The artifact type (e.g., 'PRD', 'TASKPRD', 'TASK', 'REQ')
            
        Returns:
            The template content as a string
            
        Raises:
            ValueError: If the artifact template is not found or artifact type is invalid
        """
        # Validate artifact type using the artifact type manager
        try:
            type_manager = get_artifact_type_manager()
            normalized_artifact_name = type_manager.validate_and_normalize_artifact_type(artifact_name)
            # Use the artifact name directly for template directory lookup, not the template_name format
            template_dir_name = normalized_artifact_name
        except ValueError as e:
            logger.error(f"Invalid artifact type '{artifact_name}': {e}")
            raise
        
        artifact_dir = self.template_store_path / template_dir_name
        template_file = artifact_dir / "template.md"
        
        if not template_file.exists():
            available_artifacts = [d.name for d in self.template_store_path.iterdir() if d.is_dir()]
            raise ValueError(f"Template not found for artifact '{artifact_name}' (template directory: {template_dir_name}). Available artifacts: {available_artifacts}")
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Successfully loaded template for artifact: {artifact_name}")
            return content
        except Exception as e:
            logger.error(f"Error reading template file {template_file}: {e}")
            raise ValueError(f"Failed to read template for artifact '{artifact_name}': {e}")


def get_template_manager(template_store_path: Optional[str] = None) -> DocumentTemplateManager:
    """Factory function to create a DocumentTemplateManager instance.
    
    Args:
        template_store_path: Path to the template store directory. If None, defaults to the package's templates directory.
        
    Returns:
        A DocumentTemplateManager instance
    """
    return DocumentTemplateManager(template_store_path)
