"""Artifact ID Management for ReSpecT

This module handles the generation and management of artifact IDs in the ReSpecT format:
<ARTIFACT_TYPE>-<ID>

The ID component is unique and sequential, stored in an index.md file at the repository root.
"""

import os
import fcntl
import re
from pathlib import Path
from typing import Optional, Dict, Set, Any, List, Tuple
import logging

from .artifact_type_manager import get_artifact_type_manager
from .artifact_index_manager import get_artifact_index_manager
from .artifact_header_manager import ArtifactHeaderManager

logger = logging.getLogger(__name__)

# Module version for artifact manager functionality. Keep in sync with pyproject version.
__version__ = "0.1.0"


class ArtifactManager:
    """Manages artifact ID generation and storage for ReSpecT repositories."""
    
    def __init__(self, repo_root: str):
        """Initialize the artifact ID manager.
        
        Args:
            repo_root: Path to the root of the ReSpecT repository
        """
        self.repo_root = Path(repo_root)
    
    @staticmethod
    def get_version() -> str:
        """Return the artifact_manager module version string.
        
        Static accessor for environments that prefer querying via the class.
        """
        return __version__
    
    @staticmethod
    def get_version_footer() -> str:
        """Return the ReSpecT version footer for finalized documents.
        
        Returns a minimal markdown comment that identifies the ReSpecT version.
        """
        return f"\n\n<!-- ReSpecT v{__version__} -->"
    
    def resolve_artifact_identifier(self, identifier: str) -> Optional[str]:
        """Resolve an identifier (docID or artifactID) to an artifact ID.
        
        This utility method standardizes ID resolution across all tools that accept
        either document IDs (integers) or full artifact IDs.
        
        Args:
            identifier: Either a document ID (integer) or artifact ID (e.g., PRD-1)
            
        Returns:
            Resolved artifact ID or None if not found
        """
        try:
            index_manager = get_artifact_index_manager(str(self.repo_root))
            
            # Check if identifier is a pure integer (document ID)
            if identifier.isdigit():
                doc_id_str = identifier  # Keep as string for comparison
                # Look up artifact by document ID in the index
                artifacts = index_manager.get_all_artifacts()
                for artifact in artifacts:
                    # Compare as strings since doc_id from index is a string
                    if str(artifact.get('doc_id')) == doc_id_str:
                        return artifact.get('artifact_id')
                return None
            else:
                # Assume it's already an artifact ID, normalize to uppercase
                artifact_id = identifier.upper()
                # Verify it exists in the index
                artifacts = index_manager.get_all_artifacts()
                for artifact in artifacts:
                    if artifact.get('artifact_id') == artifact_id:
                        return artifact_id
                return None
                
        except Exception as e:
            logger.error(f"Error resolving identifier {identifier}: {e}")
            return None
    
    def get_artifact_id(self, artifact_type: str, artifact_name: Optional[str] = None, is_file: bool = True, parent: Optional[str] = None) -> str:
        """Generate the next artifact ID in ReSpecT format.
        
        Args:
            artifact_type: The type of artifact (e.g., 'REQ', 'TASK', 'FTR')
            artifact_name: Optional name of the artifact to store in index
            is_file: Whether this artifact will have its own file (default True)
            parent: Optional parent artifact ID for nested artifacts
            
        Returns:
            A new artifact ID in format: ARTIFACT_TYPE-ID
            
        Raises:
            OSError: If file operations fail
            ValueError: If artifact_type is invalid
        """
        # Validate and normalize artifact type using the artifact type manager
        try:
            type_manager = get_artifact_type_manager()
            artifact_type = type_manager.validate_and_normalize_artifact_type(artifact_type)
        except ValueError as e:
            logger.error(f"Invalid artifact type: {e}")
            raise
        
        # Get the index manager
        index_manager = get_artifact_index_manager(str(self.repo_root))
        
        # Get the next document ID
        next_id = index_manager.get_next_doc_id()
        
        # Generate the full artifact ID
        artifact_id = f"{artifact_type}-{next_id}"
        
        # Add to the index
        index_manager.add_artifact(artifact_id, artifact_name, None, is_file, parent)
        
        logger.info(f"Generated new artifact ID: {artifact_id} (is_file: {is_file}, parent: {parent})")
        return artifact_id
    
    def search_artifacts_by_id(self, identifier: str, search_references: bool = False) -> Dict[str, Any]:
        """Find artifacts by document ID (integer) or artifact ID, section-aware.

        Enhancements:
        - Direct match is resolved from the index (supports non-file nested artifacts).
        - Content references attribute matches to the containing nested artifact section
          when present, otherwise to the file-level artifact.
        - Self-references (the searched artifact itself) are excluded from content_references.
        """
        try:
            # Get document repository root
            repo_root = os.getenv("RESPECT_DOC_REPO_ROOT")
            if not repo_root:
                return {"success": False, "message": "RESPECT_DOC_REPO_ROOT environment variable not set"}

            repo_path = Path(repo_root)
            if not repo_path.exists():
                return {"success": False, "message": f"Document repository not found at {repo_root}"}

            index_manager = get_artifact_index_manager(str(self.repo_root))
            type_manager = get_artifact_type_manager()
            header_manager = ArtifactHeaderManager(type_manager=type_manager)

            # Resolve identifier to artifact_id (preferred) for stable searching
            target_artifact_id: Optional[str] = None
            direct_matches: List[Dict[str, Any]] = []

            if identifier.isdigit():
                # Lookup by document ID
                by_doc = index_manager.get_artifact_by_doc_id(identifier)
                if by_doc:
                    tid = by_doc["artifact_id"]
                    target_artifact_id = tid
                    direct_matches = self._get_artifact_info_from_index([tid])
            else:
                # Normalize and lookup by artifact ID
                candidate_id = identifier.strip().upper()
                by_id = index_manager.get_artifact_by_id(candidate_id)
                if by_id:
                    tid = by_id["artifact_id"]
                    target_artifact_id = tid
                    direct_matches = self._get_artifact_info_from_index([tid])

            # Only perform content reference scanning when requested and we have a concrete artifact ID to search
            content_reference_data: Dict[str, List[Dict[str, Any]]] = {}
            if search_references and target_artifact_id:
                content_reference_data = self._scan_content_references(
                    target_artifact_id, repo_path
                )

            # Convert aggregated reference data into artifact info results
            content_references: List[Dict[str, Any]] = []
            if content_reference_data:
                content_references = self._get_artifact_info_from_index_with_references(
                    list(content_reference_data.keys()), content_reference_data
                )

            # If nothing found at all, return an error
            total_found = len(direct_matches) + len(content_references)
            if total_found == 0:
                return {
                    "success": False,
                    "message": f"No artifacts found for identifier: {identifier}",
                    "direct_matches": [],
                    "content_references": [],
                }

            return {
                "success": True,
                "direct_matches": direct_matches,
                "content_references": content_references,
                "message": f"Found {len(direct_matches)} direct matches" + (
                    f" and {len(content_references)} content references" if search_references else ""
                ),
            }

        except Exception as e:
            return {"success": False, "message": f"Error searching for artifacts: {str(e)}"}

    def _scan_content_references(self, target_artifact_id: str, repo_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        """Scan all markdown files and attribute references to nested or file artifacts.

        Returns a mapping of container artifact_id -> list of { line_number, line_content }.
        Excludes self-references for target_artifact_id.
        """
        # Managers
        index_manager = get_artifact_index_manager(str(self.repo_root))
        type_manager = get_artifact_type_manager()
        header_manager = ArtifactHeaderManager(type_manager=type_manager)

        # Build set of known artifact IDs from index
        index_ids = {a["artifact_id"] for a in index_manager.get_all_artifacts()}

        # Patterns
        # Use real word boundaries (no over-escaping), case-insensitive
        id_pattern = re.compile(r"\b" + re.escape(target_artifact_id) + r"\b", re.IGNORECASE)
        section_header_pat = re.compile(r"^\s*###\s+([A-Z]+-\d+)\b")

        reference_data: Dict[str, List[Dict[str, Any]]] = {}

        for file_path in repo_path.rglob("*.md"):
            if file_path.name == "index.md":
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            lines = content.split("\n")

            # Determine file-level artifact ID
            file_artifact_id = None
            try:
                header_info = header_manager.extract_artifact_type_and_id(content)
                if header_info:
                    _, file_artifact_id = header_info
            except Exception:
                file_artifact_id = None

            # Build nested sections
            sections: List[Dict[str, Any]] = []
            current_section: Optional[Dict[str, Any]] = None
            for i, line in enumerate(lines, 1):
                m = section_header_pat.match(line)
                if m:
                    if current_section is not None:
                        current_section["end"] = i - 1
                        sections.append(current_section)
                    sec_id = m.group(1).upper()
                    # Validate type format; still record if not recognized
                    try:
                        type_manager.get_artifact_type_from_id(sec_id)
                    except Exception:
                        pass
                    current_section = {"artifact_id": sec_id, "start": i, "end": None}
            if current_section is not None:
                current_section["end"] = len(lines)
                sections.append(current_section)

            def find_container(line_no: int) -> Optional[str]:
                for sec in sections:
                    if sec["start"] <= line_no <= sec["end"]:
                        return sec["artifact_id"]
                return file_artifact_id

            for line_num, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                if id_pattern.search(line):
                    container_id = find_container(line_num) or file_artifact_id
                    if not container_id:
                        continue
                    if container_id.upper() == target_artifact_id.upper():
                        # Skip self-reference (e.g., the REQ-6 header)
                        continue
                    # Record; enrichment step will ignore IDs not present in index
                    reference_data.setdefault(container_id, []).append({
                        "line_number": line_num,
                        "line_content": line.strip(),
                    })

        # Filter to only artifacts present in index to avoid returning unknown IDs
        filtered = {aid: lines for aid, lines in reference_data.items() if aid in index_ids}
        return filtered
    
    def get_artifact(self, identifier: str) -> Dict[str, Any]:
        """Get the content of a specific artifact by document ID or artifact ID.
        
        This method finds and returns the full content of an artifact file, or for
        non-file artifacts, extracts the content section between ### headings.
        
        Args:
            identifier: Either a document ID (integer) or artifact ID (e.g., PRD-1)
            
        Returns:
            Dictionary with 'success', 'content', 'file_path', 'artifact_info', and 'message' keys
        """
        try:
            # Resolve the identifier to an artifact ID
            artifact_id = self.resolve_artifact_identifier(identifier)
            if not artifact_id:
                return {"success": False, "message": f"No artifact found for identifier: {identifier}"}
            
            # Get artifact info from index
            index_manager = get_artifact_index_manager(str(self.repo_root))
            artifact_info = index_manager.get_artifact_by_id(artifact_id)
            
            if not artifact_info:
                return {"success": False, "message": f"Artifact {artifact_id} not found in index"}
            
            # Get document repository root
            repo_root = os.getenv("RESPECT_DOC_REPO_ROOT")
            if not repo_root:
                return {"success": False, "message": "RESPECT_DOC_REPO_ROOT environment variable not set"}
            
            repo_path = Path(repo_root)
            if not repo_path.exists():
                return {"success": False, "message": f"Document repository not found at {repo_root}"}
            
            is_file = artifact_info.get("is_file", False)
            
            if is_file:
                # Handle file artifacts (existing logic)
                return self._get_file_artifact(artifact_id, artifact_info, repo_path)
            else:
                # Handle non-file artifacts (new logic)
                return self._get_non_file_artifact(artifact_id, artifact_info, repo_path)
            
        except Exception as e:
            return {"success": False, "message": f"Error retrieving artifact: {str(e)}"}

    def update_artifact(self, identifier: str, new_content: str) -> Dict[str, Any]:
        """Update the text of an artifact by identifier (doc ID or artifact ID).

        For file artifacts, replaces the entire file content with ``new_content``.
        For non-file artifacts, replaces only the artifact's section (### heading to next ###).

        Validates that the artifact type allows tool updates via can_tool_update.

        Args:
            identifier: Document ID (digits) or full artifact ID (e.g., PRD-1)
            new_content: The replacement content. For non-file artifacts, if it does not
                        start with the expected heading, a heading line will be prepended
                        as "### <ARTIFACT-ID>: <Name>" (name from index if available).

        Returns:
            Result dictionary with success flag, message, and details.
        """
        try:
            # Resolve identifier to artifact ID
            artifact_id = self.resolve_artifact_identifier(identifier)
            if not artifact_id:
                return {"success": False, "message": f"No artifact found for identifier: {identifier}"}

            # Get artifact info from index
            index_manager = get_artifact_index_manager(str(self.repo_root))
            artifact_info = index_manager.get_artifact_by_id(artifact_id)
            if not artifact_info:
                return {"success": False, "message": f"Artifact {artifact_id} not found in index"}

            # Determine artifact type from ID and check if tools may update it
            type_manager = get_artifact_type_manager()
            artifact_type = type_manager.get_artifact_type_from_id(artifact_id)
            if not type_manager.can_tool_update(artifact_type):
                return {
                    "success": False,
                    "message": f"Artifact type '{artifact_type}' does not allow direct tool updates"
                }

            is_file = artifact_info.get("is_file", False)
            if is_file:
                return self._update_file_artifact(artifact_id, artifact_info, new_content)
            else:
                # Ensure section content contains a heading; prepend if needed
                prepared_content = new_content
                heading_prefix = f"### {artifact_id}"
                if not new_content.lstrip().startswith(heading_prefix):
                    artifact_name = artifact_info.get("name")
                    header_line = heading_prefix + (f": {artifact_name}" if artifact_name else "")
                    prepared_content = header_line + "\n" + new_content.lstrip("\n")
                return self._update_non_file_artifact(artifact_id, prepared_content)

        except Exception as e:
            return {"success": False, "message": f"Error updating artifact: {str(e)}"}
    
    def _get_file_artifact(self, artifact_id: str, artifact_info: Dict[str, Any], repo_path: Path) -> Dict[str, Any]:
        """Get content for file-based artifacts."""
        # Search for files that start with the artifact ID and end with .md
        # Use rglob to search nested directories
        pattern = f"{artifact_id}_*.md"  # Files like PRD-1_description.md
        alt_pattern = f"{artifact_id}.md"  # Files like PRD-1.md
        
        found_file = None
        
        # First try the underscore pattern (artifact_id_*.md)
        for file_path in repo_path.rglob(pattern):
            if file_path.is_file():
                found_file = file_path
                break
                
        # If not found, try the exact pattern (artifact_id.md)
        if not found_file:
            for file_path in repo_path.rglob(alt_pattern):
                if file_path.is_file():
                    found_file = file_path
                    break
        
        if not found_file:
            return {"success": False, "message": f"No file found for artifact {artifact_id}"}
        
        # Read and return the content
        try:
            content = found_file.read_text(encoding='utf-8')
            return {
                "success": True,
                "content": content,
                "file_path": str(found_file),
                "artifact_info": artifact_info,
                "message": f"Successfully retrieved content for {artifact_id}"
            }
        except (UnicodeDecodeError, PermissionError) as e:
            return {"success": False, "message": f"Error reading file {found_file}: {str(e)}"}

    def _update_file_artifact(self, artifact_id: str, artifact_info: Dict[str, Any], new_content: str) -> Dict[str, Any]:
        """Update content for file-based artifacts by overwriting the file content."""
        # Locate the file similarly to _get_file_artifact
        repo_root = os.getenv("RESPECT_DOC_REPO_ROOT")
        if not repo_root:
            return {"success": False, "message": "RESPECT_DOC_REPO_ROOT environment variable not set"}

        repo_path = Path(repo_root)
        if not repo_path.exists():
            return {"success": False, "message": f"Document repository not found at {repo_root}"}

        # Search for files that start with the artifact ID and end with .md
        # Use rglob to search nested directories
        pattern = f"{artifact_id}_*.md"  # Files like PRD-1_description.md
        alt_pattern = f"{artifact_id}.md"  # Files like PRD-1.md
        
        found_file = None
        
        # First try the underscore pattern (artifact_id_*.md)
        for file_path in repo_path.rglob(pattern):
            if file_path.is_file():
                found_file = file_path
                break
                
        # If not found, try the exact pattern (artifact_id.md)
        if not found_file:
            for file_path in repo_path.rglob(alt_pattern):
                if file_path.is_file():
                    found_file = file_path
                    break

        if not found_file:
            return {"success": False, "message": f"No file found for artifact {artifact_id}"}

        try:
            found_file.write_text(new_content, encoding='utf-8')
            return {
                "success": True,
                "artifact_id": artifact_id,
                "file_path": str(found_file),
                "message": f"Successfully updated file artifact {artifact_id}"
            }
        except (UnicodeDecodeError, PermissionError) as e:
            return {"success": False, "message": f"Error writing file {found_file}: {str(e)}"}
    
    def _get_non_file_artifact(self, artifact_id: str, artifact_info: Dict[str, Any], repo_path: Path) -> Dict[str, Any]:
        """Get content for non-file artifacts embedded in other documents."""
        # Search all markdown files for the artifact heading
        found_file = None
        artifact_content = None
        
        for file_path in repo_path.rglob("*.md"):
            try:
                content = file_path.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                # Look for the artifact heading (### ARTIFACT-ID)
                for i, line in enumerate(lines):
                    if line.strip().startswith(f"### {artifact_id}"):
                        found_file = file_path
                        # Extract content from this heading to the next ### heading or end of file
                        artifact_lines = [line]  # Include the heading line
                        
                        # Collect lines until next ### heading or end of file
                        for j in range(i + 1, len(lines)):
                            next_line = lines[j]
                            # Stop if we hit another ### heading
                            if next_line.strip().startswith("### ") and not next_line.strip().startswith(f"### {artifact_id}"):
                                break
                            artifact_lines.append(next_line)
                        
                        artifact_content = '\n'.join(artifact_lines).rstrip()
                        break
                
                if artifact_content:
                    break
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if not found_file or not artifact_content:
            return {"success": False, "message": f"No content found for non-file artifact {artifact_id}"}
        
        return {
            "success": True,
            "content": artifact_content,
            "file_path": str(found_file),
            "artifact_info": artifact_info,
            "message": f"Successfully retrieved content for non-file artifact {artifact_id}"
        }
    
    def _update_non_file_artifact(self, artifact_id: str, new_content: str) -> Dict[str, Any]:
        """Update content for non-file artifacts embedded in other documents.
        
        Args:
            artifact_id: The artifact ID to update
            new_content: The new content to replace the existing artifact section with
            
        Returns:
            Dictionary with update results including success status and file path
        """
        # Get document repository root
        repo_root = os.getenv("RESPECT_DOC_REPO_ROOT")
        if not repo_root:
            return {"success": False, "message": "RESPECT_DOC_REPO_ROOT environment variable not set"}
        
        repo_path = Path(repo_root)
        if not repo_path.exists():
            return {"success": False, "message": f"Document repository not found at {repo_root}"}
        
        # Search all markdown files for the artifact heading
        found_file = None
        start_index = None
        end_index = None
        
        for file_path in repo_path.rglob("*.md"):
            try:
                content = file_path.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                # Look for the artifact heading (### ARTIFACT-ID)
                for i, line in enumerate(lines):
                    if line.strip().startswith(f"### {artifact_id}"):
                        found_file = file_path
                        start_index = i
                        
                        # Find the end of this artifact section
                        end_index = len(lines)  # Default to end of file
                        for j in range(i + 1, len(lines)):
                            next_line = lines[j]
                            # Stop if we hit another ### heading
                            if next_line.strip().startswith("### ") and not next_line.strip().startswith(f"### {artifact_id}"):
                                end_index = j
                                break
                        
                        break
                
                if found_file:
                    break
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if not found_file or start_index is None:
            return {"success": False, "message": f"No artifact section found for {artifact_id}"}
        
        # At this point, end_index is guaranteed to be set (either to len(lines) or to j)
        assert end_index is not None, "end_index should be set when artifact is found"
        
        try:
            # Read the current content
            content = found_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Ensure new_content doesn't have trailing newlines that would create extra blank lines
            new_content_lines = new_content.rstrip('\n').split('\n')
            
            # Replace the artifact section with new content
            updated_lines = lines[:start_index] + new_content_lines + lines[end_index:]
            
            # Write the updated content back to the file
            found_file.write_text('\n'.join(updated_lines), encoding='utf-8')
            
            return {
                "success": True,
                "file_path": str(found_file),
                "artifact_id": artifact_id,
                "lines_replaced": end_index - start_index,
                "new_lines_count": len(new_content_lines),
                "message": f"Successfully updated non-file artifact {artifact_id} in {found_file.name}"
            }
            
        except (UnicodeDecodeError, PermissionError) as e:
            return {"success": False, "message": f"Error updating file {found_file}: {str(e)}"}
    
    def search_artifacts_by_type(self, artifact_type: str, status: Optional[str] = None, parent: Optional[str] = None) -> Dict[str, Any]:
        """Search for artifacts by type and optionally by status and parent.
        
        This method searches the index for artifacts matching the specified type
        and optionally filters by status and parent artifact.
        
        Status filter: Pass a single status (e.g., "ACTIVE") or a comma-separated
        list (e.g., "NEW,ACTIVE,TESTING"). Matching is case-insensitive.
        
        Args:
            artifact_type: The artifact type to search for (e.g., PRD, REQ, TASK, FTR)
            status: Optional status filter. Single value or comma-separated list
                    (e.g., "DRAFT,APPROVED,ACTIVE").
            parent: Optional parent artifact ID filter (e.g., PRD-1)
            
        Returns:
            Dictionary with 'success', 'artifacts', and 'message' keys
        """
        try:
            # Normalize artifact type to uppercase
            artifact_type = artifact_type.upper()
            
            # Validate artifact type
            try:
                type_manager = get_artifact_type_manager()
                if not type_manager.is_valid_artifact_type(artifact_type):
                    valid_types = list(type_manager.get_all_artifact_types_info().keys())
                    return {
                        "success": False, 
                        "message": f"Invalid artifact type: {artifact_type}. Valid types: {', '.join(valid_types)}",
                        "artifacts": []
                    }
            except Exception as e:
                logger.warning(f"Could not validate artifact type: {e}")
            
            # Prepare status filters (comma-separated allowed)
            status_values: Optional[set] = None
            if status:
                # Split, trim, and upper-case
                parts = [s.strip().upper() for s in status.split(',') if s.strip()]
                if parts:
                    status_values = set(parts)

            # Get all artifacts from index
            index_manager = get_artifact_index_manager(str(self.repo_root))
            all_artifacts = index_manager.get_all_artifacts()
            
            # Filter by artifact type
            matching_artifacts = []
            for artifact in all_artifacts:
                artifact_id = artifact.get("artifact_id", "")
                # Extract type from artifact ID (e.g., PRD-1 -> PRD)
                if "-" in artifact_id:
                    current_type = artifact_id.split("-")[0].upper()
                    if current_type == artifact_type:
                        # Apply status filter if provided
                        artifact_status = artifact.get("status")
                        status_match = (
                            status_values is None or (
                                artifact_status and artifact_status.upper() in status_values
                            )
                        )
                        
                        # Apply parent filter if provided
                        artifact_parent = artifact.get("parent")
                        parent_match = parent is None or (parent and artifact_parent and artifact_parent == parent)
                        
                        if status_match and parent_match:
                            matching_artifacts.append({
                                "artifact_id": artifact["artifact_id"],
                                "doc_id": artifact["doc_id"],
                                "name": artifact["name"],
                                "status": artifact["status"],
                                "parent": artifact.get("parent")
                            })
            
            if not matching_artifacts:
                status_filter = f" with status '{status}'" if status else ""
                parent_filter = f" with parent '{parent}'" if parent else ""
                return {
                    "success": False,
                    "message": f"No artifacts found for type '{artifact_type}'{status_filter}{parent_filter}",
                    "artifacts": []
                }
            
            status_filter = f" with status '{status}'" if status else ""
            parent_filter = f" with parent '{parent}'" if parent else ""
            return {
                "success": True,
                "artifacts": matching_artifacts,
                "message": f"Found {len(matching_artifacts)} artifacts of type '{artifact_type}'{status_filter}{parent_filter}"
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error searching artifacts by type: {str(e)}", "artifacts": []}
    
    
    
    def _get_artifact_info_from_index(self, artifact_ids: List[str]) -> List[Dict[str, Any]]:
        """Get artifact information from the index for the given artifact IDs.
        
        Args:
            artifact_ids: List of artifact IDs to look up
            
        Returns:
            List of dictionaries with artifact information including id, name, and status
        """
        index_manager = get_artifact_index_manager(str(self.repo_root))
        
        results = []
        for artifact_id in artifact_ids:
            artifact = index_manager.get_artifact_by_id(artifact_id)
            if artifact:
                results.append({
                    "artifact_id": artifact["artifact_id"],
                    "doc_id": artifact["doc_id"],
                    "name": artifact["name"],
                    "status": artifact["status"]
                })
        
        return results
    
    def _get_artifact_info_from_index_with_references(self, artifact_ids: List[str], reference_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Get artifact information from the index with reference line details.
        
        Args:
            artifact_ids: List of artifact IDs to look up
            reference_data: Dictionary mapping artifact_id to list of matching line details
            
        Returns:
            List of dictionaries with artifact information including matching_lines
        """
        index_manager = get_artifact_index_manager(str(self.repo_root))
        
        results = []
        for artifact_id in artifact_ids:
            artifact = index_manager.get_artifact_by_id(artifact_id)
            if artifact:
                # Strip line_number from matching lines, keep only line_content
                raw_lines = reference_data.get(artifact_id, [])
                matching_lines = [
                    {"line_content": entry.get("line_content", "")}
                    for entry in raw_lines
                    if isinstance(entry, dict)
                ]
                artifact_info = {
                    "artifact_id": artifact["artifact_id"],
                    "doc_id": artifact["doc_id"],
                    "name": artifact["name"],
                    "status": artifact["status"],
                    "matching_lines": matching_lines
                }
                results.append(artifact_info)
        
        return results
    
    def _extract_artifact_name(self, content: str, artifact_id: str) -> Optional[str]:
        """Extract the artifact name from document content.
        
        Looks for patterns like "PRD-51: Character Creation PRD" in the content.
        
        Args:
            content: The document content to search
            artifact_id: The artifact ID to find the name for
            
        Returns:
            The artifact name if found, None otherwise
        """
        lines = content.split('\n')
        
        # Look for the artifact ID followed by a colon and name
        pattern = rf'^#+\s*{re.escape(artifact_id)}:\s*(.+)$'
        
        for line in lines:
            line = line.strip()
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                return name
        
        return None
    
    def _find_provisional_file(self, provisional_file_name: str, provisional_store: str) -> Path:
        """Find the provisional file in the provisional store.
        
        Args:
            provisional_file_name: Name of the provisional file to find
            provisional_store: Path to the provisional store
            
        Returns:
            Path to the provisional file
            
        Raises:
            FileNotFoundError: If the file is not found
        """
        provisional_store_path = Path(provisional_store)
        if not provisional_store_path.exists():
            raise FileNotFoundError(f"Provisional document store not found at {provisional_store}")
        
        # Look for the file in the provisional store
        for file_path in provisional_store_path.rglob(provisional_file_name):
            if file_path.is_file():
                return file_path
        
        raise FileNotFoundError(f"Provisional file '{provisional_file_name}' not found in {provisional_store}")
    
    def _process_provisional_ids(self, content: str, type_manager, parent_artifact_id: Optional[str] = None) -> tuple[Dict[str, str], str, Dict[str, str]]:
        """Process all provisional IDs in the content and generate new artifact IDs.
        
        Args:
            content: The document content
            type_manager: The artifact type manager
            parent_artifact_id: Optional parent artifact ID for nested artifacts
            
        Returns:
            Tuple of (id_mapping, updated_content, artifact_names)
            - id_mapping: Dict mapping provisional IDs to new artifact IDs
            - updated_content: Content with provisional IDs replaced
            - artifact_names: Dict mapping new artifact IDs to their names
        """
        # Find all provisional artifact IDs in the content
        provisional_ids = type_manager.find_provisional_artifact_ids(content)
        
        if not provisional_ids:
            return {}, content, {}
        
        logger.info(f"Found {len(provisional_ids)} provisional artifact IDs: {provisional_ids}")
        
        id_mapping: Dict[str, str] = {}
        artifact_names: Dict[str, str] = {}
        updated_content = content
        
        # Process main artifacts first (those that will have their own files)
        # Then process nested artifacts with the main artifact as parent
        main_artifacts = []
        nested_artifacts = []
        
        for provisional_id in sorted(provisional_ids):
            is_main = self._is_main_artifact(content, provisional_id)
            if is_main:
                main_artifacts.append(provisional_id)
            else:
                nested_artifacts.append(provisional_id)
        
        # Determine the parent for nested artifacts
        parent_for_nested = parent_artifact_id
        
        # Process main artifacts first
        for provisional_id in main_artifacts:
            try:
                # Parse the provisional ID to get the artifact type
                artifact_type, _temp_id = type_manager.parse_provisional_id(provisional_id)
                
                # Extract the artifact name from the content
                artifact_name = self._extract_artifact_name(content, provisional_id)
                
                # Main artifacts have their own files
                is_main_artifact = True
                
                # Generate a new proper artifact ID - main artifacts have no parent
                new_artifact_id = self.get_artifact_id(artifact_type, artifact_name, is_file=is_main_artifact, parent=None)
                
                # Store the mapping and name
                id_mapping[provisional_id] = new_artifact_id
                if artifact_name:
                    artifact_names[new_artifact_id] = artifact_name
                
                # If no explicit parent was provided, use the first main artifact as parent for nested ones
                if not parent_for_nested:
                    parent_for_nested = new_artifact_id
                
                # Replace all occurrences in the content
                # Use word boundaries to avoid partial replacements
                pattern = r'\b' + re.escape(provisional_id) + r'\b'
                updated_content = re.sub(pattern, new_artifact_id, updated_content)
                
                logger.info(f"Mapped {provisional_id} -> {new_artifact_id}" + (f" ({artifact_name})" if artifact_name else "") + f" [is_file: {is_main_artifact}]")
                
            except ValueError as e:
                logger.error(f"Error processing main artifact {provisional_id}: {e}")
                continue
        
        # Process nested artifacts with determined parent
        for provisional_id in nested_artifacts:
            try:
                # Parse the provisional ID to get the artifact type
                artifact_type, _temp_id = type_manager.parse_provisional_id(provisional_id)
                
                # Extract the artifact name from the content
                artifact_name = self._extract_artifact_name(content, provisional_id)
                
                # Nested artifacts don't have their own files
                is_main_artifact = False
                
                # Generate a new proper artifact ID - nested artifacts use determined parent
                new_artifact_id = self.get_artifact_id(artifact_type, artifact_name, is_file=is_main_artifact, parent=parent_for_nested)
                
                # Store the mapping and name
                id_mapping[provisional_id] = new_artifact_id
                if artifact_name:
                    artifact_names[new_artifact_id] = artifact_name
                
                # Replace all occurrences in the content
                # Use word boundaries to avoid partial replacements
                pattern = r'\b' + re.escape(provisional_id) + r'\b'
                updated_content = re.sub(pattern, new_artifact_id, updated_content)
                
                logger.info(f"Mapped {provisional_id} -> {new_artifact_id}" + (f" ({artifact_name})" if artifact_name else "") + f" [is_file: {is_main_artifact}, parent: {parent_for_nested}]")
                
            except ValueError as e:
                logger.error(f"Error processing nested artifact {provisional_id}: {e}")
                continue
        
        return id_mapping, updated_content, artifact_names
    
    def _is_main_artifact(self, content: str, artifact_id: str) -> bool:
        """Determine if an artifact is the main artifact (should have its own file).
        
        This checks:
        1. If the artifact appears in a top-level header (# or ##), OR
        2. If the artifact type configuration specifies is_file: true
        
        Args:
            content: The document content
            artifact_id: The artifact ID to check
            
        Returns:
            True if this is a main artifact that should have its own file
        """
        # First check if it appears in top-level headers
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#') and not line.startswith('###'):  # # or ## but not ###
                if artifact_id in line:
                    return True
        
        # Check if the artifact type configuration specifies is_file: true
        try:
            from .artifact_type_manager import get_artifact_type_manager
            type_manager = get_artifact_type_manager()
            
            # Extract artifact type from the ID
            if '-' in artifact_id:
                artifact_type = artifact_id.split('-')[0].upper()
                
                # Get the artifact type configuration
                type_info = type_manager.get_artifact_type_info(artifact_type)
                if type_info:
                    # Check if is_file is explicitly set to true
                    return type_info.get('is_file', False)
                    
        except Exception as e:
            logger.warning(f"Could not determine artifact type configuration for {artifact_id}: {e}")
        
        return False
    
    def _generate_target_filename(self, provisional_file_path: Path, id_mapping: Dict[str, str], file_name_suffix: Optional[str]) -> str:
        """Generate the target filename for the finalized document.
        
        Args:
            provisional_file_path: Path to the original provisional file
            id_mapping: Mapping of provisional IDs to new artifact IDs
            file_name_suffix: Optional suffix to append
            
        Returns:
            The target filename
        """
        target_stem = provisional_file_path.stem
        filename_ext = provisional_file_path.suffix
        
        # If the filename contains any provisional IDs we converted, replace in the stem
        for provisional_id, new_artifact_id in id_mapping.items():
            pattern = r'\b' + re.escape(provisional_id) + r'\b'
            if re.search(pattern, target_stem):
                target_stem = re.sub(pattern, new_artifact_id, target_stem)
                break  # Only one provisional ID should match the filename
        
        # If a suffix is provided, sanitize and append it
        if file_name_suffix is not None:
            s = file_name_suffix.strip().lower()
            s = re.sub(r'[^a-z0-9]+', '_', s)
            s = s.strip('_')
            if s:
                target_stem = f"{target_stem}_{s}"
        
        return f"{target_stem}{filename_ext}"
    
    def register_provisional_ids(self, artifact_id: str, allowed_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Register provisional IDs found in an existing artifact without renaming the file.
        
        This method scans an existing finalized artifact for provisional IDs (typically
        nested artifacts like UACC-PROVISIONAL1, SACC-PROVISIONAL2) and assigns them
        proper artifact IDs, updating the content in place.
        
        Args:
            artifact_id: The existing artifact to scan and update
            allowed_types: Optional list of artifact types to register (e.g., ['UACC', 'SACC'])
                          If None, all provisional IDs found will be registered
            
        Returns:
            Dictionary with registration results including ID mappings
        """
        try:
            # Get the artifact content
            artifact_result = self.get_artifact(artifact_id)
            if not artifact_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to retrieve {artifact_id}: {artifact_result.get('message')}"
                }
            
            content = artifact_result["content"]
            file_path = artifact_result.get("file_path")
            
            if not file_path:
                return {
                    "success": False,
                    "message": f"No file path found for {artifact_id}"
                }
            
            # Process provisional IDs with optional type filtering
            type_manager = get_artifact_type_manager()
            id_mapping, updated_content, artifact_names = self._process_provisional_ids_filtered(
                content, type_manager, allowed_types, parent_artifact_id=artifact_id
            )
            
            if not id_mapping:
                return {
                    "success": True,
                    "message": f"No provisional IDs found in {artifact_id}",
                    "id_mappings": {}
                }
            
            # Write the updated content back to the file
            from pathlib import Path
            Path(file_path).write_text(updated_content, encoding='utf-8')
            
            logger.info(f"Registered {len(id_mapping)} provisional IDs in {artifact_id}")
            
            # Update status to NEW for all newly registered artifacts
            status_updates = {}
            try:
                from .artifact_type_handler import ArtifactHandlerFactory
                
                for provisional_id, new_artifact_id in id_mapping.items():
                    # Get artifact type from the new artifact ID
                    artifact_type = type_manager.get_artifact_type_from_id(new_artifact_id)
                    
                    # Try to get a specific handler first
                    handler = ArtifactHandlerFactory.get_handler(artifact_type)
                    
                    if handler:
                        # Use specific handler if available
                        status_result = handler.update_status(new_artifact_id, "NEW", self)
                        status_updates[new_artifact_id] = {
                            "success": status_result.get("success", False),
                            "message": status_result.get("message", "Unknown")
                        }
                    else:
                        # Fall back to direct artifact manager status update
                        status_result = self.update_artifact_status(new_artifact_id, "NEW")
                        success = status_result.get("success", False)
                        if success:
                            message = "Updated via artifact manager"
                        else:
                            error_msg = status_result.get("error", "Update failed")
                            message = f"Failed: {error_msg}"
                        status_updates[new_artifact_id] = {
                            "success": success,
                            "message": message
                        }
                        
            except Exception as e:
                logger.warning(f"Error updating status for newly registered artifacts: {e}")
                status_updates["error"] = str(e)
            
            # Process test coverage for newly registered artifacts
            test_coverage_updates = {}
            try:
                test_coverage_updates = self._process_test_coverage_updates(updated_content, id_mapping)
                logger.info(f"Test coverage updates: {test_coverage_updates}")
            except Exception as e:
                logger.warning(f"Error processing test coverage updates: {e}")
                test_coverage_updates["error"] = str(e)
            
            return {
                "success": True,
                "message": f"Registered {len(id_mapping)} provisional IDs in {artifact_id}",
                "id_mappings": id_mapping,
                "artifact_names": artifact_names,
                "file_path": file_path,
                "status_updates": status_updates,
                "test_coverage_updates": test_coverage_updates
            }
            
        except Exception as e:
            logger.error(f"Error registering provisional IDs in {artifact_id}: {e}")
            return {
                "success": False,
                "message": f"Error registering provisional IDs: {str(e)}"
            }
    
    def _process_provisional_ids_filtered(self, content: str, type_manager, allowed_types: Optional[List[str]] = None, parent_artifact_id: Optional[str] = None) -> Tuple[Dict[str, str], str, Dict[str, str]]:
        """Process provisional IDs with optional type filtering.
        
        Args:
            content: Document content to process
            type_manager: ArtifactTypeManager instance
            allowed_types: Optional list of artifact types to process (e.g., ['UACC', 'SACC'])
            parent_artifact_id: Optional parent artifact ID for nested artifacts
            
        Returns:
            Tuple of (id_mapping, updated_content, artifact_names)
        """
        # Find all provisional artifact IDs in the content
        provisional_ids = type_manager.find_provisional_artifact_ids(content)
        
        # Filter by allowed types if specified
        if allowed_types:
            filtered_ids = set()
            for provisional_id in provisional_ids:
                try:
                    artifact_type, _temp_id = type_manager.parse_provisional_id(provisional_id)
                    if artifact_type in allowed_types:
                        filtered_ids.add(provisional_id)
                except ValueError:
                    continue  # Skip invalid IDs
            provisional_ids = filtered_ids
        
        if not provisional_ids:
            return {}, content, {}
        
        logger.info(f"Found {len(provisional_ids)} provisional artifact IDs: {provisional_ids}")
        
        id_mapping: Dict[str, str] = {}
        artifact_names: Dict[str, str] = {}
        updated_content = content
        
        for provisional_id in sorted(provisional_ids):  # Sort for consistent processing
            try:
                # Parse the provisional ID to get the artifact type
                artifact_type, _temp_id = type_manager.parse_provisional_id(provisional_id)
                
                # Extract the artifact name from the content
                artifact_name = self._extract_artifact_name(content, provisional_id)
                
                # These are nested artifacts, so is_file=False
                is_file = False
                
                # Generate a new proper artifact ID - nested artifacts get the parent
                new_artifact_id = self.get_artifact_id(artifact_type, artifact_name, is_file=is_file, parent=parent_artifact_id)
                
                # Store the mapping and name
                id_mapping[provisional_id] = new_artifact_id
                if artifact_name:
                    artifact_names[new_artifact_id] = artifact_name
                
                # Replace all occurrences in the content
                # Use word boundaries to avoid partial replacements
                pattern = r'\b' + re.escape(provisional_id) + r'\b'
                updated_content = re.sub(pattern, new_artifact_id, updated_content)
                
                # Also replace step references that use just the provisional number
                # Extract the provisional number from the provisional_id (e.g., "101" from "SACC-PROVISIONAL101")
                provisional_match = re.search(r'PROVISIONAL(\d+)$', provisional_id)
                if provisional_match:
                    provisional_number = provisional_match.group(1)
                    # Extract the new artifact number from the new_artifact_id (e.g., "17" from "SACC-17")
                    new_id_match = re.search(r'-(\d+)$', new_artifact_id)
                    if new_id_match:
                        new_number = new_id_match.group(1)
                        # Replace patterns like "PROVISIONAL101.1" with "17.1"
                        step_pattern = r'\bPROVISIONAL' + re.escape(provisional_number) + r'\.(\d+)'
                        step_replacement = new_number + r'.\1'
                        updated_content = re.sub(step_pattern, step_replacement, updated_content)
                        logger.info(f"Also updated step references: PROVISIONAL{provisional_number}.X -> {new_number}.X")
                
                logger.info(f"Mapped {provisional_id} -> {new_artifact_id}" + (f" ({artifact_name})" if artifact_name else "") + f" [is_file: {is_file}]")
                
            except ValueError as e:
                logger.error(f"Error processing provisional ID {provisional_id}: {e}")
                raise
        
        return id_mapping, updated_content, artifact_names
    
    def _process_test_coverage_updates(self, content: str, id_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Process test coverage updates for newly registered artifacts.
        
        This method processes artifacts that were just assigned real IDs and:
        1. Looks for *Tests*: lines in each newly registered artifact
        2. Extracts REQ artifact IDs from those lines
        3. Updates the corresponding REQ artifacts' COVERING_TESTS managed header
        
        Args:
            content: The updated content containing the newly assigned artifact IDs
            id_mapping: Dictionary mapping provisional IDs to final artifact IDs
            
        Returns:
            Dictionary with test coverage update results
        """
        test_coverage_results = {}
        updated_reqs = []
        errors = []
        
        try:
            # Import header manager locally to avoid circular imports
            from .artifact_header_manager import ArtifactHeaderManager
            header_manager = ArtifactHeaderManager()
            
            # Process each newly assigned artifact ID
            for provisional_id, new_artifact_id in id_mapping.items():
                try:
                    # Extract the artifact section content for this new artifact ID
                    artifact_section = self._extract_artifact_section(content, new_artifact_id)
                    
                    if not artifact_section:
                        logger.info(f"No section found for {new_artifact_id}")
                        continue
                    
                    # Look for *Tests*: line in the artifact section
                    req_ids = self._extract_test_requirements(artifact_section)
                    
                    if not req_ids:
                        logger.info(f"No test requirements found in {new_artifact_id}")
                        continue
                    
                    logger.info(f"Found test requirements in {new_artifact_id}: {req_ids}")
                    
                    # Update each REQ artifact to add this test artifact as covering test
                    for req_id in req_ids:
                        try:
                            self._update_req_with_covering_test(header_manager, req_id, new_artifact_id)
                            updated_reqs.append(req_id)
                            logger.info(f"Updated {req_id} to record coverage by {new_artifact_id}")
                        except Exception as e:
                            error_msg = f"Failed to update {req_id} with covering test {new_artifact_id}: {str(e)}"
                            logger.error(error_msg)
                            errors.append(error_msg)
                
                except Exception as e:
                    error_msg = f"Error processing test coverage for {new_artifact_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Prepare results
            unique_updated_reqs = list(set(updated_reqs))
            test_coverage_results = {
                "updated_reqs": unique_updated_reqs,
                "total_updated": len(unique_updated_reqs),
                "errors": errors if errors else None
            }
            
            if unique_updated_reqs:
                logger.info(f"Test coverage updates completed for {len(unique_updated_reqs)} REQ artifacts")
            
        except Exception as e:
            error_msg = f"Critical error in test coverage processing: {str(e)}"
            logger.error(error_msg)
            test_coverage_results = {
                "error": error_msg
            }
        
        return test_coverage_results
    
    def _extract_artifact_section(self, content: str, artifact_id: str) -> str:
        """Extract the content of a specific artifact section from document content.
        
        Args:
            content: The full document content
            artifact_id: The artifact ID to find (e.g., "UACC-17")
            
        Returns:
            Content of the artifact section, or empty string if not found
        """
        lines = content.split('\n')
        section_lines = []
        in_section = False
        
        for line in lines:
            # Check if this line starts the section we're looking for
            if line.strip().startswith(f'### {artifact_id}:'):
                in_section = True
                section_lines.append(line)
                continue
            
            # Check if this line starts a different section (end of our section)
            if in_section and line.strip().startswith('### ') and not line.strip().startswith(f'### {artifact_id}:'):
                break
            
            # Add lines to our section if we're currently in it
            if in_section:
                section_lines.append(line)
        
        return '\n'.join(section_lines)
    
    def _extract_test_requirements(self, artifact_content: str) -> List[str]:
        """Extract REQ artifact IDs from an artifact's *Tests*: line.
        
        Args:
            artifact_content: Content of the artifact section
            
        Returns:
            List of REQ artifact IDs found in *Tests*: line
        """
        req_ids = []
        lines = artifact_content.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            # Look for *Tests*: line
            if line_stripped.startswith('*Tests*:'):
                # Extract REQ IDs from the line
                tests_text = line_stripped[len('*Tests*:'):].strip()
                if tests_text:
                    # Split by comma and extract REQ artifact IDs
                    potential_ids = [item.strip() for item in tests_text.split(',')]
                    for item in potential_ids:
                        # Check if it looks like a REQ artifact ID
                        if re.match(r'^REQ-\d+$', item):
                            req_ids.append(item)
                break
        
        return req_ids
    
    def _update_req_with_covering_test(self, header_manager: Any, req_id: str, test_artifact_id: str) -> None:
        """Update a REQ artifact to add a covering test reference.
        
        Args:
            header_manager: ArtifactHeaderManager instance
            req_id: REQ artifact ID to update (e.g., "REQ-8")
            test_artifact_id: Test artifact ID to add as covering test (e.g., "UACC-17")
        """
        # Get the REQ artifact content
        req_result = self.get_artifact(req_id)
        if not req_result.get("success"):
            raise ValueError(f"Failed to retrieve {req_id}: {req_result.get('message')}")
        
        req_content = req_result["content"]
        
        # Parse current REQ headers using header manager
        req_header_line, req_headers, req_body = header_manager.parse_managed_headers(req_content)
        current_covering_tests_str = req_headers.get('COVERING_TESTS', '')
        
        # Parse current covering tests from comma-separated string
        if current_covering_tests_str.strip():
            current_covering_tests = [test.strip() for test in current_covering_tests_str.split(',')]
        else:
            current_covering_tests = []
        
        # Add test artifact reference if not already present
        if test_artifact_id not in current_covering_tests:
            current_covering_tests.append(test_artifact_id)
            current_covering_tests.sort()  # Sort for consistency
            
            # Update REQ using header manager
            updated_req_headers = req_headers.copy()
            updated_req_headers['COVERING_TESTS'] = ','.join(current_covering_tests)
            
            # Get REQ artifact type for header ordering
            req_type_info = header_manager.extract_artifact_type_and_id(req_content)
            if req_type_info:
                req_type, _ = req_type_info
                applicable_headers = header_manager.get_managed_headers_for_type(req_type)
                
                # Rebuild REQ content with updated covering tests
                result_lines = [req_header_line]
                
                # Add managed headers in consistent order
                for item_key, item_config in applicable_headers.items():
                    if item_key in updated_req_headers:
                        label = item_config['label']
                        value = updated_req_headers[item_key]
                        result_lines.append(f"`{label.rstrip(':')}`: {value}")
                
                # Add body content
                if req_body.strip():
                    result_lines.append(req_body)
                
                updated_req_content = '\n'.join(result_lines)
                
                # Save the updated REQ content
                update_result = self.update_artifact(req_id, updated_req_content)
                if not update_result.get("success"):
                    raise ValueError(f"Failed to update {req_id} content: {update_result.get('message')}")
                
                logger.info(f"Updated {req_id} covering tests: {','.join(current_covering_tests)}")
    
    def finalize_provisional_file(self, provisional_file_name: str, file_name_suffix: Optional[str] = None) -> Dict[str, Any]:
        """Finalize a provisional document by finding it in the provisional store, assigning proper artifact IDs, and saving to the document repository.
        
        This method:
        1. Finds the provisional file by name in the RESPECT_PROVISIONAL_DOC_STORE
        2. Finds all provisional artifact IDs in the document content (e.g., PRD-PROVISIONAL1, REQ-PROVISIONAL2)
        3. Extracts artifact names from content patterns like "PRD-PROVISIONAL1: Character Creation PRD"
        4. Generates new proper sequential artifact IDs for each provisional ID found
        5. Updates the repository's artifact ID index with the new IDs and names in format: ID,ARTIFACT_ID,NAME
        6. Replaces all provisional IDs in the document content with the new assigned IDs
        7. If the filename itself contains a provisional ID that was converted, automatically renames 
           the file to match the new ID (e.g., "PRD-PROVISIONAL1.md" becomes "PRD-37.md")
        8. Saves the finalized document to RESPECT_DOC_REPO_ROOT/
        9. Deletes the provisional file after successful processing
        10. If file_name_suffix is provided (<= 50 chars), append it (lowercased, underscore-delimited) to the resulting filename
        
        Args:
            provisional_file_name: Name of the provisional document file to process (e.g., "PRD-PROVISIONAL1.md")
            file_name_suffix: Optional suffix to append to the resulting filename. The suffix will be
                converted to lowercase and non-alphanumeric characters will be replaced with underscores.
            
        Returns:
            Dictionary with finalization results including source path, target path, and ID mappings
            
        Raises:
            FileNotFoundError: If the provisional file doesn't exist
            ValueError: If artifact types are invalid or environment variables not set
            OSError: If file operations fail
        """
        # Get environment variables
        provisional_store = os.getenv("RESPECT_PROVISIONAL_DOC_STORE")
        if not provisional_store:
            raise ValueError("RESPECT_PROVISIONAL_DOC_STORE environment variable not set")
        
        doc_repo_root = os.getenv("RESPECT_DOC_REPO_ROOT")  
        if not doc_repo_root:
            raise ValueError("RESPECT_DOC_REPO_ROOT environment variable not set")

        # Find the provisional file
        provisional_file_path = self._find_provisional_file(provisional_file_name, provisional_store)

        # Read the provisional file content
        content = provisional_file_path.read_text(encoding='utf-8')

        # Get the artifact type manager
        type_manager = get_artifact_type_manager()

        # Process all provisional IDs in the content
        id_mapping, updated_content, artifact_names = self._process_provisional_ids(content, type_manager)

        if not id_mapping:
            logger.info(f"No provisional artifact IDs found in {provisional_file_name}")
            return {
                "target": None,
                "id_mappings": {},
                "message": "No provisional artifact IDs found"
            }

        # Generate the target filename
        target_filename = self._generate_target_filename(provisional_file_path, id_mapping, file_name_suffix)

        # Ensure the target directory exists (save to repo root)
        doc_repo_path = Path(doc_repo_root)
        doc_repo_path.mkdir(parents=True, exist_ok=True)

        # Write the finalized file to the document repository root
        target_file_path = doc_repo_path / target_filename
        # Add version footer to finalized content
        final_content = updated_content.rstrip() + self.get_version_footer()
        target_file_path.write_text(final_content, encoding='utf-8')

        # Delete the provisional file after successful processing
        provisional_file_path.unlink()

        # Handle post-finalization activities for specific artifact types
        type_manager = get_artifact_type_manager()
        filename_validation = type_manager.validate_provisional_filename(provisional_file_path.name)

        import json
        validation_result = json.loads(filename_validation)
        
        main_artifact_id = None
        if validation_result.get("valid") and validation_result.get("artifact_type"):
            main_artifact_type = validation_result["artifact_type"]
            # Find the main artifact ID from id_mapping (matches main artifact type)
            for provisional_id, final_id in id_mapping.items():
                if isinstance(final_id, str) and final_id.startswith(f"{main_artifact_type}-"):
                    main_artifact_id = final_id
                    break
            if main_artifact_id:
                # Import here to avoid circular dependency
                from .artifact_type_handler import handle_artifact_finalization
                handler_result = handle_artifact_finalization(main_artifact_type, main_artifact_id, id_mapping)
            else:
                logger.warning(f"Could not find main artifact ID for type {main_artifact_type} in id_mapping: {id_mapping}")
                handler_result = None
        else:
            handler_result = None

        logger.info(f"Successfully finalized provisional document: {provisional_file_name}")
        logger.info(f"Source: {provisional_file_path.name} (deleted)")
        logger.info(f"Target: {target_filename}")
        logger.info(f"ID mappings: {id_mapping}")
        if artifact_names:
            logger.info(f"Artifact names: {artifact_names}")

        result = {                
            "source_filename": provisional_file_path.name,
            "target": main_artifact_id,
            "id_mappings": id_mapping,
            "message": "Successfully finalized provisional document"
        }
        
        # Add handler result if available
        if handler_result:
            result["handler_result"] = handler_result

        return result
    
    def update_artifact_status(self, identifier: str, status: str) -> Dict[str, Any]:
        """Update the status of an artifact in the repository.
        
        This method:
        1. Finds the artifact by ID (numeric or full like PRD-1)
        2. Validates the status against allowed statuses
        3. Uses artifact type handlers for type-specific status update logic
        4. Updates the index.md file with the new status
        
        Args:
            identifier: Either a document ID (integer) or artifact ID (e.g., PRD-1)
            status: The new status to set
            
        Returns:
            Dictionary with update results and any errors
            
        Raises:
            ValueError: If identifier or status is invalid
            FileNotFoundError: If artifact files are not found
        """
        from .artifact_type_manager import get_artifact_type_manager
        from .artifact_type_handler import handle_artifact_status_update
        
        # Get type manager for validation
        type_manager = get_artifact_type_manager()
        
        # Find the artifact ID from the identifier first
        artifact_id = self._resolve_artifact_id(identifier)
        if not artifact_id:
            return {
                "success": False,
                "error": f"No artifact found for identifier: {identifier}"
            }
        
        # Get the artifact type for type-specific validation
        artifact_type = type_manager.get_artifact_type_from_id(artifact_id)
        
        # Validate status against type-specific valid statuses
        try:
            normalized_status = type_manager.validate_and_normalize_status_for_type(status, artifact_type)
        except ValueError as e:
            # Return type-specific valid statuses in the error
            valid_statuses = type_manager.get_valid_statuses_for_type(artifact_type)
            return {
                "success": False,
                "error": str(e),
                "valid_statuses": valid_statuses,
                "artifact_type": artifact_type
            }
        
        results = {
            "success": True,
            "artifact_id": artifact_id,
            "status": normalized_status,
            "updates": []
        }
        
        # Use artifact type handlers for status updates (they handle both index and content)
        try:
            handler_result = handle_artifact_status_update(artifact_id, normalized_status, self)
            if handler_result is None:
                # Fallback: no handler for this type → update index and header content
                index_manager = get_artifact_index_manager(str(self.repo_root))
                ok = index_manager.update_artifact(artifact_id, status=normalized_status)
                if not ok:
                    results["success"] = False
                    results["error"] = f"Artifact {artifact_id} not found in index"
                else:
                    results["updates"].append(
                        f"Updated {artifact_id} status to {normalized_status} in index (no handler for type)"
                    )
                    # Update header content with STATUS via ArtifactHeaderManager
                    try:
                        artifact_info = index_manager.get_artifact_by_id(artifact_id)
                        artifact_result = self.get_artifact(artifact_id)
                        if artifact_result.get("success"):
                            content = artifact_result["content"]
                            header_mgr = ArtifactHeaderManager()
                            updated_content = header_mgr.update_managed_header(content, {"STATUS": normalized_status})
                            # Write back based on is_file
                            is_file_flag = bool(artifact_info and artifact_info.get("is_file", False))
                            if is_file_flag and artifact_info is not None:
                                file_update = self._update_file_artifact(artifact_id, artifact_info, updated_content)
                            else:
                                file_update = self._update_non_file_artifact(artifact_id, updated_content)
                            if file_update.get("success"):
                                results["updates"].append("Updated STATUS in artifact content")
                            else:
                                results["updates"].append(f"Warning: Failed to update content header: {file_update.get('message')}")
                        else:
                            results["updates"].append(f"Warning: Could not load artifact content: {artifact_result.get('message')}")
                    except Exception as ie:
                        results["updates"].append(f"Warning: Header update failed: {ie}")
            else:
                # Handler returned a dict with success/message
                msg = handler_result.get("message", f"Updated {artifact_id} to {normalized_status}")
                results["updates"].append(msg)
                if not handler_result.get("success", True):
                    results["success"] = False
                    results["error"] = msg
        except Exception as e:
            results["updates"].append(f"Failed to update artifact: {str(e)}")
            results["success"] = False
            results["error"] = str(e)
        
        logger.info(f"Updated status for {artifact_id} to {normalized_status}")
        return results
    
    def _resolve_artifact_id(self, identifier: str) -> Optional[str]:
        """Resolve an identifier to a full artifact ID.
        
        Args:
            identifier: Either a document ID (integer) or artifact ID
            
        Returns:
            Full artifact ID or None if not found
        """
        return self.resolve_artifact_identifier(identifier)

    # Note: artifact type extraction/validation now lives in ArtifactTypeManager


def get_artifact_id_manager(repo_root: Optional[str] = None) -> ArtifactManager:
    """Factory function to create an ArtifactManager instance.
    
    Args:
        repo_root: Path to the ReSpecT repository root. If None, uses RESPECT_DOC_REPO_ROOT env var.
        
    Returns:
        An ArtifactManager instance
        
    Raises:
        ValueError: If repo_root is not provided and RESPECT_DOC_REPO_ROOT env var is not set
    """
    if repo_root is None:
        repo_root = os.getenv('RESPECT_DOC_REPO_ROOT')
        if not repo_root:
            raise ValueError("repo_root must be provided or RESPECT_DOC_REPO_ROOT environment variable must be set")
    
    return ArtifactManager(repo_root)
