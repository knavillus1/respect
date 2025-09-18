# Reference Tools (MCP API)
ReSpecT MCP is instruction driven and actions are supported by the tools listed below.
These tools are exposed by `respect_mcp_server/server.py` via FastMCP. Parameters and behaviors below are summarized from the implementation.

- get_provisional_store()
	- Returns the `RESPECT_PROVISIONAL_DOC_STORE` path

- get_document_template(artifact_type)
	- Returns the Markdown template for a given artifact type (e.g., `PRD`, `TASKPRD`, `ASD`, `UACC`, `SACC`)

- get_mode_instructions(mode)
	- Returns the instruction text for a named mode (see Modes section)

- get_valid_artifact_types()
	- Returns a readable list of all known artifact types with description and template names

- search_artifacts_by_id(identifier, search_references="true")
	- Identifier can be a document id (digits) or artifact id (e.g., `PRD-1`)
	- Returns JSON summarizing direct matches and (optionally) artifacts that reference it

- search_artifacts_by_type(artifact_type, status="", parent="")
	- Find artifacts by one or more types (comma separated), optionally filter by status and/or parent id
	- Returns JSON list plus summary counts

- get_artifact(identifier)
	- Returns the full content of a file artifact or the specific section for embedded artifacts using the `### <ARTIFACT-ID>` convention

- update_artifact_status(artifact_id, status)
	- Validates id and status; updates the index, the artifact file header, and references; handles TASK-specific cascading updates

- update_artifact_content(identifier, content)
	- Updates the full content of a file artifact, or replaces just the section for embedded artifacts (respects type capabilities)

- finalize_prov_file(provisional_file_name, file_name_suffix=None)
	- Converts provisional IDs to final IDs, writes to repository, deletes provisional file, and reports mappings and handler actions

- mark_artifact_step_done(artifact_id, step_number)
	- For TASK artifacts that support steps, toggles a checkbox step from `[ ]` to `[x]` (e.g., `12.1`)

- add_artifact(parent_artifact_id, new_artifact_type, new_artifact_content)
	- Adds a nested artifact under a parent (currently PRD supports adding UACC/SACC under `## Acceptance Tests`)

- add_reference(target_artifact_id, ref_artifact_id)
	- Adds a “Referenced by” entry to the target artifact indicating the referrer

- register_provisional_ids(artifact_id, allowed_types="UACC,SACC")
	- Scans an existing artifact for nested provisional IDs and assigns confirmed IDs in-place; updates coverage where applicable