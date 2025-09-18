"""Artifact Index Manager for ReSpecT

This module manages the index.md file structure and provides abstraction for
artifact index operations. The index tracks all artifacts in the repository
with their metadata in a structured format.

Current schema: ID,ARTIFACT_ID,NAME,STATUS,IS_FILE,PARENT
- ID: Sequential numeric ID
- ARTIFACT_ID: Full artifact ID (e.g., PRD-1, REQ-2)
- NAME: Human-readable artifact name
- STATUS: Current artifact status (optional)
- IS_FILE: Boolean flag indicating if artifact has its own file
- PARENT: Parent artifact ID for nested artifacts, null for top-level files
"""

import os
import fcntl
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class ArtifactIndexManager:
    """Manages the artifact index file (index.md) with schema abstraction."""
    
    # Schema definition - modify here for future schema changes
    SCHEMA_VERSION = "1.1"
    COLUMN_NAMES = ["ID", "ARTIFACT_ID", "NAME", "STATUS", "IS_FILE", "PARENT"]
    REQUIRED_COLUMNS = ["ID", "ARTIFACT_ID"]  # Minimum required columns
    
    # Column indices for easy access
    COL_ID = 0
    COL_ARTIFACT_ID = 1
    COL_NAME = 2
    COL_STATUS = 3
    COL_IS_FILE = 4
    COL_PARENT = 5
    
    def __init__(self, repo_root: str):
        """Initialize the artifact index manager.
        
        Args:
            repo_root: Path to the root of the ReSpecT repository
        """
        self.repo_root = Path(repo_root)
        self.index_file = self.repo_root / "index.md"
        
    def _ensure_index_file_exists(self) -> None:
        """Ensure the index.md file exists with proper initial content."""
        if not self.index_file.exists():
            # Create the repository root directory if it doesn't exist
            self.repo_root.mkdir(parents=True, exist_ok=True)
            
            # Create initial index.md with header
            initial_content = f"""# ReSpecT Artifact ID Index

This file tracks all artifacts in the ReSpecT repository with their metadata.
Schema Version: {self.SCHEMA_VERSION}

Format: {','.join(self.COLUMN_NAMES)}
- ID: Sequential numeric identifier
- ARTIFACT_ID: Full artifact ID (e.g., PRD-1, REQ-2)
- NAME: Human-readable artifact name (optional)
- STATUS: Current artifact status (optional)
- IS_FILE: true if artifact has own file, false if referenced only
- PARENT: Parent artifact ID for nested artifacts, null for top-level files

## Artifact Index

"""
            self.index_file.write_text(initial_content, encoding='utf-8')
            logger.info(f"Created initial index file at {self.index_file}")
    
    def _parse_index_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single index line into a structured dictionary.
        
        Args:
            line: Line from the index file
            
        Returns:
            Dictionary with parsed data or None if line is invalid
        """
        line = line.strip()
        if not line or ',' not in line:
            return None
        
        # Use proper CSV parsing to handle commas in values
        import csv
        import io
        
        try:
            # Parse the line as CSV
            csv_reader = csv.reader(io.StringIO(line))
            parts = next(csv_reader)
        except (csv.Error, StopIteration):
            # Fall back to simple split for backward compatibility
            parts = line.split(',')
            
        if len(parts) < len(self.REQUIRED_COLUMNS):
            return None
            
        # Ensure we have enough parts for all columns (pad with empty strings)
        while len(parts) < len(self.COLUMN_NAMES):
            parts.append("")
            
        # Parse and validate the data
        try:
            doc_id = parts[self.COL_ID].strip()
            if not doc_id.isdigit():
                return None
                
            artifact_id = parts[self.COL_ARTIFACT_ID].strip()
            if not artifact_id:
                return None
                
            name = parts[self.COL_NAME].strip() if parts[self.COL_NAME].strip() else None
            status = parts[self.COL_STATUS].strip() if parts[self.COL_STATUS].strip() else None
            
            # Parse IS_FILE - default to True for backward compatibility
            is_file_str = parts[self.COL_IS_FILE].strip().lower() if parts[self.COL_IS_FILE].strip() else "true"
            is_file = is_file_str in ("true", "1", "yes")
            
            # Parse PARENT - can be empty/null
            parent = parts[self.COL_PARENT].strip() if len(parts) > self.COL_PARENT and parts[self.COL_PARENT].strip() else None
            
            return {
                "doc_id": doc_id,
                "artifact_id": artifact_id,
                "name": name,
                "status": status,
                "is_file": is_file,
                "parent": parent
            }
            
        except (IndexError, ValueError):
            return None
    
    def _format_index_line(self, doc_id: str, artifact_id: str, name: Optional[str] = None, 
                          status: Optional[str] = None, is_file: bool = True, parent: Optional[str] = None) -> str:
        """Format data into an index line.
        
        Args:
            doc_id: Numeric document ID
            artifact_id: Full artifact ID
            name: Optional artifact name
            status: Optional status
            is_file: Whether artifact has its own file
            parent: Optional parent artifact ID
            
        Returns:
            Formatted line for the index
        """
        import csv
        import io
        
        # Use proper CSV formatting to handle commas in values
        output = io.StringIO()
        writer = csv.writer(output)
        
        parts = [
            doc_id,
            artifact_id,
            name or "",
            status or "",
            "true" if is_file else "false",
            parent or ""
        ]
        
        writer.writerow(parts)
        return output.getvalue().strip()  # Remove trailing newline
    
    def get_all_artifacts(self) -> List[Dict[str, Any]]:
        """Get all artifacts from the index.
        
        Returns:
            List of artifact dictionaries
        """
        if not self.index_file.exists():
            return []
            
        content = self.index_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        artifacts = []
        for line in lines:
            parsed = self._parse_index_line(line)
            if parsed:
                artifacts.append(parsed)
                
        return artifacts
    
    def get_artifact_by_id(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific artifact by its ID.
        
        Args:
            artifact_id: The artifact ID to find
            
        Returns:
            Artifact dictionary or None if not found
        """
        artifacts = self.get_all_artifacts()
        for artifact in artifacts:
            if artifact["artifact_id"].upper() == artifact_id.upper():
                return artifact
        return None
    
    def get_artifact_by_doc_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific artifact by its document ID.
        
        Args:
            doc_id: The document ID to find
            
        Returns:
            Artifact dictionary or None if not found
        """
        artifacts = self.get_all_artifacts()
        for artifact in artifacts:
            if artifact["doc_id"] == doc_id:
                return artifact
        return None
    
    def get_next_doc_id(self) -> int:
        """Get the next sequential document ID.
        
        Returns:
            The next sequential ID number
        """
        self._ensure_index_file_exists()
        
        artifacts = self.get_all_artifacts()
        if not artifacts:
            return 1
            
        # Find the highest doc_id
        max_id = 0
        for artifact in artifacts:
            try:
                doc_id = int(artifact["doc_id"])
                max_id = max(max_id, doc_id)
            except ValueError:
                continue
                
        return max_id + 1
    
    def add_artifact(self, artifact_id: str, name: Optional[str] = None, 
                    status: Optional[str] = None, is_file: bool = True, parent: Optional[str] = None) -> str:
        """Add a new artifact to the index.
        
        Args:
            artifact_id: The artifact ID to add
            name: Optional artifact name
            status: Optional status
            is_file: Whether artifact has its own file
            parent: Optional parent artifact ID
            
        Returns:
            The assigned document ID
            
        Raises:
            ValueError: If artifact already exists
        """
        # Check if artifact already exists
        existing = self.get_artifact_by_id(artifact_id)
        if existing:
            raise ValueError(f"Artifact {artifact_id} already exists")
        
        # Ensure the index file exists
        self._ensure_index_file_exists()
        
        # Use file locking to ensure thread safety
        with open(self.index_file, 'a+', encoding='utf-8') as f:
            try:
                # Acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                
                # Get the next ID
                next_id = self.get_next_doc_id()
                doc_id = str(next_id)
                
                # Format the new entry
                line = self._format_index_line(doc_id, artifact_id, name, status, is_file, parent)
                
                # Check if file is empty or contains only header - if so, don't add extra newline
                f.seek(0)
                content = f.read()
                needs_newline = content and not content.endswith('\n')
                
                # Go to end of file for appending
                f.seek(0, 2)
                
                if needs_newline:
                    f.write(f"\n{line}\n")
                else:
                    f.write(f"{line}\n")
                f.flush()
                
                logger.info(f"Added artifact to index: {artifact_id} (ID: {doc_id}, is_file: {is_file}, parent: {parent})")
                return doc_id
                
            finally:
                # Release the lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    def update_artifact(self, artifact_id: str, name: Optional[str] = None, 
                       status: Optional[str] = None, is_file: Optional[bool] = None, parent: Optional[str] = None) -> bool:
        """Update an existing artifact in the index.
        
        Args:
            artifact_id: The artifact ID to update
            name: New name (if provided)
            status: New status (if provided)
            is_file: New is_file flag (if provided)
            parent: New parent ID (if provided)
            
        Returns:
            True if updated, False if not found
        """
        if not self.index_file.exists():
            return False
        
        content = self.index_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        updated = False
        for i, line in enumerate(lines):
            parsed = self._parse_index_line(line)
            if parsed and parsed["artifact_id"].upper() == artifact_id.upper():
                # Update the fields that were provided
                if name is not None:
                    parsed["name"] = name
                if status is not None:
                    parsed["status"] = status
                if is_file is not None:
                    parsed["is_file"] = is_file
                if parent is not None:
                    parsed["parent"] = parent
                
                # Reformat the line
                lines[i] = self._format_index_line(
                    parsed["doc_id"], 
                    parsed["artifact_id"],
                    parsed["name"],
                    parsed["status"],
                    parsed["is_file"],
                    parsed["parent"]
                )
                updated = True
                break
        
        if updated:
            self.index_file.write_text('\n'.join(lines), encoding='utf-8')
            logger.info(f"Updated artifact in index: {artifact_id}")
        
        return updated
    
    def get_artifacts_by_filter(self, is_file: Optional[bool] = None, 
                               status: Optional[str] = None, parent: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get artifacts filtered by criteria.
        
        Args:
            is_file: Filter by is_file flag (None for no filter)
            status: Filter by status (None for no filter)
            parent: Filter by parent ID (None for no filter)
            
        Returns:
            List of matching artifacts
        """
        artifacts = self.get_all_artifacts()
        
        if is_file is not None:
            artifacts = [a for a in artifacts if a["is_file"] == is_file]
            
        if status is not None:
            artifacts = [a for a in artifacts if a["status"] == status]
            
        if parent is not None:
            artifacts = [a for a in artifacts if a["parent"] == parent]
            
        return artifacts

    def get_children_artifacts(self, parent_id: str) -> List[Dict[str, Any]]:
        """Get all child artifacts for a given parent.
        
        Args:
            parent_id: The parent artifact ID
            
        Returns:
            List of child artifacts
        """
        return self.get_artifacts_by_filter(parent=parent_id)


def get_artifact_index_manager(repo_root: Optional[str] = None) -> ArtifactIndexManager:
    """Factory function to create an ArtifactIndexManager instance.
    
    Args:
        repo_root: Path to the ReSpecT repository root. If None, uses RESPECT_DOC_REPO_ROOT env var.
        
    Returns:
        An ArtifactIndexManager instance
        
    Raises:
        ValueError: If repo_root is not provided and RESPECT_DOC_REPO_ROOT env var is not set
    """
    if repo_root is None:
        repo_root = os.getenv('RESPECT_DOC_REPO_ROOT')
        if not repo_root:
            raise ValueError("repo_root must be provided or RESPECT_DOC_REPO_ROOT environment variable must be set")
    
    return ArtifactIndexManager(repo_root)
