# ReSpecT MCP Server

Requirements, Specifications, and Task Management for AI-assisted software development.

ReSpecT is an MCP server that equips a coding agent with a structured toolkit to manage the software development lifecycle for moderate-size projects. It focuses on:

- Requirements gathering and documentation (PRD, REQ, ADR)
- Task planning and execution tracking (TASKPRD, TASK with steps)
- Acceptance testing workflow (UACC, SACC)
- Architecture documentation and review (ASD, Architecture Review PRDs)

This README summarizes what the server provides, how to run it, the tools it exposes, and the end-to-end workflows (“modes”) it enables.


## Why ReSpecT

Modern AI coding agents are great at writing code, but less consistent at managing artifacts and state across a project. ReSpecT MCP is a proof-of-prinicple project that provides MCP tooling to support:

- Markdown document-based artifact store - source controlled document source of truth.
- PRD creation, Task generation, Acceptance test generation, architectural review.
- Manage process and state throughout phases.
- Track artifact IDs and statuses across related files
- Link related artifacts (parent/child, references), real-time updating of related requirements, implementation tasks, and acceptance testings.
- Task Management and real-time task step status updates
- Drive well-defined phases from ideation through testing and completion


## Repository Layout (high level)

- `respect_mcp/respect_mcp_server/` — FastMCP server (tools are defined in `server.py`)
- `respect_mcp/respect_manager/` — Artifact managers and type/status configuration
- `respect_mcp/instructions/` — Mode instructions that orchestrate end-to-end flows
- `respect_mcp/templates/` — Markdown templates for artifacts (ASD, PRD, TASKPRD, SACC, UACC)


## Environment and Setup

Prerequisites
- Python 3.11+
- uv (used by the setup script to create the venv and install deps): https://docs.astral.sh/uv/getting-started/installation/

### Target project workspace
Agent invocation (/respect)
- Copy agent instructions in `AGENTS.md` to your base agent instructions file.

Prepare project folders (target project)
- Create two folders in your target project:
	1) A source-controlled ReSpecT document repository (RESPECT_DOC_REPO_ROOT)
	2) A transient/provisional folder for drafts (RESPECT_PROVISIONAL_DOC_STORE)
- Keep the provisional folder out of version control (e.g., add to .gitignore). The document repository should be tracked in your VCS.

### Codex CLI/IDE (No MCP support for cloud)

Codex CLI integration
- Use `codex-config-example.toml` in the repo root as a starting point and copy it to your global Codex config (e.g., `~/.codex/config.toml`). As of 2025‑09‑17, project-level config may not be supported.
- Update the `command` path to point to your cloned script at `respect_mcp/setup-respect-mcp.sh` and set appropriate args:

```toml
[mcp_servers.respect_manager]
command = "/absolute/path/to/your/clone/respect_mcp/setup-respect-mcp.sh"
args = [
	"/absolute/path/to/your/project/respect_docs",
	"/absolute/path/to/your/project/respect_provisional",
	"false" # set to "true" for debug
]
```

## Typical Flows (at a glance)

ReSpecT instruction following will be triggered with `/respect` slash command followed by an optional mode intention (does not have to be exact) and any other descriptive text desired for the current request.  Tech ical guidance documentation is highly suggested to augment coding agent work.  If provided, these documents need to be referenced explicitly in the request; ReSpecT will not instruct the agent to seek out supplementary guidance documentation during PRD development.

- `/respect` — Detects current project state and proposes the next mode/phase to run.
- `/respect Generate PRD <short description>` — Start PRD creation from templates and inputs you provide.
- `/respect Generate TASKPRD <context or PRD id>` — Plan implementation tasks from the active PRD.
- `/respect Task Implementation <notes>` — Continue or start executing the next applicable task.
- `/respect Setup PRD Tests <context>` — Add UACC/SACC to a PRD ready for testing and set it to TESTING.
- `/respect Acceptance Test <which tests or PRD id>` — Run SACC and guide UACC; update statuses accordingly.
- `/respect PRD Review and Completion <notes>` — Summarize statuses and, if appropriate, complete the PRD.
- `/respect Architecture Summary <scope>` — Produce/update an ASD summarizing the current architecture.
- `/respect Architecture Review <scope>` — Analyze the codebase and produce a refactoring-focused PRD.

