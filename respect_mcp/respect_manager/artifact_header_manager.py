"""Artifact Header Management for ReSpecT

This module manages artifact header lines including system-managed headers
based on the artifact_managed_header_items.json configuration.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from .artifact_type_manager import ArtifactTypeManager

logger = logging.getLogger(__name__)


class ArtifactHeaderManager:
    """Manages artifact header content including system-managed header items."""
    
    def __init__(self, config_path: Optional[str] = None, type_manager: Optional[ArtifactTypeManager] = None):
        """Initialize the artifact header manager.
        
        Args:
            config_path: Path to the artifact_managed_header_items.json config file.
                        If None, uses default location relative to this module.
            type_manager: Optional ArtifactTypeManager instance. If None, creates a new one.
        """
        if config_path is None:
            # Default to artifact_managed_header_items.json in the same directory as this module
            config_path = str(Path(__file__).parent / "artifact_managed_header_items.json")
        
        self.config_path = Path(config_path)
        
        if not self.config_path.exists():
            raise ValueError(f"Artifact header items config file not found: {self.config_path}")
        
        self.type_manager = type_manager or ArtifactTypeManager()
        self._config = self._load_config()
        
        logger.info(f"Initialized ArtifactHeaderManager with config: {self.config_path}")
    
    def _load_config(self) -> Dict:
        """Load the artifact managed header items configuration from JSON file.
        
        Returns:
            The parsed configuration dictionary
            
        Raises:
            ValueError: If the config file is invalid JSON or missing required fields
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate required top-level keys
            if 'managed_header_items' not in config:
                raise ValueError("Config file missing required 'managed_header_items' section")
            
            # Validate each header item has required fields
            for item_key, definition in config['managed_header_items'].items():
                required_fields = ['label', 'type', 'artifact_types']
                for field in required_fields:
                    if field not in definition:
                        raise ValueError(f"Header item '{item_key}' missing required field: {field}")
            
            logger.info(f"Successfully loaded {len(config['managed_header_items'])} managed header items")
            return config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in managed header items configuration: {e}")
        except Exception as e:
            raise ValueError(f"Error loading managed header items configuration: {e}")
    
    def extract_artifact_type_and_id(self, content: str) -> Optional[tuple[str, str]]:
        """Extract artifact type and ID from the first line of artifact content.
        
        Args:
            content: The full artifact content string
            
        Returns:
            Tuple of (artifact_type, artifact_id) if found, None otherwise
        """
        lines = content.strip().split('\n')
        if not lines:
            return None
            
        first_line = lines[0].strip()
        
        # Try to match against all known header formats
        for artifact_type, type_info in self.type_manager._config['artifact_types'].items():
            header_format = type_info.get('header_format', '')
            if not header_format:
                continue
                
            # Convert format template to regex pattern
            # e.g., "# PRD-{id}: {description}" -> r"# PRD-(\d+): (.+)"
            # e.g., "### REQ-{id}: {description}" -> r"### REQ-(\d+): (.+)"
            
            # Escape the format string and then replace the placeholders
            escaped_format = re.escape(header_format)
            # Replace escaped placeholders with regex groups
            pattern = escaped_format.replace(r'\{id\}', r'(\d+)').replace(r'\{description\}', r'(.+)')
            
            try:
                match = re.match(pattern, first_line)
                if match:
                    artifact_id = match.group(1)
                    return artifact_type, f"{artifact_type}-{artifact_id}"
            except re.error as e:
                logger.warning(f"Regex error for pattern '{pattern}': {e}")
                continue
        
        return None
    
    def get_managed_headers_for_type(self, artifact_type: str) -> Dict[str, Dict]:
        """Get all managed header items that apply to the given artifact type.
        
        Args:
            artifact_type: The artifact type to get headers for
            
        Returns:
            Dictionary of header item keys to their configuration
        """
        applicable_headers = {}
        
        for item_key, item_config in self._config['managed_header_items'].items():
            if artifact_type in item_config['artifact_types']:
                applicable_headers[item_key] = item_config
                
        return applicable_headers
    
    def parse_managed_headers(self, content: str) -> tuple[str, Dict[str, str], str]:
        """Parse artifact content to extract header line, managed headers, and body.
        
        Args:
            content: The full artifact content string
            
        Returns:
            Tuple of (header_line, managed_headers_dict, remaining_content)
        """
        lines = content.strip().split('\n')
        if not lines:
            return "", {}, ""
        
        header_line = lines[0].strip()
        managed_headers = {}
        body_start_index = 1
        
        # Extract artifact type to know which headers to look for
        artifact_info = self.extract_artifact_type_and_id(content)
        if not artifact_info:
            return header_line, {}, '\n'.join(lines[1:])
        
        artifact_type, _ = artifact_info
        applicable_headers = self.get_managed_headers_for_type(artifact_type)
        
        # Look for managed header lines (lines with backticks containing labels)
        for i in range(1, len(lines)):
            line = lines[i].strip()
            if not line:
                body_start_index = i + 1
                continue
                
            # Check if this line matches any managed header format: `Label`: value
            match = re.match(r'`([^`]+)`:\s*(.+)', line)
            if match:
                label, value = match.groups()
                
                # Find which header item this corresponds to
                header_found = False
                for item_key, item_config in applicable_headers.items():
                    if item_config['label'].rstrip(':') == label:
                        managed_headers[item_key] = value.strip()
                        header_found = True
                        body_start_index = i + 1
                        break
                
                # If this looks like a header but isn't managed, include it in body
                if not header_found:
                    break
            else:
                # If we hit a non-header line, stop looking
                break
        
        remaining_content = '\n'.join(lines[body_start_index:])
        return header_line, managed_headers, remaining_content
    
    def update_managed_header(self, content: str, header_updates: Dict[str, str]) -> str:
        """Update managed header values in artifact content.
        
        Args:
            content: The full artifact content string
            header_updates: Dictionary of header item keys to new values
            
        Returns:
            Updated artifact content with modified headers
        """
        # Parse the current content
        header_line, current_headers, body_content = self.parse_managed_headers(content)
        
        if not header_line:
            raise ValueError("Could not parse artifact header from content")
        
        # Extract artifact type
        artifact_info = self.extract_artifact_type_and_id(content)
        if not artifact_info:
            raise ValueError("Could not determine artifact type from content")
        
        artifact_type, _ = artifact_info
        applicable_headers = self.get_managed_headers_for_type(artifact_type)
        
        # Update headers
        updated_headers = current_headers.copy()
        
        for item_key, new_value in header_updates.items():
            if item_key not in applicable_headers:
                logger.warning(f"Header item '{item_key}' not applicable to artifact type '{artifact_type}'")
                continue
                
            item_config = applicable_headers[item_key]
            
            if item_config['type'] == 'atomic':
                # Atomic values replace existing value
                updated_headers[item_key] = new_value
            elif item_config['type'] == 'list':
                # List values append to existing value (comma-separated)
                if item_key in updated_headers:
                    existing_values = [v.strip() for v in updated_headers[item_key].split(',')]
                    new_values = [v.strip() for v in new_value.split(',')]
                    # Combine and deduplicate while preserving order
                    combined_values = existing_values.copy()
                    for val in new_values:
                        if val not in combined_values:
                            combined_values.append(val)
                    updated_headers[item_key] = ','.join(combined_values)
                else:
                    updated_headers[item_key] = new_value
        
        # Rebuild the content
        result_lines = [header_line]
        
        # Add managed headers in a consistent order (based on config order)
        for item_key, item_config in applicable_headers.items():
            if item_key in updated_headers:
                label = item_config['label']
                value = updated_headers[item_key]
                result_lines.append(f"`{label.rstrip(':')}`: {value}")
        
        # Add body content
        if body_content.strip():
            result_lines.append(body_content)
        
        return '\n'.join(result_lines)
    
    def get_header_format(self, artifact_type: str) -> Optional[str]:
        """Get the header format template for the given artifact type.
        
        Args:
            artifact_type: The artifact type
            
        Returns:
            Header format template string, or None if not found
        """
        type_info = self.type_manager.get_artifact_type_info(artifact_type)
        return type_info.get('header_format') if type_info else None
