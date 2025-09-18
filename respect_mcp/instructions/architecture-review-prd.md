# Architecture Review mode instructions
You have entered the `Architecture Review` mode. Upon reading this your responsibility is to follow the directions in the instructions below.

## Goal
To guide an AI assistant in conducting a comprehensive architecture review of an existing codebase and creating a detailed Product Requirements Document (PRD) focused on refactoring targets. The PRD should identify opportunities for simplifying architecture, improving robustness, deduplicating code, and removing unused components. The output should be clear, actionable, and suitable for a developer to understand and implement the refactoring improvements.

## Workspace Scope
Do not search directories or read files outside of the project root provided by the user (with exception of files referenced directly by the user). If no project root is provided, clarify before moving on. Do not include any project management files in the Reference Files section from the ReSpecT document root, with exception of the current ASD artifact if available.

## Process

### MCP Server
- Ensure the `ReSpecT MCP` server is available and tools are enabled:
`get_provisional_store`
`get_document_template`
`finalize_provisional_file`
`search_artifacts_by_type`
`get_artifact`
`update_artifact_status`

### Get Document Repository Root 
- Use `get_provisional_store` tool to verify environment setup and get the repository root path
```
Tool: get_provisional_store
Parameters:
  None
```
- The value of the document root will be referenced from now on as `PROVISIONAL_STORE`

### Receive Initial Prompt
- The user may provide a description of specific architectural concerns or provide files for background and guidance. If so then read them and treat the content as additional input for the architecture review. If the user provides a specific code root or package to focus on store this in `PROJECT_ROOT`

### View Active ASD
- Use the `search_artifacts_by_type` tool to obtain the active ASD artifact:

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "ASD",
  status: "ACTIVE"
```
- If an ASD exists fetch it for comprehensive understanding of current architecture:
```
Tool: get_artifact
Parameters:
  identifier: "<asd_artifact_id>"
```

### View Existing Architecture PRDs
- Use the `search_artifacts_by_type` tool to obtain existing architecture-focused PRD artifact ids:

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "PRD",
  status: "COMPLETED"
```
- If there are completed PRD artifacts in the document store that relate to architecture, retrieve them for analysis with the `get_artifact` tool to avoid duplication and understand previous architectural decisions:

```
Tool: get_artifact
Parameters:
  identifier: "<artifact_id>"
```

### Retrieve the PRD Template
- Use the `get_document_template` tool to obtain the PRD template:

```
Tool: get_document_template
Parameters:
  artifact_type: "PRD"
```
- The template provided by the tool will serve as your guidepost for the output format of the architecture refactoring PRD you create in the steps below.
- Adhere to the template strictly, particularly using ### header markdown and using `*<section>*:' for section labels. Downstream management of this artifact depends on this.

### Conduct Comprehensive Code Analysis
- Generate a detailed tree view of the project at `PROJECT_ROOT` or the workspace root if not specified, including all significant directories and files
- Analyze the codebase structure using VS Code's built-in tools and workspace search capabilities:
  - Identify duplicate code patterns across files
  - Look for unused imports, functions, classes, and modules
  - Examine dependency relationships and circular dependencies
  - Assess architectural patterns and consistency
  - Review configuration and setup files for redundancy
  - Identify overly complex components that could be simplified
  - Look for violations of separation of concerns
  - Assess test coverage gaps and testing architecture

### Architecture Assessment
- Compare the current codebase structure against the ASD to identify:
  - Deviations from documented architecture
  - Components that have grown beyond their intended scope
  - Missing architectural boundaries
  - Opportunities for modularization
  - Performance bottlenecks in the architecture
  - Security architectural concerns
  - Maintainability issues

### Ask Clarifying Questions (if needed)
- If the `FULL AUTO` latch is enabled, skip clarifying questions and proceed to the next step.
- Before writing the architecture review PRD, ask clarifying questions to understand:
  - Specific pain points developers have experienced
  - Performance requirements and constraints
  - Deployment and operational considerations
  - Timeline and priority for refactoring efforts
  - Risk tolerance for architectural changes
  - See `Architecture Review Questions (Examples)` below for guidance.

