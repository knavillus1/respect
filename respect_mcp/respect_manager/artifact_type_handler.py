"""Artifact Type Handlers for ReSpecT

This module provides specialized handling for different artifact types during
processing. Each artifact type can have its own handler that
performs post-processing activities.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

# We'll import get_artifact_id_manager locally in functions to avoid circular imports
# This eliminates the module-level import complexity


class ArtifactHandler(ABC):
    """Abstract base class for artifact handlers."""
    
    def __init__(self):
        """Initialize the artifact handler with the header manager."""
        from .artifact_header_manager import ArtifactHeaderManager
        self._header_manager = ArtifactHeaderManager()
    
    def finalize(self, artifact_id: str, id_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Perform post-finalization activities for this artifact type.
        
        This is optional for artifact handlers. Only file-based artifacts that need
        post-processing should override this method.
        
        Args:
            artifact_id: The main artifact ID that was finalized
            id_mapping: Dictionary mapping provisional IDs to final artifact IDs
            
        Returns:
            Dictionary with handler results and status information
        """
        # Default implementation - no post-processing needed
        artifact_type = self.__class__.__name__.replace('Handler', '').upper()
        return {
            "handler_type": artifact_type,
            "artifact_id": artifact_id,
            "status": "completed",
            "message": f"{artifact_type} handler processed {artifact_id} (no post-processing needed)",
            "actions_performed": ["No post-processing required for this artifact type"]
        }
    
    def update_status_in_index(self, artifact_id: str, status: str) -> Dict[str, Any]:
        """Update the status of an artifact in the index.
        
        This is a shared method that all handlers can use to update the index.
        It handles the index update consistently across all artifact types.
        
        Args:
            artifact_id: The artifact ID to update
            status: The new status to set
            
        Returns:
            Dictionary with update results
        """
        try:
            # Import locally to avoid circular imports
            from .artifact_index_manager import get_artifact_index_manager
            
            # Get the document repository root
            import os
            repo_root = os.getenv("RESPECT_DOC_REPO_ROOT")
            if not repo_root:
                raise ValueError("RESPECT_DOC_REPO_ROOT environment variable not set")
            
            # Update the index
            index_manager = get_artifact_index_manager(repo_root)
            success = index_manager.update_artifact(artifact_id, status=status)
            
            if not success:
                return {
                    "success": False,
                    "message": f"Artifact {artifact_id} not found in index"
                }
            
            return {
                "success": True,
                "message": f"Updated {artifact_id} status to {status} in index"
            }
            
        except Exception as e:
            logger.error(f"Error updating status in index for {artifact_id}: {e}")
            return {
                "success": False,
                "message": f"Error updating status in index: {str(e)}"
            }
    
    def update_status(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Template method that ensures index is always updated consistently.
        
        This method follows the Template Method Pattern:
        1. Always updates the index first
        2. Delegates content-specific updates to subclasses
        3. Combines and returns the results
        
        Args:
            artifact_id: The artifact ID to update
            status: The new status to set
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with combined update results
        """
        try:
            # Step 1: Always update index first
            index_result = self.update_status_in_index(artifact_id, status)
            
            # Step 2: Let subclass handle content-specific updates
            content_result = self.update_status_content(artifact_id, status, artifact_manager)
            
            # Step 3: Combine results
            return self._combine_update_results(index_result, content_result, artifact_id, status)
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating {artifact_id}: {str(e)}"
            }
    
    @abstractmethod
    def update_status_content(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Update the status in the artifact's content.
        
        Subclasses must implement this to handle their specific content update logic.
        
        Args:
            artifact_id: The artifact ID to update
            status: The new status to set
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with content update results
        """
        pass
    
    def mark_step_done(self, artifact_id: str, step_number: str, artifact_manager) -> Dict[str, Any]:
        """Mark a step as done in an artifact.
        
        Default implementation that returns an error. Subclasses that support steps
        should override this method.
        
        Args:
            artifact_id: The artifact ID (e.g., "TASK-10")
            step_number: The step number to mark as done (e.g., "10.1")
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with success status and message
        """
        artifact_type = self.__class__.__name__.replace('Handler', '').upper()
        return {
            "success": False,
            "message": f"Artifact type {artifact_type} does not support step marking"
        }
    
    def _combine_update_results(self, index_result: Dict[str, Any], content_result: Dict[str, Any], 
                               artifact_id: str, status: str) -> Dict[str, Any]:
        """Combine index and content update results into a single response.
        
        Args:
            index_result: Result from index update
            content_result: Result from content update
            artifact_id: The artifact ID that was updated
            status: The status that was set
            
        Returns:
            Combined result dictionary
        """
        messages = []
        success = True
        
        # Process index result
        if index_result.get("success"):
            messages.append(index_result.get("message", f"Updated {artifact_id} status in index"))
        else:
            messages.append(f"Warning: Failed to update index: {index_result.get('message')}")
            # Don't fail completely if index update fails, but warn
        
        # Process content result
        if content_result.get("success"):
            messages.append(content_result.get("message", f"Updated {artifact_id} status in content"))
        else:
            messages.append(f"Error: Failed to update content: {content_result.get('message')}")
            success = False
        
        return {
            "success": success,
            "message": "; ".join(messages),
            "file_path": content_result.get("file_path")
        }
    
    def _move_file_for_status(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Move artifact file to status subdirectory if required by artifact type config.
        
        Args:
            artifact_id: The artifact ID
            status: The new status being set
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with move operation results
        """
        try:
            from .artifact_type_manager import get_artifact_type_manager
            from pathlib import Path
            import os
            
            # Get artifact type and check if status triggers file move
            type_manager = get_artifact_type_manager()
            artifact_type = type_manager.get_artifact_type_from_id(artifact_id)
            type_info = type_manager.get_artifact_type_info(artifact_type)
            
            move_statuses = type_info.get("status_update_file_move", [])
            if status not in move_statuses:
                return {"success": True, "message": "No file move required for this status"}
            
            # Get the current file location
            artifact_result = artifact_manager.get_artifact(artifact_id)
            if not artifact_result.get("success"):
                return {"success": False, "message": f"Could not locate file for {artifact_id}"}
            
            current_file_path = artifact_result.get("file_path")
            if not current_file_path:
                return {"success": False, "message": f"No file path found for {artifact_id}"}
            
            current_path = Path(current_file_path)
            if not current_path.exists():
                return {"success": False, "message": f"Current file does not exist: {current_path}"}
            
            # Create target directory (status name under document root)
            doc_repo_root = os.getenv("RESPECT_DOC_REPO_ROOT")
            if not doc_repo_root:
                return {"success": False, "message": "RESPECT_DOC_REPO_ROOT not configured"}
            
            target_dir = Path(doc_repo_root) / status.lower()
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Move file to target directory
            target_path = target_dir / current_path.name
            current_path.rename(target_path)
            
            return {
                "success": True,
                "message": f"Moved {artifact_id} file to {status.lower()}/ directory",
                "old_path": str(current_path),
                "new_path": str(target_path)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error moving file for {artifact_id}: {str(e)}"
            }
    
    def _manage_header_metadata_lines(self, content: str, updates: Dict[str, str]) -> str:
        """Manage metadata lines in document header using ArtifactHeaderManager.
        
        Args:
            content: Full artifact content string
            updates: Dict of metadata key -> value (e.g., {'Status': 'ACTIVE', 'Referenced by': 'TASKPRD-16'})
            
        Returns:
            Updated content with metadata properly managed
        """
        try:
            # Convert old-style key names to new header item keys
            header_updates = {}
            for key, value in updates.items():
                if key == 'Status':
                    header_updates['STATUS'] = value
                elif key == 'Referenced by':
                    header_updates['REFERENCED_BY'] = value
                elif key == 'Implementing Tasks':
                    header_updates['IMPLEMENTING_TASKS'] = value
                elif key == 'Covering Tests':
                    header_updates['COVERING_TESTS'] = value
                elif key == 'Parent':
                    header_updates['PARENT'] = value
                else:
                    # For unknown keys, try to find a matching header item
                    logger.warning(f"Unknown header key '{key}', trying direct update")
                    # Convert to uppercase and replace spaces with underscores
                    header_key = key.upper().replace(' ', '_')
                    header_updates[header_key] = value
            
            return self._header_manager.update_managed_header(content, header_updates)
            
        except Exception as e:
            logger.error(f"Error managing headers with ArtifactHeaderManager: {e}")
            # Fallback to original method if header manager fails
            lines = content.split('\n')
            return '\n'.join(self._legacy_manage_header_metadata_lines(lines, updates))
    
    def _legacy_manage_header_metadata_lines(self, lines: List[str], updates: Dict[str, str]) -> List[str]:
        """Legacy metadata management (fallback method).
        
        This is the original implementation kept as fallback.
        """
        if not lines:
            return lines
            
        # Find the main heading (first line)
        header_line_idx = 0
        
        # Define expected metadata order
        metadata_order = ['Status', 'Referenced by']
        
        # Collect existing metadata and their positions
        existing_metadata = {}
        metadata_line_indices = []
        
        # Scan for existing metadata lines after header
        for i in range(1, len(lines)):
            line = lines[i].strip()
            if not line:  # Empty line - marks end of metadata section
                break
            
            # Check if this is a metadata line (key: value)
            for key in metadata_order:
                if line.startswith(f"{key}:"):
                    existing_metadata[key] = line
                    metadata_line_indices.append(i)
                    break
            else:
                # If it's not a metadata line, stop scanning
                break
        
        # Merge existing with updates
        all_metadata = {**existing_metadata}
        for key, value in updates.items():
            all_metadata[key] = f"{key}: {value}"
        
        # Remove old metadata lines (in reverse order to preserve indices)
        for idx in sorted(metadata_line_indices, reverse=True):
            lines.pop(idx)
        
        # Insert new metadata lines in correct order
        insert_pos = 1  # After header
        for key in metadata_order:
            if key in all_metadata:
                lines.insert(insert_pos, all_metadata[key])
                insert_pos += 1
        
        return lines
    
    def add_reference(self, target_artifact_id: str, ref_artifact_id: str, artifact_manager) -> Dict[str, Any]:
        """Add a reference to an artifact's Referenced by line using ArtifactHeaderManager.
        
        Args:
            target_artifact_id: The artifact to add the reference to
            ref_artifact_id: The artifact that references the target
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with operation results
        """
        try:
            from .artifact_type_manager import get_artifact_type_manager
            
            # Validate target artifact type supports references
            type_manager = get_artifact_type_manager()
            target_type = type_manager.get_artifact_type_from_id(target_artifact_id)
            target_type_info = type_manager.get_artifact_type_info(target_type)
            
            allowed_ref_types = target_type_info.get("reference_types", [])
            if not allowed_ref_types:
                return {
                    "success": False,
                    "message": f"Artifact type {target_type} does not support references"
                }
            
            # Validate reference artifact type is allowed
            ref_type = type_manager.get_artifact_type_from_id(ref_artifact_id)
            if ref_type not in allowed_ref_types:
                return {
                    "success": False,
                    "message": f"Reference type {ref_type} not allowed for {target_type}. Allowed: {', '.join(allowed_ref_types)}"
                }
            
            # Get the target artifact content
            artifact_result = artifact_manager.get_artifact(target_artifact_id)
            if not artifact_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to retrieve {target_artifact_id}: {artifact_result.get('message')}"
                }
            
            content = artifact_result["content"]
            
            # Use the header manager to add the reference
            header_updates = {'REFERENCED_BY': ref_artifact_id}
            updated_content = self._header_manager.update_managed_header(content, header_updates)
            
            # Write back the updated content
            file_path = artifact_result.get("file_path")
            if file_path:
                from pathlib import Path
                Path(file_path).write_text(updated_content, encoding='utf-8')
                
                return {
                    "success": True,
                    "message": f"Added reference {ref_artifact_id} to {target_artifact_id}",
                    "file_path": file_path
                }
            else:
                return {
                    "success": False,
                    "message": f"No file path found for {target_artifact_id}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error adding reference to {target_artifact_id}: {str(e)}"
            }
class TaskPRDHandler(ArtifactHandler):
    """Handler for TASKPRD artifact processing."""
    
    def update_status(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Override to add file move logic for TASKPRD status updates.
        
        Args:
            artifact_id: The artifact ID to update
            status: The new status to set
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with combined update results including file move
        """
        try:
            # Step 1: Always update index first
            index_result = self.update_status_in_index(artifact_id, status)
            
            # Step 2: Let subclass handle content-specific updates
            content_result = self.update_status_content(artifact_id, status, artifact_manager)
            
            # Step 3: Handle file move if required by status
            move_result = self._move_file_for_status(artifact_id, status, artifact_manager)
            
            # Step 4: Combine all results
            messages = []
            success = True
            
            if index_result.get("success"):
                messages.append(f"Index: {index_result.get('message')}")
            else:
                messages.append(f"Index warning: {index_result.get('message')}")
            
            if content_result.get("success"):
                messages.append(f"Content: {content_result.get('message')}")
            else:
                messages.append(f"Content error: {content_result.get('message')}")
                success = False
            
            if move_result.get("success"):
                if "No file move required" not in move_result.get("message", ""):
                    messages.append(f"File move: {move_result.get('message')}")
            else:
                messages.append(f"File move error: {move_result.get('message')}")
                success = False
            
            return {
                "success": success,
                "artifact_id": artifact_id,
                "status": status,
                "updates": messages,
                "index_result": index_result,
                "content_result": content_result,
                "move_result": move_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating {artifact_id}: {str(e)}"
            }
    
    def finalize(self, artifact_id: str, id_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Handle TASKPRD-specific post-finalization activities.
        
        This method processes each TASK artifact in the id_mapping to:
        1. Extract REQ artifacts that each TASK implements
        2. Update those REQ artifacts to record which TASK implements them
        
        Args:
            artifact_id: The main TASKPRD artifact ID that was finalized
            id_mapping: Dictionary mapping provisional IDs to final artifact IDs
            
        Returns:
            Dictionary with handler results
        """
        logger.info(f"TASKPRD handler called for {artifact_id}")
        logger.info(f"ID mapping received: {id_mapping}")
        
        # Import ArtifactManager here to avoid circular imports
        from .artifact_manager import get_artifact_id_manager
        
        actions_performed = ["Post-processing hook executed"]
        errors = []
        updated_reqs = []
        
        try:
            # Get artifact manager instance
            artifact_manager = get_artifact_id_manager()
            
            # Update the main TASKPRD artifact status to NEW
            taskprd_status_result = self.update_status(artifact_id, "NEW", artifact_manager)
            if taskprd_status_result.get("success"):
                actions_performed.append(f"Updated {artifact_id} status to NEW")
                logger.info(f"Successfully updated {artifact_id} status to NEW")
            else:
                error_msg = f"Failed to update {artifact_id} status: {taskprd_status_result.get('message')}"
                logger.warning(error_msg)
                errors.append(error_msg)
            
            # Get the TASKPRD content to parse parent PRD and TASK sections from it
            taskprd_result = artifact_manager.get_artifact(artifact_id)
            
            if not taskprd_result.get("success"):
                error_msg = f"Failed to retrieve TASKPRD {artifact_id}: {taskprd_result.get('message')}"
                logger.error(error_msg)
                errors.append(error_msg)
                return {
                    "handler_type": "TASKPRD",
                    "artifact_id": artifact_id,
                    "status": "error",
                    "message": error_msg,
                    "actions_performed": actions_performed,
                    "errors": [error_msg]
                }
            
            taskprd_content = taskprd_result["content"]
            
            # Extract and update parent PRD reference
            try:
                # Parse TASKPRD content to find parent PRD in asterisk format (*Parent*:)
                parent_prd_id = None
                lines = taskprd_content.split('\n')
                
                for line in lines:
                    line_stripped = line.strip()
                    if line_stripped.startswith('*Parent*:'):
                        # Extract parent ID from line like "*Parent*: PRD-1: Flask-React Hello World Web Application"
                        parent_text = line_stripped[len('*Parent*:'):].strip()
                        # Extract just the PRD ID (first part before any colon or description)
                        if parent_text:
                            # Split on colon and take first part, or use whole text if no colon
                            parent_parts = parent_text.split(':')
                            parent_prd_id = parent_parts[0].strip()
                        break
                
                if parent_prd_id:
                    logger.info(f"Found parent PRD: {parent_prd_id}")
                    
                    # Update parent PRD's Referenced by header
                    prd_result = artifact_manager.get_artifact(parent_prd_id)
                    if prd_result.get("success"):
                        prd_content = prd_result["content"]
                        
                        # Parse current PRD headers using header manager
                        prd_header_line, prd_headers, prd_body = self._header_manager.parse_managed_headers(prd_content)
                        current_refs_str = prd_headers.get('REFERENCED_BY', '')
                        
                        # Parse current references from comma-separated string
                        if current_refs_str.strip():
                            current_refs = [ref.strip() for ref in current_refs_str.split(',')]
                        else:
                            current_refs = []
                        
                        # Add TASKPRD reference if not already present
                        if artifact_id not in current_refs:
                            current_refs.append(artifact_id)
                            current_refs.sort()  # Sort for consistency
                            
                            # Update PRD using header manager - rebuild manually to avoid append behavior
                            updated_prd_headers = prd_headers.copy()
                            updated_prd_headers['REFERENCED_BY'] = ','.join(current_refs)
                            
                            # Get PRD artifact type for header ordering
                            prd_type_info = self._header_manager.extract_artifact_type_and_id(prd_content)
                            if prd_type_info:
                                prd_type, _ = prd_type_info
                                applicable_headers = self._header_manager.get_managed_headers_for_type(prd_type)
                                
                                # Rebuild PRD content with updated references
                                result_lines = [prd_header_line]
                                
                                # Add managed headers in consistent order
                                for item_key, item_config in applicable_headers.items():
                                    if item_key in updated_prd_headers:
                                        label = item_config['label']
                                        value = updated_prd_headers[item_key]
                                        result_lines.append(f"`{label.rstrip(':')}`: {value}")
                                
                                # Add body content
                                if prd_body.strip():
                                    result_lines.append(prd_body)
                                
                                updated_prd_content = '\n'.join(result_lines)
                                
                                # Write back updated PRD content
                                prd_file_path = prd_result.get("file_path")
                                if prd_file_path:
                                    from pathlib import Path
                                    Path(prd_file_path).write_text(updated_prd_content, encoding='utf-8')
                                    actions_performed.append(f"Updated parent PRD {parent_prd_id} Referenced by to include {artifact_id}")
                                    logger.info(f"Successfully updated {parent_prd_id} Referenced by header")
                                else:
                                    error_msg = f"No file path found for parent PRD {parent_prd_id}"
                                    logger.warning(error_msg)
                                    errors.append(error_msg)
                            else:
                                error_msg = f"Could not determine artifact type for parent PRD {parent_prd_id}"
                                logger.warning(error_msg)
                                errors.append(error_msg)
                        else:
                            logger.info(f"TASKPRD {artifact_id} already referenced in parent PRD {parent_prd_id}")
                            actions_performed.append(f"TASKPRD {artifact_id} already referenced in parent PRD {parent_prd_id}")
                    else:
                        error_msg = f"Failed to retrieve parent PRD {parent_prd_id}: {prd_result.get('message')}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                else:
                    logger.warning(f"No parent PRD found in TASKPRD {artifact_id} content")
                    actions_performed.append(f"No parent PRD found in TASKPRD {artifact_id} content")
                    
            except Exception as e:
                error_msg = f"Error updating parent PRD reference: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
            
            # Extract only the TASK artifact IDs (ignore provisional IDs)
            task_ids = [v for v in id_mapping.values() if v.startswith('TASK-')]
            
            logger.info(f"Processing {len(task_ids)} TASK artifacts")
            actions_performed.append(f"Found {len(task_ids)} TASK artifacts to process")
            
            for task_id in task_ids:
                try:
                    logger.info(f"Processing TASK artifact: {task_id}")
                    
                    # Update TASK status to NEW using the TASK handler
                    task_handler = ArtifactHandlerFactory.get_handler("TASK")
                    if task_handler:
                        status_result = task_handler.update_status(task_id, "NEW", artifact_manager)
                        if status_result.get("success"):
                            actions_performed.append(f"Updated {task_id} status to NEW")
                            logger.info(f"Successfully updated {task_id} status to NEW")
                        else:
                            error_msg = f"Failed to update {task_id} status: {status_result.get('message')}"
                            logger.warning(error_msg)
                            errors.append(error_msg)
                    
                    # Parse the TASKPRD content to find this specific TASK section
                    task_section_content = self._extract_task_section(taskprd_content, task_id)
                    
                    if not task_section_content:
                        logger.warning(f"Could not find section for {task_id} in TASKPRD")
                        continue
                    
                    # Parse the task section to find REQ implementations
                    req_ids = self._extract_req_implementations(task_section_content)
                    
                    if not req_ids:
                        logger.info(f"No REQ implementations found in {task_id}")
                        continue
                    
                    logger.info(f"Found REQ implementations in {task_id}: {req_ids}")
                    actions_performed.append(f"{task_id} implements REQs: {', '.join(req_ids)}")
                    
                    # Update each REQ artifact to record this TASK as implementing it
                    for req_id in req_ids:
                        try:
                            self._update_req_with_implementing_task(artifact_manager, req_id, task_id)
                            updated_reqs.append(req_id)
                            logger.info(f"Updated {req_id} to record implementation by {task_id}")
                        except Exception as e:
                            error_msg = f"Failed to update {req_id} for {task_id}: {str(e)}"
                            logger.error(error_msg)
                            errors.append(error_msg)
                
                except Exception as e:
                    error_msg = f"Error processing TASK {task_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Summary of actions
            unique_updated_reqs = list(set(updated_reqs))
            if unique_updated_reqs:
                actions_performed.append(f"Updated {len(unique_updated_reqs)} REQ artifacts: {', '.join(unique_updated_reqs)}")
            
            if errors:
                actions_performed.append(f"Encountered {len(errors)} errors during processing")
        
        except Exception as e:
            error_msg = f"Critical error in TASKPRD handler: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        return {
            "handler_type": "TASKPRD",
            "artifact_id": artifact_id,
            "id_mapping": id_mapping,
            "status": "completed" if not errors else "completed_with_errors",
            "message": f"TASKPRD handler processed {artifact_id}",
            "actions_performed": actions_performed,
            "updated_reqs": list(set(updated_reqs)) if updated_reqs else [],
            "errors": errors if errors else None
        }
    
    def _extract_task_section(self, taskprd_content: str, task_id: str) -> str:
        """Extract the content of a specific TASK section from TASKPRD content.
        
        Args:
            taskprd_content: The full content of the TASKPRD artifact
            task_id: The TASK ID to find (e.g., "TASK-10")
            
        Returns:
            Content of the TASK section, or empty string if not found
        """
        lines = taskprd_content.split('\n')
        task_section_lines = []
        in_task_section = False
        
        for line in lines:
            # Check if this line starts a TASK section we're looking for
            if line.strip().startswith(f'### {task_id}:'):
                in_task_section = True
                task_section_lines.append(line)
                continue
            
            # Check if this line starts a different TASK section (end of our section)
            if in_task_section and line.strip().startswith('### TASK-'):
                break
            
            # Add lines to our section if we're currently in it
            if in_task_section:
                task_section_lines.append(line)
        
        return '\n'.join(task_section_lines)
    
    def _extract_req_implementations(self, task_content: str) -> list[str]:
        """Extract REQ artifact IDs from a TASK's *Implements:* line.
        
        Args:
            task_content: The content of the TASK artifact
            
        Returns:
            List of REQ artifact IDs that this TASK implements
        """
        import re
        
        lines = task_content.split('\n')
        req_ids = []
        
        for line in lines:
            line = line.strip()
            # Look for lines like "*Implements*: REQ-2, REQ-3"
            if line.startswith('*Implements*:'):
                # Extract everything after "*Implements*:"
                implements_text = line[len('*Implements*:'):].strip()
                
                # Find all REQ-<number> patterns
                req_pattern = r'\bREQ-(\d+)\b'
                matches = re.findall(req_pattern, implements_text)
                
                # Convert matches back to full REQ IDs
                for match in matches:
                    req_ids.append(f"REQ-{match}")
                
                break  # Assume only one *Implements*: line per TASK
        
        return req_ids
    
    def _update_req_with_implementing_task(self, artifact_manager, req_id: str, task_id: str) -> None:
        """Update a REQ artifact to record which TASK implements it.
        
        Args:
            artifact_manager: The ArtifactManager instance
            req_id: The REQ artifact ID to update
            task_id: The TASK artifact ID that implements this REQ
        """
        # Get the current REQ content
        req_result = artifact_manager.get_artifact(req_id)
        
        if not req_result.get("success"):
            raise Exception(f"Failed to retrieve REQ {req_id}: {req_result.get('message')}")
        
        req_content = req_result["content"]
        
        # Check if this REQ already has an *Implementing Tasks* line
        updated_content = self._add_or_update_implementing_task_line(req_content, task_id)
        
        # Debug logging
        logger.info(f"Original REQ content for {req_id}:")
        logger.info(repr(req_content))
        logger.info(f"Updated REQ content for {req_id}:")
        logger.info(repr(updated_content))
        
        # Update the REQ artifact with the new content
        update_result = artifact_manager._update_non_file_artifact(req_id, updated_content)
        
        if not update_result.get("success"):
            raise Exception(f"Failed to update REQ {req_id}: {update_result.get('message')}")
    
    def _add_or_update_implementing_task_line(self, req_content: str, task_id: str) -> str:
        """Add or update the implementing tasks in REQ content using ArtifactHeaderManager.
        
        Args:
            req_content: Current content of the REQ artifact
            task_id: The TASK ID to add to the implementing tasks
            
        Returns:
            Updated REQ content with the implementing task recorded
        """
        try:
            # Parse current implementing tasks using header manager
            header_line, current_headers, body_content = self._header_manager.parse_managed_headers(req_content)
            current_tasks_str = current_headers.get('IMPLEMENTING_TASKS', '')
            
            # Parse current tasks from comma-separated string
            if current_tasks_str.strip():
                current_tasks = [task.strip() for task in current_tasks_str.split(',')]
            else:
                current_tasks = []
            
            # Add the new task if not already present (check without status)
            task_found = False
            for task in current_tasks:
                clean_task = task.split(' (')[0].strip()
                if clean_task == task_id:
                    task_found = True
                    break
            
            if not task_found:
                current_tasks.append(task_id)
            
            # Sort for consistency
            current_tasks.sort(key=lambda x: x.split(' (')[0])
            
            # Rebuild content manually to avoid header manager's append behavior
            if not header_line:
                raise Exception("Could not parse REQ header")
            
            # Get artifact type for header ordering
            artifact_info = self._header_manager.extract_artifact_type_and_id(req_content)
            if not artifact_info:
                raise Exception("Could not determine artifact type for REQ")
            
            artifact_type, _ = artifact_info
            applicable_headers = self._header_manager.get_managed_headers_for_type(artifact_type)
            
            # Update the IMPLEMENTING_TASKS in current headers
            updated_headers = current_headers.copy()
            if current_tasks:
                updated_headers['IMPLEMENTING_TASKS'] = ','.join(current_tasks)
            elif 'IMPLEMENTING_TASKS' in updated_headers:
                del updated_headers['IMPLEMENTING_TASKS']
            
            # Rebuild the content with proper header ordering
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
            
        except Exception as e:
            logger.error(f"Error updating implementing tasks with ArtifactHeaderManager: {e}")
            # Fallback to legacy method
            return self._legacy_add_or_update_implementing_task_line(req_content, task_id)
    
    def _legacy_add_or_update_implementing_task_line(self, req_content: str, task_id: str) -> str:
        """Legacy method for updating implementing tasks (fallback).
        
        This is the original implementation kept as fallback.
        """
        lines = req_content.split('\n')
        implementing_line_index = None
        
        # Look for existing *Implementing Tasks* line
        for i, line in enumerate(lines):
            if line.strip().startswith('*Implementing Tasks*:') or line.strip().startswith('*Implementing Task*:'):
                implementing_line_index = i
                break
        
        if implementing_line_index is not None:
            # Update existing line
            current_line = lines[implementing_line_index].strip()
            
            # Extract current task IDs
            if ':' in current_line:
                current_tasks_text = current_line.split(':', 1)[1].strip()
                current_tasks = [t.strip() for t in current_tasks_text.split(',') if t.strip()]
            else:
                current_tasks = []
            
            # Add new task if not already present
            if task_id not in current_tasks:
                current_tasks.append(task_id)
            
            # Sort for consistency
            current_tasks.sort()
            
            # Update the line with proper markdown formatting
            if len(current_tasks) == 1:
                lines[implementing_line_index] = f"*Implementing Task*: {current_tasks[0]}  "
            else:
                lines[implementing_line_index] = f"*Implementing Tasks*: {', '.join(current_tasks)}  "
        
        else:
            # Find the last metadata line (line starting with *)
            last_metadata_index = -1
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if line_stripped.startswith('*') and ':' in line_stripped:
                    last_metadata_index = i
            
            if last_metadata_index >= 0:
                # Ensure the last metadata line has proper markdown line ending (two spaces)
                if not lines[last_metadata_index].endswith('  '):
                    lines[last_metadata_index] = lines[last_metadata_index].rstrip() + '  '
                
                # Insert after the last metadata line with proper markdown spacing
                insert_index = last_metadata_index + 1
                
                # Add the implementing task line with proper markdown line ending
                lines.insert(insert_index, f"*Implementing Task*: {task_id}  ")
            else:
                # If no metadata found, find the heading and insert after it
                for i, line in enumerate(lines):
                    if line.strip().startswith('###'):
                        insert_index = i + 1
                        new_line = f"*Implementing Task*: {task_id}"
                        lines.insert(insert_index, new_line)
                        break
        
        return '\n'.join(lines)
    
    def update_status_content(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Update status for TASKPRD artifact (full-file type, status on second line).
        
        Args:
            artifact_id: The TASKPRD artifact ID
            status: The new status
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with update results
        """
        try:
            # Get the artifact content
            artifact_result = artifact_manager.get_artifact(artifact_id)
            
            if not artifact_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to retrieve TASKPRD {artifact_id}: {artifact_result.get('message')}"
                }
            
            content = artifact_result["content"]
            lines = content.split('\n')
            
            # Update status only - don't preserve any existing references for TASKPRD
            updates = {'Status': status}
            
            # Update the lines using header metadata management
            updated_content = self._manage_header_metadata_lines(content, updates)
            
            # Write back the updated content
            file_path = artifact_result.get("file_path")
            if file_path:
                from pathlib import Path
                Path(file_path).write_text(updated_content, encoding='utf-8')
                
                return {
                    "success": True,
                    "message": f"Updated TASKPRD {artifact_id} status to {status}",
                    "file_path": file_path
                }
            else:
                return {
                    "success": False,
                    "message": f"No file path found for TASKPRD {artifact_id}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating TASKPRD {artifact_id}: {str(e)}"
            }


class PRDHandler(ArtifactHandler):
    """Handler for PRD artifact processing."""
    
    def update_status(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Override to add file move logic for PRD status updates.
        
        Args:
            artifact_id: The artifact ID to update
            status: The new status to set
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with combined update results including file move
        """
        try:
            # Step 1: Always update index first
            index_result = self.update_status_in_index(artifact_id, status)
            
            # Step 2: Let subclass handle content-specific updates
            content_result = self.update_status_content(artifact_id, status, artifact_manager)
            
            # Step 3: Handle file move if required by status
            move_result = self._move_file_for_status(artifact_id, status, artifact_manager)
            
            # Step 4: Combine all results
            messages = []
            success = True
            
            if index_result.get("success"):
                messages.append(f"Index: {index_result.get('message')}")
            else:
                messages.append(f"Index warning: {index_result.get('message')}")
            
            if content_result.get("success"):
                messages.append(f"Content: {content_result.get('message')}")
            else:
                messages.append(f"Content error: {content_result.get('message')}")
                success = False
            
            if move_result.get("success"):
                if "No file move required" not in move_result.get("message", ""):
                    messages.append(f"File move: {move_result.get('message')}")
            else:
                messages.append(f"File move error: {move_result.get('message')}")
                success = False
            
            return {
                "success": success,
                "artifact_id": artifact_id,
                "status": status,
                "updates": messages,
                "index_result": index_result,
                "content_result": content_result,
                "move_result": move_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating {artifact_id}: {str(e)}"
            }
    
    def finalize(self, artifact_id: str, id_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Handle PRD-specific post-finalization activities."""
        logger.info(f"PRD handler called for {artifact_id}")

        actions_performed: list[str] = ["Post-processing hook executed"]
        errors: list[str] = []
        updated_reqs: list[str] = []

        try:
            # Get artifact manager instance (import locally to avoid circular imports)
            from .artifact_manager import get_artifact_id_manager
            artifact_manager = get_artifact_id_manager()

            # Update the main PRD artifact status
            logger.info(f"Updating status for PRD artifact: {artifact_id}")

            # Update PRD status to NEW after finalization
            # First update the index
            index_result = self.update_status_in_index(artifact_id, "NEW")
            if index_result.get("success"):
                actions_performed.append(f"Updated {artifact_id} status to NEW in index")
                logger.info(f"Successfully updated {artifact_id} status to NEW in index")
            else:
                error_msg = f"Failed to update {artifact_id} status in index: {index_result.get('message')}"
                logger.error(error_msg)
                errors.append(error_msg)

            # Then update the artifact content (template method also updates index; kept for parity with existing behavior)
            status_result = self.update_status(artifact_id, "NEW", artifact_manager)
            if status_result.get("success"):
                actions_performed.append(f"Updated {artifact_id} status to NEW in content")
                logger.info(f"Successfully updated {artifact_id} status to NEW in content")
            else:
                error_msg = f"Failed to update {artifact_id} status in content: {status_result.get('message')}"
                logger.error(error_msg)
                errors.append(error_msg)

            # After PRD is finalized, set all nested REQ artifacts to NEW
            try:
                # Extract REQ artifact IDs from id_mapping
                req_ids = [final_id for final_id in id_mapping.values() if isinstance(final_id, str) and final_id.startswith('REQ-')]
                if req_ids:
                    actions_performed.append(f"Found {len(req_ids)} REQ artifacts to initialize")
                    logger.info(f"Initializing {len(req_ids)} REQ artifacts under {artifact_id}")

                # Use REQ handler via factory to update status
                from .artifact_type_handler import ArtifactHandlerFactory as _Factory
                req_handler = _Factory.get_handler("REQ")

                for req_id in req_ids:
                    try:
                        if req_handler:
                            res = req_handler.update_status(req_id, "NEW", artifact_manager)
                            if res.get("success"):
                                actions_performed.append(f"Updated {req_id} status to NEW")
                                updated_reqs.append(req_id)
                            else:
                                msg = res.get("message", "Unknown error")
                                error_msg = f"Failed to set {req_id} to NEW: {msg}"
                                logger.warning(error_msg)
                                errors.append(error_msg)
                        else:
                            error_msg = "REQ handler unavailable"
                            logger.error(error_msg)
                            errors.append(error_msg)
                            break
                    except Exception as e:
                        error_msg = f"Error updating REQ {req_id}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
            except Exception as e:
                error_msg = f"Error initializing nested REQs: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        except Exception as e:
            error_msg = f"Error in PRD finalization: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        return {
            "handler_type": "PRD",
            "artifact_id": artifact_id,
            "id_mapping": id_mapping,
            "status": "completed" if not errors else "completed_with_errors",
            "message": f"PRD handler processed {artifact_id}",
            "actions_performed": actions_performed,
            "updated_reqs": list(sorted(set(updated_reqs))) if updated_reqs else [],
            "errors": errors if errors else None
        }
    
    def update_status_content(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Update status for PRD artifact (full-file type, status on second line)."""
        try:
            # Get the artifact content
            artifact_result = artifact_manager.get_artifact(artifact_id)
            
            if not artifact_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to retrieve PRD {artifact_id}: {artifact_result.get('message')}"
                }
            
            content = artifact_result["content"]
            lines = content.split('\n')
            
            # Preserve existing references if present
            updates = {'Status': status}
            for line in lines[1:]:
                if line.startswith('Referenced by:'):
                    updates['Referenced by'] = line.replace('Referenced by:', '').strip()
                    break
            
            # Update the lines using header metadata management
            updated_content = self._manage_header_metadata_lines(content, updates)
            
            # Write back the updated content
            file_path = artifact_result.get("file_path")
            if file_path:
                from pathlib import Path
                Path(file_path).write_text(updated_content, encoding='utf-8')
                
                return {
                    "success": True,
                    "message": f"Updated PRD {artifact_id} status to {status}",
                    "file_path": file_path
                }
            else:
                return {
                    "success": False,
                    "message": f"No file path found for PRD {artifact_id}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating PRD {artifact_id}: {str(e)}"
            }

    # --- New capability: add nested artifacts (e.g., UACC/SACC) into PRD ---
    def add_nested_artifact(self, parent_artifact_id: str, new_artifact_type: str, new_artifact_content: str, artifact_manager) -> Dict[str, Any]:
        """Add a nested artifact (UACC/SACC) under a PRD's Acceptance Tests section.

        - Validates PRD allows adding the requested nested type via artifact_types config
        - Ensures a top-level `## Acceptance Tests` section exists
        - Appends the provided content under an appropriate subsection heading

        Args:
            parent_artifact_id: PRD artifact ID (e.g., PRD-1)
            new_artifact_type: Nested type code (e.g., 'UACC' or 'SACC')
            new_artifact_content: Markdown content to insert (should include a heading like `### UACC-<id or title>`)
            artifact_manager: ArtifactManager instance

        Returns:
            Dict with success, message, and file_path
        """
        try:
            # Validate parent is PRD
            from .artifact_type_manager import get_artifact_type_manager
            type_manager = get_artifact_type_manager()
            parent_type = type_manager.get_artifact_type_from_id(parent_artifact_id)
            if parent_type != "PRD":
                return {"success": False, "message": f"Parent artifact must be PRD, got {parent_type}"}

            # Validate nested type is allowed
            prd_info = type_manager.get_artifact_type_info("PRD")
            allowed = set(prd_info.get("addable_nested_artifact_types", []))
            new_type_norm = type_manager.validate_and_normalize_artifact_type(new_artifact_type)
            if new_type_norm not in allowed:
                return {"success": False, "message": f"Type {new_type_norm} not allowed in PRD. Allowed: {', '.join(sorted(allowed))}"}

            # Load PRD file content
            prd_result = artifact_manager.get_artifact(parent_artifact_id)
            if not prd_result.get("success"):
                return {"success": False, "message": f"Failed to read {parent_artifact_id}: {prd_result.get('message')}"}
            content = prd_result["content"]
            file_path = prd_result.get("file_path")
            if not file_path:
                return {"success": False, "message": f"No file path found for {parent_artifact_id}"}

            lines = content.split('\n')

            # Find or create '## Acceptance Tests' section
            acc_header = "## Acceptance Tests"
            has_section = any(l.strip() == acc_header for l in lines)
            if not has_section:
                # Append header at end, but before any version footer
                text = '\n'.join(lines)
                import re
                version_footer_match = re.search(r"<!--\s*ReSpecT\s+v[\d.]+\s*-->", text)
                if version_footer_match:
                    # Insert before version footer
                    insert_pos = version_footer_match.start()
                    left = text[:insert_pos].rstrip()
                    right = text[insert_pos:]
                    insertion = f"\n\n{acc_header}\n\n{new_artifact_content.strip()}\n"
                    new_text = left + insertion + right
                else:
                    # No version footer, append at end like before
                    if lines and lines[-1].strip() != "":
                        lines.append("")
                    lines.append(acc_header)
                    lines.append("")
                    base_text = '\n'.join(lines).rstrip() + "\n\n"
                    new_text = base_text + new_artifact_content.strip() + "\n"
            else:
                # Reconstruct full text to locate the end of Acceptance Tests section
                text = '\n'.join(lines)
                import re
                header_pattern = re.compile(r"^\s*##\s+Acceptance Tests\s*$", re.MULTILINE)
                match = header_pattern.search(text)
                if not match:
                    # Fallback: append header, but before version footer if present
                    version_footer_match = re.search(r"<!--\s*ReSpecT\s+v[\d.]+\s*-->", text)
                    if version_footer_match:
                        insert_pos = version_footer_match.start()
                        left = text[:insert_pos].rstrip()
                        right = text[insert_pos:]
                        insertion = f"\n\n{acc_header}\n\n{new_artifact_content.strip()}\n"
                        new_text = left + insertion + right
                    else:
                        # No version footer, append at end
                        if lines and lines[-1].strip() != "":
                            lines.append("")
                        lines.append(acc_header)
                        lines.append("")
                        base_text = '\n'.join(lines).rstrip() + "\n\n"
                        new_text = base_text + new_artifact_content.strip() + "\n"
                else:
                    header_end = match.end()
                    # Find the next top-level '## ' header after Acceptance Tests
                    next_header_match = re.search(r"^\s*##\s+", text[header_end:], re.MULTILINE)
                    if next_header_match:
                        insert_pos = header_end + next_header_match.start()
                    else:
                        # Check for ReSpecT version footer and insert before it
                        version_footer_match = re.search(r"<!--\s*ReSpecT\s+v[\d.]+\s*-->", text)
                        if version_footer_match:
                            insert_pos = version_footer_match.start()
                        else:
                            insert_pos = len(text)
                    # Build new text inserting at the end of the Acceptance Tests section
                    left = text[:insert_pos].rstrip()
                    right = text[insert_pos:].lstrip('\n') if insert_pos < len(text) else ""
                    insertion = "\n\n" + new_artifact_content.strip() + "\n"
                    new_text = left + insertion + right

            # Write PRD file back
            from pathlib import Path as _Path
            _Path(file_path).write_text(new_text, encoding='utf-8')

            return {
                "success": True,
                "message": f"Added {new_type_norm} content to {parent_artifact_id} under Acceptance Tests",
                "file_path": file_path
            }
        except Exception as e:
            return {"success": False, "message": f"Error adding nested artifact to {parent_artifact_id}: {str(e)}"}


class REQHandler(ArtifactHandler):
    """Handler for REQ artifact processing."""
    
    def update_status_content(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Update status for REQ artifact using ArtifactHeaderManager."""
        try:
            # Get the current REQ content
            req_result = artifact_manager.get_artifact(artifact_id)
            
            if not req_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to retrieve REQ {artifact_id}: {req_result.get('message')}"
                }
            
            req_content = req_result["content"]
            
            # Use the header manager to update the status
            header_updates = {'STATUS': status}
            updated_content = self._header_manager.update_managed_header(req_content, header_updates)
            
            # Update the REQ artifact with the new content
            update_result = artifact_manager._update_non_file_artifact(artifact_id, updated_content)
            
            if not update_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to update REQ {artifact_id}: {update_result.get('message')}"
                }
            
            return {
                "success": True,
                "message": f"Updated REQ {artifact_id} status to {status}",
                "file_path": update_result.get("file_path")
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating REQ {artifact_id}: {str(e)}"
            }


class TASKHandler(ArtifactHandler):
    """Handler for TASK artifact processing."""
    
    def mark_step_done(self, artifact_id: str, step_number: str, artifact_manager) -> Dict[str, Any]:
        """Mark a step as done in a TASK artifact.
        
        Args:
            artifact_id: The TASK artifact ID (e.g., "TASK-10")
            step_number: The step number to mark as done (e.g., "10.1")
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with success status and message
        """
        import re
        
        try:
            # Get the current TASK content
            task_result = artifact_manager.get_artifact(artifact_id)
            
            if not task_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to retrieve TASK {artifact_id}: {task_result.get('message')}"
                }
            
            task_content = task_result["content"]
            lines = task_content.split('\n')
            
            # Find the step line to mark as done
            # Pattern: [ ] X.Y description  ->  [x] X.Y description
            step_pattern = re.compile(r'^(\[ \]) (' + re.escape(step_number) + r') (.+)$')
            updated = False
            
            for i, line in enumerate(lines):
                match = step_pattern.match(line)
                if match:
                    # Replace [ ] with [x] while preserving the rest of the line
                    lines[i] = f"[x] {match.group(2)} {match.group(3)}"
                    updated = True
                    break
            
            if not updated:
                return {
                    "success": False,
                    "message": f"Step {step_number} not found in TASK {artifact_id} or already marked as done"
                }
            
            updated_content = '\n'.join(lines)
            
            # Update the TASK artifact with the new content
            update_result = artifact_manager._update_non_file_artifact(artifact_id, updated_content)
            
            if not update_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to update TASK {artifact_id}: {update_result.get('message')}"
                }
            
            return {
                "success": True,
                "message": f"Marked step {step_number} as done in TASK {artifact_id}",
                "file_path": update_result.get("file_path")
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error marking step done in TASK {artifact_id}: {str(e)}"
            }
    
    def update_status_content(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Update status for TASK artifact using ArtifactHeaderManager.
        
        Also updates all REQ artifacts that this TASK implements to show the new status.
        """
        try:
            # Get the current TASK content
            task_result = artifact_manager.get_artifact(artifact_id)
            
            if not task_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to retrieve TASK {artifact_id}: {task_result.get('message')}"
                }
            
            task_content = task_result["content"]
            
            # Use the header manager to update the status
            header_updates = {'STATUS': status}
            updated_content = self._header_manager.update_managed_header(task_content, header_updates)
            
            # Update the TASK artifact with the new content
            update_result = artifact_manager._update_non_file_artifact(artifact_id, updated_content)
            
            if not update_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to update TASK {artifact_id}: {update_result.get('message')}"
                }
            
            # Now update all REQ artifacts that this TASK implements
            req_update_messages = []
            try:
                req_ids = self._extract_req_implementations(task_content)
                logger.info(f"TASK {artifact_id} implements REQs: {req_ids}")
                
                for req_id in req_ids:
                    try:
                        self._update_req_implementing_task_status(artifact_manager, req_id, artifact_id, status)
                        req_update_messages.append(f"Updated {req_id} to show {artifact_id} status as {status}")
                        logger.info(f"Updated {req_id} implementing task status for {artifact_id}")
                    except Exception as e:
                        error_msg = f"Failed to update {req_id} for {artifact_id}: {str(e)}"
                        logger.error(error_msg)
                        req_update_messages.append(f"Error: {error_msg}")
            except Exception as e:
                logger.error(f"Error processing REQ updates for {artifact_id}: {str(e)}")
                req_update_messages.append(f"Error processing REQ updates: {str(e)}")
            
            # Combine messages
            main_message = f"Updated TASK {artifact_id} status to {status}"
            if req_update_messages:
                combined_message = main_message + "; " + "; ".join(req_update_messages)
            else:
                combined_message = main_message
            
            return {
                "success": True,
                "message": combined_message,
                "file_path": update_result.get("file_path")
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating TASK {artifact_id}: {str(e)}"
            }
    
    def _extract_req_implementations(self, task_content: str) -> list[str]:
        """Extract REQ artifact IDs from a TASK's *Implements:* line.
        
        Args:
            task_content: The content of the TASK artifact
            
        Returns:
            List of REQ artifact IDs that this TASK implements
        """
        import re
        
        lines = task_content.split('\n')
        req_ids = []
        
        for line in lines:
            line = line.strip()
            # Look for lines like "*Implements*: REQ-2, REQ-3"
            if line.startswith('*Implements*:'):
                # Extract everything after "*Implements*:"
                implements_text = line[len('*Implements*:'):].strip()
                
                # Find all REQ-<number> patterns
                req_pattern = r'\bREQ-(\d+)\b'
                matches = re.findall(req_pattern, implements_text)
                
                # Convert matches back to full REQ IDs
                for match in matches:
                    req_ids.append(f"REQ-{match}")
                
                break  # Assume only one *Implements*: line per TASK
        
        return req_ids
    
    def _update_req_implementing_task_status(self, artifact_manager, req_id: str, task_id: str, status: str) -> None:
        """Update a REQ artifact to show the status of an implementing TASK.
        
        This method finds the implementing task line in the REQ and updates it to include
        the task status in parentheses, e.g., "`Implementing Tasks`: TASK-10 (COMPLETED)"
        
        Args:
            artifact_manager: The ArtifactManager instance
            req_id: The REQ artifact ID to update
            task_id: The TASK artifact ID that implements this REQ
            status: The status of the TASK to display
        """
        # Get the current REQ content
        req_result = artifact_manager.get_artifact(req_id)
        
        if not req_result.get("success"):
            raise Exception(f"Failed to retrieve REQ {req_id}: {req_result.get('message')}")
        
        req_content = req_result["content"]
        
        # Parse current implementing tasks using header manager
        header_line, current_headers, body_content = self._header_manager.parse_managed_headers(req_content)
        current_tasks_str = current_headers.get('IMPLEMENTING_TASKS', '')
        
        # Parse current tasks from comma-separated string
        if current_tasks_str.strip():
            current_tasks = [task.strip() for task in current_tasks_str.split(',')]
        else:
            current_tasks = []
        
        # Update the task list to include status for this task
        updated_tasks = []
        task_found = False
        
        for task in current_tasks:
            # Remove any existing status from task string
            clean_task = task.split(' (')[0].strip()
            if clean_task == task_id:
                # Replace this task with the new status
                updated_tasks.append(f"{task_id} ({status})")
                task_found = True
            else:
                # Keep other tasks as they were
                updated_tasks.append(task)
        
        # If task wasn't found in the list, add it
        if not task_found:
            updated_tasks.append(f"{task_id} ({status})")
        
        # Convert back to comma-separated string and replace the entire list
        updated_tasks_str = ','.join(updated_tasks) if updated_tasks else ''
        
        # For list types, we need to replace the entire value, not append
        # So we'll build the updated content manually to avoid the header manager's append logic
        header_line, current_headers, body_content = self._header_manager.parse_managed_headers(req_content)
        
        # Update the IMPLEMENTING_TASKS header directly
        updated_headers = current_headers.copy()
        if updated_tasks_str:
            updated_headers['IMPLEMENTING_TASKS'] = updated_tasks_str
        elif 'IMPLEMENTING_TASKS' in updated_headers:
            # Remove the header if no tasks remain
            del updated_headers['IMPLEMENTING_TASKS']
        
        # Get artifact type for header ordering
        artifact_info = self._header_manager.extract_artifact_type_and_id(req_content)
        if not artifact_info:
            raise Exception(f"Could not determine artifact type for REQ {req_id}")
        
        artifact_type, _ = artifact_info
        applicable_headers = self._header_manager.get_managed_headers_for_type(artifact_type)
        
        # Rebuild the content with proper header ordering
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
        
        updated_content = '\n'.join(result_lines)
        
        # Debug logging
        logger.info(f"Updating REQ {req_id} implementing task {task_id} with status {status}")
        
        # Update the REQ artifact with the new content
        update_result = artifact_manager._update_non_file_artifact(req_id, updated_content)
        
        if not update_result.get("success"):
            raise Exception(f"Failed to update REQ {req_id}: {update_result.get('message')}")
    

class UACCHandler(ArtifactHandler):
    """Handler for UACC artifact processing."""
    
    def mark_step_done(self, artifact_id: str, step_number: str, artifact_manager) -> Dict[str, Any]:
        """Mark a step as done in a UACC artifact.
        
        Args:
            artifact_id: The UACC artifact ID (e.g., "UACC-17")
            step_number: The step number to mark as done (e.g., "17.1")
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with success status and message
        """
        import re
        
        try:
            # Get the current UACC content
            uacc_result = artifact_manager.get_artifact(artifact_id)
            
            if not uacc_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to retrieve UACC {artifact_id}: {uacc_result.get('message')}"
                }
            
            uacc_content = uacc_result["content"]
            lines = uacc_content.split('\n')
            
            # Find the step line to mark as done
            # Pattern: [ ] X.Y description  ->  [x] X.Y description
            step_pattern = re.compile(r'^(\[ \]) (' + re.escape(step_number) + r') (.+)$')
            updated = False
            
            for i, line in enumerate(lines):
                match = step_pattern.match(line)
                if match:
                    # Replace [ ] with [x] while preserving the rest of the line
                    lines[i] = f"[x] {match.group(2)} {match.group(3)}"
                    updated = True
                    break
            
            if not updated:
                return {
                    "success": False,
                    "message": f"Step {step_number} not found in UACC {artifact_id} or already marked as done"
                }
            
            updated_content = '\n'.join(lines)
            
            # Update the UACC artifact with the new content
            update_result = artifact_manager._update_non_file_artifact(artifact_id, updated_content)
            
            if not update_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to update UACC {artifact_id}: {update_result.get('message')}"
                }
            
            return {
                "success": True,
                "message": f"Marked step {step_number} as done in UACC {artifact_id}",
                "file_path": update_result.get("file_path")
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error marking step done in UACC {artifact_id}: {str(e)}"
            }
    
    def update_status(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Override to add covering test update logic for UACC status updates.
        
        Args:
            artifact_id: The artifact ID to update
            status: The new status to set
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with combined update results including covering test updates
        """
        try:
            # Step 1: Always update index first
            index_result = self.update_status_in_index(artifact_id, status)
            
            # Step 2: Update content using the existing method
            content_result = self.update_status_content(artifact_id, status, artifact_manager)
            
            # Step 3: Update covering tests in REQ artifacts
            covering_test_result = self._update_covering_tests(artifact_id, status, artifact_manager)
            
            # Step 4: Combine all results
            messages = []
            success = True
            
            if index_result.get("success"):
                messages.append(f"Index: {index_result.get('message')}")
            else:
                messages.append(f"Index warning: {index_result.get('message')}")
            
            if content_result.get("success"):
                messages.append(f"Content: {content_result.get('message')}")
            else:
                messages.append(f"Content error: {content_result.get('message')}")
                success = False
            
            if covering_test_result.get("success"):
                if covering_test_result.get("updated_reqs"):
                    messages.append(f"Covering tests: {covering_test_result.get('message')}")
            else:
                messages.append(f"Covering tests error: {covering_test_result.get('message')}")
                # Don't fail the whole operation for covering test errors
            
            return {
                "success": success,
                "artifact_id": artifact_id,
                "status": status,
                "updates": messages,
                "index_result": index_result,
                "content_result": content_result,
                "covering_test_result": covering_test_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating {artifact_id}: {str(e)}"
            }
    
    def _update_covering_tests(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Update covering test references in REQ artifacts when UACC status changes.
        
        Args:
            artifact_id: The UACC artifact ID (e.g., "UACC-17")
            status: The new status
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with update results
        """
        try:
            from .artifact_index_manager import get_artifact_index_manager
            
            updated_reqs = []
            errors = []
            
            # Get index manager to search for REQ artifacts
            index_manager = get_artifact_index_manager()
            
            # Search for all REQ artifacts
            all_artifacts = index_manager.get_all_artifacts()
            req_artifacts = [artifact for artifact in all_artifacts 
                           if artifact.get("artifact_id", "").startswith("REQ-")]
            
            for req_entry in req_artifacts:
                req_id = req_entry.get("artifact_id")
                if not req_id:
                    continue
                
                try:
                    # Get REQ content
                    req_result = artifact_manager.get_artifact(req_id)
                    if not req_result.get("success"):
                        continue
                    
                    req_content = req_result["content"]
                    
                    # Parse REQ headers to check covering tests
                    req_header_line, req_headers, req_body = self._header_manager.parse_managed_headers(req_content)
                    covering_tests_str = req_headers.get('COVERING_TESTS', '')
                    
                    if not covering_tests_str or artifact_id not in covering_tests_str:
                        continue  # This REQ doesn't reference our artifact
                    
                    # Update the status notation for our artifact in the covering tests
                    updated_covering_tests = self._update_test_status_in_list(covering_tests_str, artifact_id, status)
                    
                    if updated_covering_tests != covering_tests_str:
                        # Update REQ with new covering tests
                        updated_req_headers = req_headers.copy()
                        updated_req_headers['COVERING_TESTS'] = updated_covering_tests
                        
                        # Rebuild REQ content
                        req_type_info = self._header_manager.extract_artifact_type_and_id(req_content)
                        if req_type_info:
                            req_type, _ = req_type_info
                            applicable_headers = self._header_manager.get_managed_headers_for_type(req_type)
                            
                            result_lines = [req_header_line]
                            for item_key, item_config in applicable_headers.items():
                                if item_key in updated_req_headers:
                                    label = item_config['label']
                                    value = updated_req_headers[item_key]
                                    result_lines.append(f"`{label.rstrip(':')}`: {value}")
                            
                            if req_body.strip():
                                result_lines.append(req_body)
                            
                            updated_req_content = '\n'.join(result_lines)
                            
                            # Save updated REQ
                            update_result = artifact_manager.update_artifact(req_id, updated_req_content)
                            if update_result.get("success"):
                                updated_reqs.append(req_id)
                            else:
                                errors.append(f"Failed to update {req_id}: {update_result.get('message')}")
                
                except Exception as e:
                    errors.append(f"Error processing {req_id}: {str(e)}")
            
            if updated_reqs:
                message = f"Updated covering tests in {len(updated_reqs)} REQ artifacts: {', '.join(updated_reqs)}"
            else:
                message = "No REQ artifacts with covering tests needed updates"
            
            return {
                "success": True,
                "message": message,
                "updated_reqs": updated_reqs,
                "errors": errors if errors else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating covering tests: {str(e)}"
            }
    
    def _update_test_status_in_list(self, covering_tests_str: str, artifact_id: str, status: str) -> str:
        """Update status notation for a specific artifact in a covering tests list.
        
        Args:
            covering_tests_str: Comma-separated list of covering tests (e.g., "UACC-17 (NEW),SACC-18 (ACTIVE)")
            artifact_id: The artifact ID to update (e.g., "UACC-17")
            status: The new status
            
        Returns:
            Updated covering tests string
        """
        import re
        
        # Split by comma and process each test
        tests = [test.strip() for test in covering_tests_str.split(',')]
        updated_tests = []
        
        for test in tests:
            if test.startswith(artifact_id):
                # Update or add status notation
                # Pattern: UACC-17 (OLD_STATUS) -> UACC-17 (NEW_STATUS)
                # Or: UACC-17 -> UACC-17 (NEW_STATUS)
                test_without_status = re.sub(r'\s*\([^)]*\)$', '', test)
                updated_test = f"{test_without_status} ({status})"
                updated_tests.append(updated_test)
            else:
                updated_tests.append(test)
        
        return ','.join(updated_tests)
    
    def update_status_content(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Update status for UACC artifact using ArtifactHeaderManager."""
        try:
            # Get the current UACC content
            uacc_result = artifact_manager.get_artifact(artifact_id)
            
            if not uacc_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to retrieve UACC {artifact_id}: {uacc_result.get('message')}"
                }
            
            uacc_content = uacc_result["content"]
            
            # Use the header manager to update the status
            header_updates = {'STATUS': status}
            updated_content = self._header_manager.update_managed_header(uacc_content, header_updates)
            
            # Update the UACC artifact with the new content
            update_result = artifact_manager._update_non_file_artifact(artifact_id, updated_content)
            
            if not update_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to update UACC {artifact_id}: {update_result.get('message')}"
                }
            
            return {
                "success": True,
                "message": f"Updated UACC {artifact_id} status to {status}",
                "file_path": update_result.get("file_path")
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating UACC {artifact_id}: {str(e)}"
            }


