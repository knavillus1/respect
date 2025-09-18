"""Artifact Type Management for ReSpecT

This module manages artifact type definitions, validation, and naming patterns.
Artifact types are configured in artifact_types.json for flexibility.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
import logging

logger = logging.getLogger(__name__)


class ArtifactTypeManager:
    """Manages artifact type definitions and naming patterns."""
    
    def can_tool_update(self, artifact_type: str) -> bool:
        """Return True if the artifact type can be directly updated by tools, else False.
        Args:
            artifact_type: The artifact type to check
        Returns:
            True if can_tool_update is set to true for this type, else False
        """
        artifact_type = artifact_type.upper()
        info = self.get_artifact_type_info(artifact_type)
        return bool(info.get("can_tool_update", False))
    
    def has_capability(self, artifact_type: str, capability: str) -> bool:
        """Return True if the artifact type has the specified capability.
        Args:
            artifact_type: The artifact type to check
            capability: The capability to check for (e.g., 'has_steps', 'can_tool_update')
        Returns:
            True if the capability is set to true for this type, else False
        """
        artifact_type = artifact_type.upper()
        info = self.get_artifact_type_info(artifact_type)
        return bool(info.get(capability, False))
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the artifact type manager.
        
        Args:
            config_path: Path to the artifact_types.json config file.
                        If None, uses default location relative to this module.
        """
        if config_path is None:
            # Default to artifact_types.json in the same directory as this module
            config_path = str(Path(__file__).parent / "artifact_types.json")
        
        self.config_path = Path(config_path)
        
        if not self.config_path.exists():
            raise ValueError(f"Artifact types config file not found: {self.config_path}")
        
        # Load status configuration
        self.status_config_path = self.config_path.parent / "artifact_statuses.json"
        
        self._config = self._load_config()
        self._status_config = self._load_status_config()
        logger.info(f"Initialized ArtifactTypeManager with config: {self.config_path}")
        logger.info(f"Loaded status config: {self.status_config_path}")
        
    def _load_config(self) -> Dict:
        """Load the artifact types configuration from JSON file.
        
        Returns:
            The parsed configuration dictionary
            
        Raises:
            ValueError: If the config file is invalid JSON or missing required fields
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate required top-level keys
            if 'artifact_types' not in config:
                raise ValueError("Config file missing required 'artifact_types' section")
            
            # Validate each artifact type has required fields
            for artifact_type, definition in config['artifact_types'].items():
                required_fields = ['name', 'description', 'template_name']
                for field in required_fields:
                    if field not in definition:
                        raise ValueError(f"Artifact type '{artifact_type}' missing required field: {field}")
            
            logger.info(f"Successfully loaded {len(config['artifact_types'])} artifact types")
            return config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in artifact types configuration: {e}")
        except Exception as e:
            raise ValueError(f"Error loading artifact types configuration: {e}")
    
    def _load_status_config(self) -> Dict:
        """Load the artifact status configuration from JSON file.
        
        Returns:
            The parsed status configuration dictionary
            
        Raises:
            ValueError: If the status config file is invalid JSON or missing required fields
        """
        try:
            if not self.status_config_path.exists():
                # Create default status config if it doesn't exist
                default_statuses = {
                    "statuses": {
                        "DRAFT": {"name": "Draft", "description": "Initial draft version, work in progress"},
                        "REVIEW": {"name": "Under Review", "description": "Ready for review and feedback"},
                        "APPROVED": {"name": "Approved", "description": "Reviewed and approved for implementation"},
                        "ACTIVE": {"name": "Active", "description": "Currently active and in use"},
                        "COMPLETED": {"name": "Completed", "description": "Work completed successfully"},
                        "CANCELLED": {"name": "Cancelled", "description": "Cancelled or abandoned"},
                        "ARCHIVED": {"name": "Archived", "description": "Archived for historical reference"}
                    }
                }
                with open(self.status_config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_statuses, f, indent=2)
                logger.info(f"Created default status config at {self.status_config_path}")
            
            with open(self.status_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate required top-level keys
            if 'statuses' not in config:
                raise ValueError("Status config file missing required 'statuses' section")
            
            logger.info(f"Successfully loaded {len(config['statuses'])} status definitions")
            return config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in status configuration: {e}")
        except Exception as e:
            raise ValueError(f"Error loading status configuration: {e}")
    
    def get_valid_artifact_types(self) -> List[str]:
        """Get a list of all valid artifact types.
        
        Returns:
            List of valid artifact type codes (e.g., ['PRD', 'TASKPRD', 'REQ','TASK'])
        """
        return list(self._config['artifact_types'].keys())
    
    def is_valid_artifact_type(self, artifact_type: str) -> bool:
        """Check if an artifact type is valid.
        
        Args:
            artifact_type: The artifact type to validate
            
        Returns:
            True if the artifact type is valid, False otherwise
        """
        return artifact_type.upper() in self._config['artifact_types']
    
    def get_artifact_type_info(self, artifact_type: str) -> Dict:
        """Get detailed information about an artifact type.
        
        Args:
            artifact_type: The artifact type to get info for
            
        Returns:
            Dictionary containing name, description, file_pattern, and template_name
            
        Raises:
            ValueError: If the artifact type is not valid
        """
        artifact_type = artifact_type.upper()
        if not self.is_valid_artifact_type(artifact_type):
            valid_types = self.get_valid_artifact_types()
            raise ValueError(f"Invalid artifact type '{artifact_type}'. Valid types: {valid_types}")
        
        return self._config['artifact_types'][artifact_type].copy()
    
    def get_template_name(self, artifact_type: str) -> str:
        """Get the template name for an artifact type.
        
        Args:
            artifact_type: The artifact type
            
        Returns:
            The template name to use for this artifact type
            
        Raises:
            ValueError: If the artifact type is not valid
        """
        info = self.get_artifact_type_info(artifact_type)
        return info['template_name']

    def get_header_format(self, artifact_type: str) -> Optional[str]:
        """Get the header format template for an artifact type.
        
        Args:
            artifact_type: The artifact type
            
        Returns:
            The header format template string, or None if not defined
            
        Raises:
            ValueError: If the artifact type is not valid
        """
        info = self.get_artifact_type_info(artifact_type)
        return info.get('header_format')

    def get_artifact_type_from_id(self, artifact_id: str) -> str:
        """Extract and validate the artifact type from a full artifact ID.

        Args:
            artifact_id: Full ID like "PRD-1" or "TASKPRD-12"

        Returns:
            Normalized artifact type (uppercase)

        Raises:
            ValueError: If the ID format is invalid or type is unknown
        """
        import re as _re
        if not artifact_id or not isinstance(artifact_id, str):
            raise ValueError("artifact_id must be a non-empty string")
        match = _re.match(r"^([A-Z]+)-\d+$", artifact_id.upper())
        if not match:
            raise ValueError(f"Invalid artifact ID format: {artifact_id}")
        artifact_type = match.group(1)
        return self.validate_and_normalize_artifact_type(artifact_type)
    
    def validate_and_normalize_artifact_type(self, artifact_type: str) -> str:
        """Validate and normalize an artifact type string.
        
        Args:
            artifact_type: The artifact type to validate and normalize
            
        Returns:
            The normalized (uppercase) artifact type
            
        Raises:
            ValueError: If the artifact type is not valid
        """
        if not artifact_type or not artifact_type.strip():
            raise ValueError("Artifact type cannot be empty")
        
        normalized = artifact_type.strip().upper()
        
        if not self.is_valid_artifact_type(normalized):
            valid_types = self.get_valid_artifact_types()
            raise ValueError(f"Invalid artifact type '{artifact_type}'. Valid types: {valid_types}")
        
        return normalized
    
    def get_all_artifact_types_info(self) -> Dict[str, Dict]:
        """Get information about all configured artifact types.
        
        Returns:
            Dictionary mapping artifact type codes to their info dictionaries
        """
        return {k: v.copy() for k, v in self._config['artifact_types'].items()}
    
    def find_provisional_artifact_ids(self, text: str) -> Set[str]:
        """Find all provisional artifact IDs in the given text.
        
        Args:
            text: The text to search for provisional artifact IDs
            
        Returns:
            Set of provisional artifact IDs found in the text
        """
        provisional_ids = set()
        valid_types = self.get_valid_artifact_types()
        
        # Create pattern for any valid artifact type followed by -PROVISIONAL and digits
        pattern = r'\b(' + '|'.join(re.escape(t) for t in valid_types) + r')-PROVISIONAL\d+\b'
        
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in re.finditer(pattern, text, re.IGNORECASE):
            provisional_ids.add(match.group(0).upper())
        
        return provisional_ids
    
    def parse_provisional_id(self, provisional_id: str) -> Tuple[str, int]:
        """Parse a provisional artifact ID into its components.
        
        Args:
            provisional_id: The provisional ID to parse (e.g., "PRD-PROVISIONAL1")
            
        Returns:
            Tuple of (artifact_type, temp_id)
            
        Raises:
            ValueError: If the provisional ID format is invalid
        """
        pattern = r'^([A-Z]+)-PROVISIONAL(\d+)$'
        match = re.match(pattern, provisional_id.upper())
        
        if not match:
            raise ValueError(f"Invalid provisional ID format: {provisional_id}")
        
        artifact_type = match.group(1)
        temp_id = int(match.group(2))
        
        # Validate the artifact type
        if not self.is_valid_artifact_type(artifact_type):
            valid_types = self.get_valid_artifact_types()
            raise ValueError(f"Invalid artifact type '{artifact_type}' in provisional ID. Valid types: {valid_types}")
        
        return artifact_type, temp_id
    
    def get_valid_statuses(self) -> List[str]:
        """Get a list of all valid artifact statuses.
        
        Returns:
            List of valid status codes (e.g., ['DRAFT', 'REVIEW', 'APPROVED'])
        """
        return list(self._status_config['statuses'].keys())
    
    def get_valid_statuses_for_type(self, artifact_type: str) -> List[str]:
        """Get a list of valid statuses for a specific artifact type.
        
        Args:
            artifact_type: The artifact type to get valid statuses for
            
        Returns:
            List of valid status codes for this artifact type
            Falls back to global statuses if type-specific ones aren't defined
        """
        artifact_type = artifact_type.upper()
        type_info = self.get_artifact_type_info(artifact_type)
        
        # Check if type has specific valid_statuses defined
        if 'valid_statuses' in type_info:
            return type_info['valid_statuses']
        
        # Fall back to global statuses
        return self.get_valid_statuses()
    
    def is_valid_status(self, status: str) -> bool:
        """Check if a status is valid.
        
        Args:
            status: The status to validate
            
        Returns:
            True if the status is valid, False otherwise
        """
        return status.upper() in self._status_config['statuses']
    
    def is_valid_status_for_type(self, status: str, artifact_type: str) -> bool:
        """Check if a status is valid for a specific artifact type.
        
        Args:
            status: The status to validate
            artifact_type: The artifact type to check against
            
        Returns:
            True if the status is valid for this artifact type, False otherwise
        """
        valid_statuses = self.get_valid_statuses_for_type(artifact_type)
        return status.upper() in valid_statuses
    
    def get_status_info(self, status: str) -> Dict:
        """Get detailed information about a status.
        
        Args:
            status: The status to get info for
            
        Returns:
            Dictionary containing name and description
            
        Raises:
            ValueError: If the status is not valid
        """
        status_upper = status.upper()
        if not self.is_valid_status(status_upper):
            valid_statuses = self.get_valid_statuses()
            raise ValueError(f"Invalid status '{status}'. Valid statuses: {valid_statuses}")
        
        return self._status_config['statuses'][status_upper]
    
    def get_all_statuses_info(self) -> Dict:
        """Get information about all valid statuses.
        
        Returns:
            Dictionary mapping status codes to their information
        """
        return self._status_config['statuses']
    
    def validate_and_normalize_status(self, status: str) -> str:
        """Validate and normalize a status.
        
        Args:
            status: The status to validate and normalize
            
        Returns:
            The normalized status (uppercase)
            
        Raises:
            ValueError: If the status is not valid
        """
        status_upper = status.upper()
        if not self.is_valid_status(status_upper):
            valid_statuses = self.get_valid_statuses()
            raise ValueError(f"Invalid status '{status}'. Valid statuses: {valid_statuses}")
        
        return status_upper
    
    def validate_and_normalize_status_for_type(self, status: str, artifact_type: str) -> str:
        """Validate and normalize a status for a specific artifact type.
        
        Args:
            status: The status to validate and normalize
            artifact_type: The artifact type to validate against
            
        Returns:
            The normalized status (uppercase)
            
        Raises:
            ValueError: If the status is not valid for this artifact type
        """
        status_upper = status.upper()
        if not self.is_valid_status_for_type(status_upper, artifact_type):
            valid_statuses = self.get_valid_statuses_for_type(artifact_type)
            raise ValueError(f"Invalid status '{status}' for artifact type '{artifact_type}'. Valid statuses: {valid_statuses}")
        
        return status_upper
    
    def validate_artifact_id_format(self, artifact_id: str) -> Dict[str, Any]:
        """Validate an artifact ID format and return detailed validation results.
        
        This method provides comprehensive validation of artifact IDs, checking:
        - Basic format requirements (TYPE-NUMBER pattern)
        - Valid artifact type
        - Proper numeric component
        
        Args:
            artifact_id: The artifact ID to validate (e.g., "PRD-1", "TASKPRD-12")
            
        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "artifact_id": str,
                "artifact_type": str or None,
                "number": int or None,
                "error": str or None,
                "suggestions": List[str] or None
            }
        """
        result = {
            "valid": False,
            "artifact_id": artifact_id,
            "artifact_type": None,
            "number": None,
            "error": None,
            "suggestions": None
        }
        
        try:
            # Basic validation
            if not artifact_id or not isinstance(artifact_id, str):
                result["error"] = "Artifact ID must be a non-empty string"
                return result
            
            artifact_id = artifact_id.strip()
            if not artifact_id:
                result["error"] = "Artifact ID cannot be empty or whitespace"
                return result
            
            # Check basic format: TYPE-NUMBER
            match = re.match(r"^([A-Z]+)-(\d+)$", artifact_id.upper())
            if not match:
                result["error"] = f"Invalid artifact ID format. Expected format: TYPE-NUMBER (e.g., PRD-1, TASKPRD-12)"
                
                # Provide suggestions based on common patterns
                suggestions = []
                valid_types = self.get_valid_artifact_types()
                
                # Check if it's just a type without number
                if artifact_id.upper() in valid_types:
                    suggestions.append(f"Did you mean '{artifact_id.upper()}-1'?")
                
                # Check if it's close to a valid type
                for valid_type in valid_types:
                    if artifact_id.upper().startswith(valid_type):
                        suggestions.append(f"Did you mean '{valid_type}-1'?")
                
                if not suggestions:
                    suggestions.append(f"Valid artifact types: {', '.join(valid_types)}")
                    suggestions.append("Example valid IDs: PRD-1, TASKPRD-12, REQ-5, TASK-3")
                
                result["suggestions"] = suggestions
                return result
            
            artifact_type = match.group(1)
            number = int(match.group(2))
            
            # Validate artifact type
            if not self.is_valid_artifact_type(artifact_type):
                valid_types = self.get_valid_artifact_types()
                result["error"] = f"Invalid artifact type '{artifact_type}'. Valid types: {', '.join(valid_types)}"
                
                # Suggest closest match
                suggestions = []
                for valid_type in valid_types:
                    if artifact_type in valid_type or valid_type in artifact_type:
                        suggestions.append(f"Did you mean '{valid_type}-{number}'?")
                
                if not suggestions:
                    suggestions.append(f"Example valid IDs: {', '.join([f'{t}-{number}' for t in valid_types[:3]])}")
                
                result["suggestions"] = suggestions
                return result
            
            # Validate number
            if number <= 0:
                result["error"] = f"Artifact number must be positive, got: {number}"
                result["suggestions"] = [f"Try '{artifact_type}-1' instead"]
                return result
            
            # If we get here, everything is valid
            result["valid"] = True
            result["artifact_type"] = artifact_type
            result["number"] = number
            
            return result
            
        except Exception as e:
            result["error"] = f"Unexpected error validating artifact ID: {str(e)}"
            return result
    
    def validate_artifact_id(self, artifact_id: str) -> str:
        """Validate an artifact ID format and return the normalized ID.
        
        This is a convenience method that validates the format and returns
        the normalized artifact ID or raises an exception with helpful details.
        
        Args:
            artifact_id: The artifact ID to validate
            
        Returns:
            The normalized artifact ID (uppercase)
            
        Raises:
            ValueError: If the artifact ID is invalid, with detailed error message
        """
        validation = self.validate_artifact_id_format(artifact_id)
        
        if not validation["valid"]:
            error_msg = validation["error"]
            if validation.get("suggestions"):
                error_msg += f"\n\nSuggestions:\n" + "\n".join(f"  • {s}" for s in validation["suggestions"])
            raise ValueError(error_msg)
        
        # Return normalized format
        return f"{validation['artifact_type']}-{validation['number']}"
    
    def validate_provisional_filename(self, filename: str) -> str:
        """Validate a provisional filename and extract the artifact type.
        
        This method validates that a filename follows the provisional naming pattern
        and extracts the artifact type from it.
        
        Expected patterns:
        - ARTIFACTTYPE-PROVISIONAL1.md
        - TASKPRD-PROVISIONAL1.md
        - PRD-PROVISIONAL1.md
        
        Args:
            filename: The provisional filename to validate
            
        Returns:
            JSON string containing validation results and artifact type
            
        Example:
            >>> manager.validate_provisional_filename("TASKPRD-PROVISIONAL1.md")
            '{"valid": true, "artifact_type": "TASKPRD", "filename": "TASKPRD-PROVISIONAL1.md"}'
        """
        import json
        
        result = {
            "valid": False,
            "artifact_type": None,
            "filename": filename,
            "error": None
        }
        
        try:
            # Remove file extension if present
            name_without_ext = filename
            if filename.endswith('.md'):
                name_without_ext = filename[:-3]
            
            # Pattern: ARTIFACTTYPE-PROVISIONAL[number]
            pattern = r'^([A-Z]+)-PROVISIONAL\d*$'
            match = re.match(pattern, name_without_ext.upper())
            
            if not match:
                result["error"] = f"Filename '{filename}' does not match provisional pattern (ARTIFACTTYPE-PROVISIONAL[number].md)"
                return json.dumps(result)
            
            artifact_type = match.group(1)
            
            # Validate that the artifact type is valid
            if not self.is_valid_artifact_type(artifact_type):
                valid_types = self.get_valid_artifact_types()
                result["error"] = f"Invalid artifact type '{artifact_type}'. Valid types: {valid_types}"
                return json.dumps(result)
            
            # If we get here, everything is valid
            result["valid"] = True
            result["artifact_type"] = artifact_type
            
            return json.dumps(result)
            
        except Exception as e:
            result["error"] = f"Error validating filename: {str(e)}"
            return json.dumps(result)


def get_artifact_type_manager(config_path: Optional[str] = None) -> ArtifactTypeManager:
    """Factory function to create an ArtifactTypeManager instance.
    
    Args:
        config_path: Path to the artifact_types.json config file.
                    If None, uses default location.
        
    Returns:
        An ArtifactTypeManager instance
        
    Raises:
        ValueError: If config file is not found or invalid
    """
    return ArtifactTypeManager(config_path)