New feature.
1) Generate PRD → finalize → set PRD ACTIVE
2) Generate TASKPRD → set ACTIVE → Task Implementation until all tasks COMPLETED
3) Setup PRD Tests → add UACC/SACC → set PRD TESTING
4) Acceptance Test → mark tests PASSED/FAILED, update REQ statuses
5) PRD Review and Completion → resolve leftovers → mark PRD COMPLETED

Architecture initiative
1) Architecture Review → PRD for refactoring (ACTIVE)
2) Generate TASKPRD and implement → Setup PRD Tests (if applicable) → Review and Complete



## Artifact Model (concepts)

Common artifact types
- PRD — Product Requirements Document (parent container for REQ/ADR and references to TASKPRD and tests)
- REQ — Individual requirement (referenced by tasks and tests)
- ADR — Architecture Decision Record
- TASKPRD — Implementation plan that expands REQ into concrete TASKs
- TASK — Executable task with step checkboxes; status evolves from NEW → ACTIVE → COMPLETED
- ASD — Architecture Summary Document
- UACC / SACC — User/System acceptance tests

Statuses (typical)
- NEW, APPROVED, ACTIVE, TESTING, PASSED, FAILED, COMPLETED, CANCELLED, REPLACED

## Modes and End-to-End Workflows

The server ships with detailed instructions for orchestrating full phases. A supervising agent typically calls `get_mode_instructions(<Mode Name>)` and follows the returned steps.

Available modes (instruction files live in `respect_mcp/instructions/`):

- Detect Project State — Determine the current working PRD and the appropriate next mode based on repository state
- Generate PRD — Create a new PRD from templates and prior artifacts; finalize and set ACTIVE
- Generate TASKPRD — Expand an ACTIVE PRD into a TASKPRD with parent tasks and relevant files; set ACTIVE
- Failed Tests TASKPRD — Create a follow-up TASKPRD to address FAILED UACC/SACC cases from a TESTING PRD
- Task Implementation — Pick next TASK, add/execute steps, mark steps done, advance statuses; complete TASKPRD
- Setup PRD Tests — For an ACTIVE PRD with a COMPLETED TASKPRD, add UACC/SACC under Acceptance Tests and register provisional IDs; set PRD to TESTING
- Acceptance Test — Execute SACC (system) and guide UACC (user) tests; update test and REQ statuses based on outcomes
- PRD Review and Completion — Summarize nested artifacts, resolve ambiguous statuses, and mark the PRD COMPLETED (and ADRs ACTIVE)
- Architecture Summary — Produce or refresh the ASD and reconcile ACTIVE ADRs (set REPLACED as needed)
- Architecture Review — Generate a refactoring-focused PRD after analyzing the codebase and ASD

There is also a “ReSpecT Master” instruction set that helps an agent route to the correct mode, including a `FULL AUTO` path that chains modes automatically.

## Support and Contributions
This project was developed rapidly as a proof-of-prinicple and the python implementation leaned on LLM generation heavily.  It's messy.  If this concept proves worthwile, I'd consider a rewrite.
## Reference
### Templates

Document templates live under `respect_mcp/templates/` and are retrieved by the tooling:
- `ASD/template.md`
- `PRD/template.md`
- `TASKPRD/template.md`
- `UACC/template.md`
- `SACC/template.md`

Always adhere to template structure (notably `###` headings and `*<Section>*:` labels). Downstream tools parse and update documents based on these conventions.

### Reference Tools (MCP API)
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