class SACCHandler(ArtifactHandler):
    """Handler for SACC artifact processing."""
    
    def mark_step_done(self, artifact_id: str, step_number: str, artifact_manager) -> Dict[str, Any]:
        """Mark a step as done in a SACC artifact.
        
        Args:
            artifact_id: The SACC artifact ID (e.g., "SACC-17")
            step_number: The step number to mark as done (e.g., "17.1")
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with success status and message
        """
        import re
        
        try:
            # Get the current SACC content
            sacc_result = artifact_manager.get_artifact(artifact_id)
            
            if not sacc_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to retrieve SACC {artifact_id}: {sacc_result.get('message')}"
                }
            
            sacc_content = sacc_result["content"]
            lines = sacc_content.split('\n')
            
            # Find the step line to mark as done
            # Pattern: [ ] X.Y description  ->  [x] X.Y description
            step_pattern = re.compile(r'^(\[ \]) (' + re.escape(step_number) + r') (.+)$')
            updated = False
            
            for i, line in enumerate(lines):
                match = step_pattern.match(line)
                if match:
                    # Replace [ ] with [x] while preserving the rest of the line
                    lines[i] = f"[x] {match.group(2)} {match.group(3)}"
                    updated = True
                    break
            
            if not updated:
                return {
                    "success": False,
                    "message": f"Step {step_number} not found in SACC {artifact_id} or already marked as done"
                }
            
            updated_content = '\n'.join(lines)
            
            # Update the SACC artifact with the new content
            update_result = artifact_manager._update_non_file_artifact(artifact_id, updated_content)
            
            if not update_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to update SACC {artifact_id}: {update_result.get('message')}"
                }
            
            return {
                "success": True,
                "message": f"Marked step {step_number} as done in SACC {artifact_id}",
                "file_path": update_result.get("file_path")
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error marking step done in SACC {artifact_id}: {str(e)}"
            }
    
    def update_status_content(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Update status for SACC artifact using ArtifactHeaderManager."""
        try:
            # Get the current SACC content
            sacc_result = artifact_manager.get_artifact(artifact_id)
            
            if not sacc_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to retrieve SACC {artifact_id}: {sacc_result.get('message')}"
                }
            
            sacc_content = sacc_result["content"]
            
            # Use the header manager to update the status
            header_updates = {'STATUS': status}
            updated_content = self._header_manager.update_managed_header(sacc_content, header_updates)
            
            # Update the SACC artifact with the new content
            update_result = artifact_manager._update_non_file_artifact(artifact_id, updated_content)
            
            if not update_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to update SACC {artifact_id}: {update_result.get('message')}"
                }
            
            return {
                "success": True,
                "message": f"Updated SACC {artifact_id} status to {status}",
                "file_path": update_result.get("file_path")
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating SACC {artifact_id}: {str(e)}"
            }
    
    def update_status(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Override to add covering test update logic for SACC status updates.
        
        Args:
            artifact_id: The artifact ID to update
            status: The new status to set
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with combined update results including covering test updates
        """
        try:
            # Step 1: Always update index first
            index_result = self.update_status_in_index(artifact_id, status)
            
            # Step 2: Update content using the existing method
            content_result = self.update_status_content(artifact_id, status, artifact_manager)
            
            # Step 3: Update covering tests in REQ artifacts
            covering_test_result = self._update_covering_tests(artifact_id, status, artifact_manager)
            
            # Step 4: Combine all results
            messages = []
            success = True
            
            if index_result.get("success"):
                messages.append(f"Index: {index_result.get('message')}")
            else:
                messages.append(f"Index warning: {index_result.get('message')}")
            
            if content_result.get("success"):
                messages.append(f"Content: {content_result.get('message')}")
            else:
                messages.append(f"Content error: {content_result.get('message')}")
                success = False
            
            if covering_test_result.get("success"):
                if covering_test_result.get("updated_reqs"):
                    messages.append(f"Covering tests: {covering_test_result.get('message')}")
            else:
                messages.append(f"Covering tests error: {covering_test_result.get('message')}")
                # Don't fail the whole operation for covering test errors
            
            return {
                "success": success,
                "artifact_id": artifact_id,
                "status": status,
                "updates": messages,
                "index_result": index_result,
                "content_result": content_result,
                "covering_test_result": covering_test_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating {artifact_id}: {str(e)}"
            }
    
    def _update_covering_tests(self, artifact_id: str, status: str, artifact_manager) -> Dict[str, Any]:
        """Update covering test references in REQ artifacts when SACC status changes.
        
        Args:
            artifact_id: The SACC artifact ID (e.g., "SACC-18")
            status: The new status
            artifact_manager: The ArtifactManager instance
            
        Returns:
            Dictionary with update results
        """
        try:
            from .artifact_index_manager import get_artifact_index_manager
            
            updated_reqs = []
            errors = []
            
            # Get index manager to search for REQ artifacts
            index_manager = get_artifact_index_manager()
            
            # Search for all REQ artifacts
            all_artifacts = index_manager.get_all_artifacts()
            req_artifacts = [artifact for artifact in all_artifacts 
                           if artifact.get("artifact_id", "").startswith("REQ-")]
            
            for req_entry in req_artifacts:
                req_id = req_entry.get("artifact_id")
                if not req_id:
                    continue
                
                try:
                    # Get REQ content
                    req_result = artifact_manager.get_artifact(req_id)
                    if not req_result.get("success"):
                        continue
                    
                    req_content = req_result["content"]
                    
                    # Parse REQ headers to check covering tests
                    req_header_line, req_headers, req_body = self._header_manager.parse_managed_headers(req_content)
                    covering_tests_str = req_headers.get('COVERING_TESTS', '')
                    
                    if not covering_tests_str or artifact_id not in covering_tests_str:
                        continue  # This REQ doesn't reference our artifact
                    
                    # Update the status notation for our artifact in the covering tests
                    updated_covering_tests = self._update_test_status_in_list(covering_tests_str, artifact_id, status)
                    
                    if updated_covering_tests != covering_tests_str:
                        # Update REQ with new covering tests
                        updated_req_headers = req_headers.copy()
                        updated_req_headers['COVERING_TESTS'] = updated_covering_tests
                        
                        # Rebuild REQ content
                        req_type_info = self._header_manager.extract_artifact_type_and_id(req_content)
                        if req_type_info:
                            req_type, _ = req_type_info
                            applicable_headers = self._header_manager.get_managed_headers_for_type(req_type)
                            
                            result_lines = [req_header_line]
                            for item_key, item_config in applicable_headers.items():
                                if item_key in updated_req_headers:
                                    label = item_config['label']
                                    value = updated_req_headers[item_key]
                                    result_lines.append(f"`{label.rstrip(':')}`: {value}")
                            
                            if req_body.strip():
                                result_lines.append(req_body)
                            
                            updated_req_content = '\n'.join(result_lines)
                            
                            # Save updated REQ
                            update_result = artifact_manager.update_artifact(req_id, updated_req_content)
                            if update_result.get("success"):
                                updated_reqs.append(req_id)
                            else:
                                errors.append(f"Failed to update {req_id}: {update_result.get('message')}")
                
                except Exception as e:
                    errors.append(f"Error processing {req_id}: {str(e)}")
            
            if updated_reqs:
                message = f"Updated covering tests in {len(updated_reqs)} REQ artifacts: {', '.join(updated_reqs)}"
            else:
                message = "No REQ artifacts with covering tests needed updates"
            
            return {
                "success": True,
                "message": message,
                "updated_reqs": updated_reqs,
                "errors": errors if errors else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating covering tests: {str(e)}"
            }
    
    def _update_test_status_in_list(self, covering_tests_str: str, artifact_id: str, status: str) -> str:
        """Update status notation for a specific artifact in a covering tests list.
        
        Args:
            covering_tests_str: Comma-separated list of covering tests (e.g., "UACC-17 (NEW),SACC-18 (ACTIVE)")
            artifact_id: The artifact ID to update (e.g., "SACC-18")
            status: The new status
            
        Returns:
            Updated covering tests string
        """
        import re
        
        # Split by comma and process each test
        tests = [test.strip() for test in covering_tests_str.split(',')]
        updated_tests = []
        
        for test in tests:
            if test.startswith(artifact_id):
                # Update or add status notation
                # Pattern: SACC-18 (OLD_STATUS) -> SACC-18 (NEW_STATUS)
                # Or: SACC-18 -> SACC-18 (NEW_STATUS)
                test_without_status = re.sub(r'\s*\([^)]*\)$', '', test)
                updated_test = f"{test_without_status} ({status})"
                updated_tests.append(updated_test)
            else:
                updated_tests.append(test)
        
        return ','.join(updated_tests)


class ArtifactHandlerFactory:
    """Factory for creating artifact type handlers."""
    
    _handlers = {
        "TASKPRD": TaskPRDHandler,
        "PRD": PRDHandler,
        "REQ": REQHandler,
        "TASK": TASKHandler,
        "UACC": UACCHandler,
        "SACC": SACCHandler,
        # Future handlers can be added here
    }
    
    @classmethod
    def get_handler(cls, artifact_type: str) -> Optional[ArtifactHandler]:
        """Get a handler for the specified artifact type.
        
        Args:
            artifact_type: The artifact type (e.g., "TASKPRD", "PRD")
            
        Returns:
            Handler instance if available, None otherwise
        """
        handler_class = cls._handlers.get(artifact_type.upper())
        if handler_class:
            return handler_class()
        return None
    
    @classmethod
    def has_handler(cls, artifact_type: str) -> bool:
        """Check if a handler exists for the specified artifact type.
        
        Args:
            artifact_type: The artifact type to check
            
        Returns:
            True if a handler exists, False otherwise
        """
        return artifact_type.upper() in cls._handlers
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Get a list of artifact types that have handlers.
        
        Returns:
            List of supported artifact types
        """
        return list(cls._handlers.keys())


def handle_artifact_status_update(artifact_id: str, status: str, artifact_manager) -> Optional[Dict[str, Any]]:
    """Handle status updates for an artifact using the appropriate handler.
    
    Args:
        artifact_id: The artifact ID (e.g., "REQ-2", "TASK-47")
        status: The new status to set
        artifact_manager: The ArtifactManager instance
        
    Returns:
        Handler results if a handler exists, None otherwise
    """
    # Extract artifact type from ID
    if '-' in artifact_id:
        artifact_type = artifact_id.split('-')[0].upper()
        handler = ArtifactHandlerFactory.get_handler(artifact_type)
        if handler:
            return handler.update_status(artifact_id, status, artifact_manager)
    return None


def handle_artifact_finalization(artifact_type: str, artifact_id: str, id_mapping: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Handle post-finalization activities for an artifact if a handler exists.
    
    This is a convenience function that encapsulates the factory pattern
    and handler invocation in a single call.
    
    Args:
        artifact_type: The artifact type (e.g., "TASKPRD")
        artifact_id: The main artifact ID that was finalized
        id_mapping: Dictionary mapping provisional IDs to final artifact IDs
        
    Returns:
        Handler results if a handler exists, None otherwise
    """
    handler = ArtifactHandlerFactory.get_handler(artifact_type)
    if handler:
        return handler.finalize(artifact_id, id_mapping)
    return None
