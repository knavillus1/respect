"""ReSpecT Manager MCP server

Tools for managing software development lifecycle documents using the ReSpecT framework.
Environment variables expected (provided by editor/mcp.json or shell):
    - RESPECT_DOC_REPO_ROOT (Root directory for ReSpecT repository)
    - DEBUG_MODE (Debug mode true/false)
    - RESPECT_PROVISIONAL_DOC_STORE (Root directory for ReSpecT provisional documents)

Available tools:
    - get_provisional_store: return provisional document store root path
    - get_document_template: get document template by artifact type
    - get_mode_instructions: get mode instructions by fetching content from instruction files
    - get_valid_artifact_types: get list of all valid artifact types and their information
    - search_artifacts_by_id: find artifacts by document ID (integer) or artifact ID (e.g., PRD-1), returns JSON with filename matches and optionally content references
    - search_artifacts_by_type: search for artifacts by type (e.g., PRD, REQ) or multiple types (e.g., PRD,REQ,TASK) and optionally by status
    - get_artifact: get the full content of artifacts (file-based or non-file embedded sections using ### headings)
    - update_artifact_status: update the STATUS of an artifact by ID and status value
    - update_artifact_content: update the CONTENT/TEXT of an artifact by ID and new content
    - finalize_prov_file: find provisional file by name in provisional store, assign proper artifact IDs, save to document repository root, and delete provisional file; optional file name suffix
    - mark_artifact_step_done: mark a step as done in a TASK artifact (changes [ ] to [x] for specified step number)
    - add_artifact: add a nested artifact (e.g., UACC/SACC) into a parent artifact when permitted
    - add_reference: add a reference from one artifact to another (creates "Referenced by" entries)
    - register_provisional_ids: register provisional IDs in existing artifacts without file renaming (UACC/SACC types)
"""
from __future__ import annotations

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import respect_manager
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from fastmcp import FastMCP

app = FastMCP("respect_mcp_server")

# Set up logging
logging.basicConfig(level=logging.INFO)

# Import respect_manager modules after app creation
import respect_manager.artifact_manager as artifact_manager
from respect_manager.template_manager import get_template_manager
from respect_manager.artifact_type_manager import get_artifact_type_manager


@app.tool()
def get_provisional_store() -> str:
    """Return the ReSpecT provisional document store root path."""
    return os.getenv("RESPECT_PROVISIONAL_DOC_STORE", "")


@app.tool()
def get_document_template(artifact_type: str) -> str:
    """Get a document template by artifact type.
    
    Args:
        artifact_type: The artifact type (e.g., 'PRD', 'TASKPRD', 'PRD', 'REQ')
    
    Returns:
        The template content as a string
    """
    try:
        template_manager = get_template_manager()
        
        # Get the template content
        template_content = template_manager.get_document_template(artifact_type)
        
        return template_content
        
    except Exception as e:
        return f"Error: {str(e)}"