### Show all reference docs and confirm commencement of PRD creation
- Output a list of all guidance documents and code analysis findings that you will include in the architecture review PRD and ask the user to confirm to move on to next step with `ok`

### Generate Architecture Review PRD
- Based on the code analysis, ASD review, and any user input, generate a PRD using the structure provided by the template obtained by the mcp tool. Focus specifically on:
  - **Refactoring Requirements**: Specific code simplification targets
  - **Deduplication Requirements**: Identification and consolidation of duplicate code
  - **Cleanup Requirements**: Removal of unused code and dependencies  
  - **Architecture Improvements**: Structural changes to improve robustness
  - **Modularity Enhancements**: Better separation of concerns
  - **Performance Optimizations**: Architecture-level performance improvements
  - **Technical Debt Reduction**: Prioritized list of technical debt items

- For nested artifacts ADR and REQ, each should be given a unique PROVISIONAL<id>, ALL <id>s should be distinct on the resulting document, even between different artifact types!
- Architecture Decision Records (ADR) should be labeled with `ADR-PROVISIONAL<id>` and focus on:
  - Consolidation strategies
  - Modularization approaches
  - Code organization improvements
  - Performance architectural decisions
- Requirements should be labeled with `REQ-PROVISIONAL<id>` and focus on:
  - Specific refactoring tasks
  - Code cleanup objectives
  - Architecture improvement goals
  - Testing and validation requirements

- Save the generated document as `PRD-PROVISIONAL1.md` inside the `PROVISIONAL_STORE/` directory.

### Ask the user for review
- If the `FULL AUTO` latch is enabled, do not ask for review. Skip review and finalize the PRD
- Ask the user to review the provisional architecture review PRD to ensure the refactoring requirements are comprehensive and prioritized appropriately. Update and edit as necessary, ask user `To finalize this PRD enter ok` to continue with finalize step.

### Finalize the Architecture Review PRD
- Use the `finalize_provisional_file` tool to convert provisional IDs to final IDs. This will remove the provisional PRD and enter into the ReSpecT system. Enter an informative name for the file_name_suffix that indicates this is an architecture review:

```
Tool: finalize_provisional_file
Parameters:
  provisional_file_path: "PRD-PROVISIONAL1.md"
  file_name_suffix: "architecture_review"  # up to 50 chars, will be lowercased and underscore-delimited
```
This will convert all provisional ids to confirmed ids that are tracked by the ReSpecT system. The tool will return the updated artifact id for the newly entered architecture review PRD. This artifact id will be referred to as `NEW_PRD_ID`

- Update the status to ACTIVE using the `update_artifact_status` tool:
```
Tool: update_artifact_status
Parameters:
  artifact_id: "NEW_PRD_ID"
  status: "ACTIVE"
```

### Architecture Review mode completion
- If the `FULL AUTO` latch is enabled, conclude `Architecture Review` mode by moving on to `Generate TASKPRD` mode. Use tool get_mode_instructions with mode: "Generate TASKPRD"
- Otherwise, report back to the user that the architecture review is complete and ask what to do next with a suggestion that `Generate TASKPRD` mode typically follows for implementation planning.

## APPENDIX 1: Architecture Review Questions (Examples)

The AI should adapt its questions based on the codebase analysis, but here are some common areas to explore:

* **Pain Points:** "What are the main development pain points you've experienced with the current architecture?"
* **Performance Issues:** "Are there any known performance bottlenecks or areas where the system is slower than desired?"
* **Maintenance Concerns:** "Which parts of the codebase are most difficult to maintain or modify?"
* **Testing Challenges:** "Are there areas of the code that are particularly difficult to test?"
* **Deployment Issues:** "Are there any deployment or operational challenges with the current architecture?"
* **Team Velocity:** "Which architectural aspects slow down development or create frequent bugs?"
* **Priority Areas:** "If you had to pick the top 3 areas for architectural improvement, what would they be?"
* **Risk Tolerance:** "How aggressive can we be with refactoring? Are there areas that must remain stable?"
* **Timeline Constraints:** "Are there any upcoming deadlines that should influence the refactoring timeline?"
* **Dependencies:** "Are there external dependencies or integrations that constrain architectural changes?"
* **Scalability:** "Are there anticipated growth areas that the architecture should better support?"