@app.tool()
def get_mode_instructions(mode: str) -> str:
    """Get mode instructions by fetching content from instruction files.
    
    Args:
        mode: The mode name (e.g., 'Generate PRD', 'Generate Tasks')
    
    Returns:
        The instruction file content as a string
    """
    try:
        # Map mode names to instruction file names
        mode_mapping = {
            "Generate PRD": "generate-prd.md",
            "Generate TASKPRD": "generate-taskprd.md",
            "Task Implementation": "execute-task.md",
            "Setup PRD Tests": "setup-prd-tests.md",
            "Review Architecture": "review-architecture.md",
            "ReSpecT Master": "respect-master.md",
            "Detect Project State": "detect-project-state.md",
            "Acceptance Test": "acceptance-test.md",
            "Failed Tests TASKPRD":"generate-taskprd-failed-test.md",
            "PRD Review and Completion":"review-prd-complete.md",
            "Architecture Summary":"architecture-summary.md",
            "Architecture Review":"architecture-review-prd.md",
        }
        
        # Get the instruction file name
        instruction_file = mode_mapping.get(mode)
        if not instruction_file:
            available_modes = ", ".join(mode_mapping.keys())
            return f"Error: Unknown mode '{mode}'. Available modes: {available_modes}"
        
        # Build the path to the instruction file
        current_dir = Path(__file__).parent
        project_root = current_dir.parent
        instructions_dir = project_root / "instructions"
        instruction_path = instructions_dir / instruction_file
        
        # Check if file exists
        if not instruction_path.exists():
            return f"Error: Instruction file not found at {instruction_path}"
        
        # Read and return the file content
        with open(instruction_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
        
    except Exception as e:
        return f"Error: {str(e)}"


@app.tool()
def get_valid_artifact_types() -> str:
    """Get a list of all valid artifact types and their information.
    
    Returns:
        JSON string containing artifact type definitions
    """
    try:
        type_manager = get_artifact_type_manager()
        
        # Get all artifact types info
        all_types = type_manager.get_all_artifact_types_info()
        
        # Format as a readable string
        result = "Valid Artifact Types:\n\n"
        for artifact_type, info in all_types.items():
            result += f"{artifact_type}: {info['name']}\n"
            result += f"  Description: {info['description']}\n"
            result += f"  Template: {info['template_name']}\n\n"
        
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"


@app.tool()
def search_artifacts_by_id(identifier: str, search_references: str = "true") -> str:
    """Find artifacts by document ID (integer) or artifact ID.
    
    This tool searches the document repository for files containing the specified identifier
    and returns structured artifact information from the index.
    
    It can handle:
    - Document ID (integer): e.g., "36" to find document with ID 36
    - Artifact ID: e.g., "PRD-1", "REQ-7", "TASK-8" to find specific artifacts
    
    Results are categorized into:
    - Direct matches: Artifacts whose IDs/names directly match the search identifier
    - Content references: Artifacts that reference the search identifier in their content (only if search_references="true")
    
    Each artifact includes: artifact_id, doc_id, name, and status from the index.
    
    Args:
        identifier: Either a document ID (integer) or artifact ID (e.g., PRD-1)
        search_references: Whether to search for files that reference the artifact ID in their content ("true" or "false", default: "true")
    
    Returns:
        JSON-formatted string with categorized artifact information, or error message if not found
    """
    try:
        # Convert string parameter to boolean
        search_refs_bool = search_references.lower() in ("true", "1", "yes", "on")
        
        # Get the artifact ID manager and delegate to it
        manager = artifact_manager.get_artifact_id_manager()
        result = manager.search_artifacts_by_id(identifier, search_refs_bool)
        
        if not result.get("success"):
            return f"Error: {result.get('message', 'Unknown error')}"
        
        # Format the response as structured JSON
        direct_matches = result.get("direct_matches", [])
        content_references = result.get("content_references", [])
        
        if not direct_matches and not content_references:
            return f"No artifacts found for identifier: {identifier}"
        
        # Build structured response
        response = {
            "identifier": identifier,
            "search_references": search_refs_bool,
            "direct_matches": direct_matches,
            "content_references": content_references,
            "summary": {
                "direct_matches_count": len(direct_matches),
                "content_references_count": len(content_references),
                "total_found": len(direct_matches) + len(content_references)
            }
        }
        
        import json
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return f"Error: {str(e)}"


@app.tool()
def get_artifact(identifier: str) -> str:
    """Get the full content of a specific artifact by document ID or artifact ID.
    
    This tool retrieves and returns the complete content of an artifact.
    For file artifacts (is_file=true), it returns the entire file content.
    For non-file artifacts (is_file=false), it extracts the content section 
    between the ### heading and the next ### heading using the three hash marks convention.
    
    Args:
        identifier: Either a document ID (integer) or artifact ID (e.g., PRD-1, TASK-13)
    
    Returns:
        The full content of the artifact file or extracted section, with metadata
    """
    try:
        # Get the artifact ID manager and delegate to it
        manager = artifact_manager.get_artifact_id_manager()
        result = manager.get_artifact(identifier)
        
        if not result.get("success"):
            return f"Error: {result.get('message', 'Unknown error')}"
        
        # Return the content with some metadata (excluding file path for security)
        content = result.get("content", "")
        artifact_info = result.get("artifact_info", {})
        
        response = f"# Content for {artifact_info.get('artifact_id', identifier)}\n"
        response += f"**Status:** {artifact_info.get('status', 'Unknown')}\n"
        response += f"**Name:** {artifact_info.get('name', 'Unknown')}\n\n"
        response += "---\n\n"
        response += content
        
        return response
        
    except Exception as e:
        return f"Error: {str(e)}"


@app.tool()
def search_artifacts_by_type(artifact_type: str, status: str = "", parent: str = "") -> str:
    """Search for artifacts by type and optionally by status and parent.
    
    This tool searches the artifact index for all artifacts of a specific type
    and can optionally filter by status and parent artifact.
    
    Args:
        artifact_type: The artifact type(s) to search for. Can be a single type (e.g., PRD) or comma-separated types (e.g., PRD,REQ,TASK,TASKPRD)
        status: Optional status filter (e.g., NEW, DRAFT, APPROVED, ACTIVE, COMPLETED). Leave empty to get all statuses.
        parent: Optional parent artifact ID filter (e.g., PRD-1). Leave empty to get all parents.
    
    Returns:
        JSON-formatted string with matching artifacts, or error message if none found
    """
    try:
        # Get the artifact ID manager
        manager = artifact_manager.get_artifact_id_manager()
        
        # Convert empty strings to None for optional parameters
        status_filter = status if status and status.strip() else None
        parent_filter = parent if parent and parent.strip() else None
        
        # Parse artifact types (comma-separated)
        artifact_types = [t.strip().upper() for t in artifact_type.split(',') if t.strip()]
        
        if not artifact_types:
            return "Error: No valid artifact types provided"
        
        # Aggregate results from all artifact types
        all_artifacts = []
        by_type_summary = {}
        errors = []
        
        for single_type in artifact_types:
            try:
                result = manager.search_artifacts_by_type(single_type, status_filter, parent_filter)
                
                if result.get("success"):
                    type_artifacts = result.get("artifacts", [])
                    all_artifacts.extend(type_artifacts)
                    by_type_summary[single_type] = len(type_artifacts)
                else:
                    by_type_summary[single_type] = 0
                    errors.append(f"{single_type}: {result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                by_type_summary[single_type] = 0
                errors.append(f"{single_type}: {str(e)}")
        
        # Build structured response
        response = {
            "artifact_types": artifact_types,
            "status_filter": status_filter,
            "parent_filter": parent_filter,
            "artifacts": all_artifacts,
            "summary": {
                "total_found": len(all_artifacts),
                "by_type": by_type_summary,
                "by_status": {}
            }
        }
        
        # Add errors if any occurred
        if errors:
            response["errors"] = errors
        
        # Count artifacts by status for summary
        for artifact in all_artifacts:
            artifact_status = artifact.get("status") or "NO_STATUS"
            if artifact_status != "NO_STATUS":
                artifact_status = artifact_status.upper()
            response["summary"]["by_status"][artifact_status] = response["summary"]["by_status"].get(artifact_status, 0) + 1
        
        import json
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return f"Error: {str(e)}"


@app.tool()
def update_artifact_status(artifact_id: str, status: str) -> str:
    """Update the STATUS of an artifact in the repository.
    
    ⚠️  IMPORTANT: This tool updates the STATUS of artifacts (e.g., NEW → ACTIVE → COMPLETED).
    ⚠️  To update artifact CONTENT/TEXT, use the update_artifact_content tool instead.
    
    This tool updates the status of an artifact across the entire repository:
    1. Validates the artifact ID format and existence
    2. Validates the status against allowed statuses from artifact_statuses.json
    3. Updates the artifact entry in index.md with the new status
    4. Updates the Status line (second line) in the artifact's own file
    5. Updates all references to this artifact in other files (lines starting with "### <artifact_id>")
    6. For TASK artifacts: Also updates implementing REQ references to show the new status
    
    Args:
        artifact_id: Either a document ID (integer) or artifact ID (e.g., PRD-1, 36)
        status: The new status to set (e.g., DRAFT, REVIEW, APPROVED, ACTIVE, COMPLETED, CANCELLED, ARCHIVED)
    
    Returns:
        Status message with details of what was updated, or error message with valid statuses if invalid
    """
    try:
        # Import here to avoid circular imports
        from respect_manager.artifact_type_manager import get_artifact_type_manager
        
        # Pre-validate artifact ID format if it's not a pure number (document ID)
        if not artifact_id.isdigit():
            type_manager = get_artifact_type_manager()
            validation = type_manager.validate_artifact_id_format(artifact_id)
            
            if not validation["valid"]:
                error_msg = f"Invalid artifact ID format: {validation['error']}"
                if validation.get("suggestions"):
                    error_msg += f"\n\nSuggestions:\n" + "\n".join(f"  • {s}" for s in validation["suggestions"])
                return f"Error: {error_msg}"
        
        # Get the artifact ID manager
        manager = artifact_manager.get_artifact_id_manager()
        
        # Update the artifact status
        result = manager.update_artifact_status(artifact_id, status)
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            if "valid_statuses" in result:
                valid_statuses = result["valid_statuses"]
                artifact_type = result.get("artifact_type", "")
                type_info = f" for {artifact_type}" if artifact_type else ""
                return f"{error_msg}\n\nValid statuses{type_info}: {', '.join(valid_statuses)}"
            return f"Error: {error_msg}"
        
        # Format the successful result
        response = f"Successfully updated status for {result['artifact_id']} to {result['status']}\n\n"
        response += "Updates performed:\n"
        for update in result["updates"]:
            response += f"  - {update}\n"
        
        return response
        
    except Exception as e:
        return f"Error: {str(e)}"


@app.tool()
def finalize_prov_file(provisional_file_name: str, file_name_suffix: str | None = None) -> str:
    """Finalize a provisional document by finding it in the provisional store, assigning proper artifact IDs, and saving to the document repository.
    
    Args:
        provisional_file_name: Name of the provisional document file to process (e.g., "PRD-PROVISIONAL1.md")
        file_name_suffix: Optional suffix (50 chars or fewer) to append to the finalized filename
    
    Returns:
        Status message with source and target paths, and ID mappings
    """
    try:
        # Validate input
        if not provisional_file_name:
            return "Error: provisional_file_name is required"
        # Validate optional suffix length if provided
        if file_name_suffix is not None and len(file_name_suffix) > 50:
            return "Error: file_name_suffix must be 50 characters or fewer"

        # Get the artifact ID manager and delegate to it
        manager = artifact_manager.get_artifact_id_manager()
        result = manager.finalize_provisional_file(provisional_file_name, file_name_suffix)
        
        # Format the response
        if not result.get("id_mappings"):
            return f"No provisional artifact IDs found in {provisional_file_name}"
        
        response = f"Successfully finalized provisional document\n"
        if result.get("target"):
            response += f"Source: {result['source_filename']}\n"
            response += f"Target: {result['target']}\n\n"
        response += "ID mappings:\n"
        for provisional_id, new_id in result["id_mappings"].items():
            response += f"  {provisional_id} -> {new_id}\n"
        
        # Include handler result if available
        if "handler_result" in result:
            handler_result = result["handler_result"]
            response += f"\nPost-finalization handler:\n"
            response += f"  Type: {handler_result.get('handler_type', 'Unknown')}\n"
            response += f"  Status: {handler_result.get('status', 'Unknown')}\n"
            response += f"  Message: {handler_result.get('message', 'No message')}\n"
            if "actions_performed" in handler_result:
                response += f"  Actions: {', '.join(handler_result['actions_performed'])}\n"
        
        return response
        
    except Exception as e:
        return f"Error: {str(e)}"


@app.tool()
def update_artifact_content(identifier: str, content: str) -> str:
    """Update the CONTENT/TEXT of an artifact by identifier (doc ID or artifact ID).
    
    ⚠️  IMPORTANT: This tool updates the CONTENT/TEXT of artifacts, NOT the status.
    ⚠️  To update artifact STATUS, use the update_artifact_status tool instead.

    - File artifacts: overwrite entire file content.
    - Non-file artifacts: replace only the artifact section (### heading → next ###).
    - Respects artifact type configuration: requires can_tool_update = true.

    Args:
        identifier: Document ID (digits) or full artifact ID (e.g., PRD-1)
        content: New content to write. For non-file artifacts, if the content does not
                 start with "### <ARTIFACT-ID>", a heading line will be prepended using
                 the artifact name from the index when available.

    Returns:
        Status message indicating success or detailed error.
    """
    try:
        manager = artifact_manager.get_artifact_id_manager()
        result = manager.update_artifact(identifier, content)
        if not result.get("success"):
            return f"Error: {result.get('message', 'Unknown error')}"

        artifact_id = result.get("artifact_id") or identifier
        return f"Successfully updated {artifact_id}"
    except Exception as e:
        return f"Error: {str(e)}"


@app.tool()
def mark_artifact_step_done(artifact_id: str, step_number: str) -> str:
    """Mark a step as done in a TASK artifact.
    
    Args:
        artifact_id: The artifact ID (e.g., "TASK-10")
        step_number: The step number to mark as done (e.g., "10.1")
        
    Returns:
        Success message or error description
    """
    try:
        # Extract artifact type from ID
        if '-' not in artifact_id:
            return f"Error: Invalid artifact ID format: {artifact_id}"
        
        artifact_type = artifact_id.split('-')[0].upper()
        
        # Validate artifact type supports steps using type manager
        type_manager = get_artifact_type_manager()
        
        if not type_manager.has_capability(artifact_type, "has_steps"):
            return f"Error: Artifact type {artifact_type} does not support step marking"
        
        # Get the appropriate handler
        from respect_manager.artifact_type_handler import ArtifactHandlerFactory
        handler = ArtifactHandlerFactory.get_handler(artifact_type)
        
        if not handler:
            return f"Error: No handler available for artifact type {artifact_type}"
        
        # Get artifact manager
        mgr = artifact_manager.get_artifact_id_manager()
        
        # Call the handler method (all handlers have this method, though not all implement it)
        result = handler.mark_step_done(artifact_id, step_number, mgr)
        
        if not result.get("success"):
            return f"Error: {result.get('message', 'Unknown error')}"
        
        return result.get("message", f"Successfully marked step {step_number} as done in {artifact_id}")
        
    except Exception as e:
        return f"Error: {str(e)}"


@app.tool()
def add_artifact(parent_artifact_id: str, new_artifact_type: str, new_artifact_content: str) -> str:
    """Add a nested artifact under a parent artifact when allowed by type config.
    
    Currently implemented for PRD parent type, supporting nested UACC and SACC content
    inserted under the PRD's `## Acceptance Tests` section.

    Args:
        parent_artifact_id: Parent artifact ID (e.g., PRD-1)
        new_artifact_type: Type of nested artifact (e.g., UACC or SACC)
        new_artifact_content: Markdown content to insert
    """
    try:
        # Setup managers
        manager = artifact_manager.get_artifact_id_manager()
        type_manager = get_artifact_type_manager()

        # Validate parent id format and resolve type
        normalized_parent_id = type_manager.validate_artifact_id(parent_artifact_id)
        parent_type = type_manager.get_artifact_type_from_id(normalized_parent_id)

        # Only PRD supported for now
        if parent_type != "PRD":
            return f"Error: add_artifact currently supports PRD as parent; got {parent_type}"

        # Validate nested type against PRD's addable list
        prd_info = type_manager.get_artifact_type_info("PRD")
        allowed = set(prd_info.get("addable_nested_artifact_types", []))
        normalized_new_type = type_manager.validate_and_normalize_artifact_type(new_artifact_type)
        if normalized_new_type not in allowed:
            return f"Error: {normalized_new_type} is not allowed under PRD. Allowed: {', '.join(sorted(allowed))}"

        # Delegate to PRD handler
        from respect_manager.artifact_type_handler import ArtifactHandlerFactory
        handler = ArtifactHandlerFactory.get_handler("PRD")
        add_fn = getattr(handler, 'add_nested_artifact', None) if handler else None
        if not callable(add_fn):
            return "Error: PRD handler does not support nested artifact insertion"

        result = add_fn(normalized_parent_id, normalized_new_type, new_artifact_content, manager)
        if not isinstance(result, dict):
            return "Error: Unexpected handler response"
        if not result.get("success"):
            return f"Error: {result.get('message', 'Unknown error')}"
        return result.get("message", "Successfully added nested artifact")
    except Exception as e:
        return f"Error: {str(e)}"


@app.tool()
def add_reference(target_artifact_id: str, ref_artifact_id: str) -> str:
    """Add a reference from one artifact to another.
    
    This creates a "Referenced by" entry in the target artifact, indicating
    that the reference artifact refers to or depends on the target.
    
    Args:
        target_artifact_id: The artifact being referenced (e.g., PRD-1)
        ref_artifact_id: The artifact making the reference (e.g., TASKPRD-16)
    
    Returns:
        Status message indicating success or error
    """
    try:
        # Setup managers
        manager = artifact_manager.get_artifact_id_manager()
        type_manager = get_artifact_type_manager()

        # Validate target artifact ID format
        try:
            normalized_target_id = type_manager.validate_artifact_id(target_artifact_id)
        except ValueError as e:
            return f"Error: Invalid target artifact ID: {str(e)}"

        # Validate reference artifact ID format  
        try:
            normalized_ref_id = type_manager.validate_artifact_id(ref_artifact_id)
        except ValueError as e:
            return f"Error: Invalid reference artifact ID: {str(e)}"

        # Get the appropriate handler for the target artifact
        target_type = type_manager.get_artifact_type_from_id(normalized_target_id)
        
        from respect_manager.artifact_type_handler import ArtifactHandlerFactory
        handler = ArtifactHandlerFactory.get_handler(target_type)
        
        if not handler:
            return f"Error: No handler available for artifact type {target_type}"
        
        # Check if handler supports add_reference
        add_ref_fn = getattr(handler, 'add_reference', None)
        if not callable(add_ref_fn):
            return f"Error: {target_type} handler does not support adding references"

        # Call the handler method
        result = add_ref_fn(normalized_target_id, normalized_ref_id, manager)
        
        if not isinstance(result, dict):
            return "Error: Unexpected handler response"
        if not result.get("success"):
            return f"Error: {result.get('message', 'Unknown error')}"
        return result.get("message", "Successfully added reference")
        
    except Exception as e:
        return f"Error: {str(e)}"


@app.tool()
def register_provisional_ids(artifact_id: str, allowed_types: str = "UACC,SACC") -> str:
    """Register provisional IDs found in an existing artifact without renaming the file.
    
    This tool scans an existing finalized artifact for provisional IDs (typically
    nested artifacts like UACC-PROVISIONAL1, SACC-PROVISIONAL2) and assigns them
    proper artifact IDs, updating the content in place. This is useful when you have
    nested provisional artifacts that need to be formalized.
    
    Args:
        artifact_id: The existing artifact to scan and update (e.g., "PRD-1", "TASKPRD-16")
        allowed_types: Comma-separated list of artifact types to register (default: "UACC,SACC")
                      Only provisional IDs of these types will be processed
    
    Returns:
        Status message with details of registered IDs or error information
    """
    try:
        # Setup manager
        manager = artifact_manager.get_artifact_id_manager()
        
        # Parse allowed types
        allowed_types_list = None
        if allowed_types.strip():
            allowed_types_list = [t.strip().upper() for t in allowed_types.split(",") if t.strip()]
        
        # Register provisional IDs
        result = manager.register_provisional_ids(artifact_id, allowed_types_list)
        
        if not isinstance(result, dict):
            return "Error: Unexpected manager response"
        
        if not result.get("success"):
            return f"Error: {result.get('message', 'Unknown error')}"
        
        id_mappings = result.get("id_mappings", {})
        if not id_mappings:
            return result.get("message", "No provisional IDs found to register")
        
        # Format the response with mapping details and status updates
        mapping_details = []
        for provisional_id, new_id in id_mappings.items():
            mapping_details.append(f"{provisional_id} -> {new_id}")
        
        base_message = result.get("message", "Successfully registered provisional IDs")
        mapping_text = "\n".join(mapping_details)
        
        response = f"{base_message}\n\nID Mappings:\n{mapping_text}"
        
        # Add status update information if available
        status_updates = result.get("status_updates", {})
        if status_updates:
            response += "\n\nStatus Updates:"
            for artifact_id, status_info in status_updates.items():
                if artifact_id == "error":
                    response += f"\n  Error updating statuses: {status_info}"
                else:
                    success_status = "✓" if status_info.get("success") else "✗"
                    response += f"\n  {success_status} {artifact_id}: {status_info.get('message', 'Unknown')}"
        
        # Add test coverage update information if available
        test_coverage_updates = result.get("test_coverage_updates", {})
        if test_coverage_updates and not test_coverage_updates.get("error"):
            updated_reqs = test_coverage_updates.get("updated_reqs", [])
            if updated_reqs:
                response += f"\n\nTest Coverage Updates:"
                response += f"\n  Updated {len(updated_reqs)} REQ artifact(s): {', '.join(updated_reqs)}"
            
            errors = test_coverage_updates.get("errors")
            if errors:
                response += f"\n  Errors: {len(errors)} error(s) occurred during test coverage updates"
        elif test_coverage_updates and test_coverage_updates.get("error"):
            response += f"\n\nTest Coverage Error: {test_coverage_updates.get('error')}"
        
        return response
        
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":  # pragma: no cover
    if hasattr(app, "run_stdio"):
        app.run_stdio() # type: ignore
    elif hasattr(app, "serve"):
        app.serve() # type: ignore
    elif hasattr(app, "run"):
        app.run()
    else:
        raise RuntimeError("FastMCP app has no run_stdio/run/serve method; cannot start.")
