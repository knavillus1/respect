# Agent Instructions: Creating a New PRD Document
You have entered the `Generate PRD` mode.  Upon reading this your responsability is to follow the directions in the instructions below.

## Goal
To guide an AI assistant in creating a detailed Product Requirements Document (PRD) in Markdown format, based on an initial user prompt. The PRD should be clear, actionable, and suitable for a junior developer to understand and implement the feature.

## Workspace Scope
Do not search directories or read files outside of the project root provided by the user (with exception of file referenced directly by the user).  If no project root is provided, clarify before moving on. Do not include include any project management files in the Reference Files section from the ReSpecT document root, with exception of specific guidance files referenced by the user.

## Process

### MCP Server
- Ensure the `ReSpecT MCP` server is available and tools are enabled:
`get_provisional_store`
`get_document_template`
`finalize_provisional_file`

### Get Document Repository Root 
- Use `get_provisional_store` tool to verify environment setup and get the repository root path
```
Tool: get_provisional_store
Parameters:
  None
```
- The value of the document root will be referenced from now on as `PROVISIONAL_STORE`


### Receive Initial Prompt
- The user may provide a description or provide files for background and guidance. If so then read them and treat the content as additional input for the feature request. If the the user provides a specific code root or pacakge to focus on store this in `PROJECT_ROOT`

### View Active ASD
- Use the `search_artifacts_by_type` tool to obtain the closed PRD artifact ids:

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "ASD",
  status: "ACTIVE"
```
- If an ASD exists fetch it:
```
Tool: get_artifact
Parameters:
  identifier: "<asd_artifact_id>"
```

### View Completed PRDs
- Use the `search_artifacts_by_type` tool to obtain the closed PRD artifact ids:

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "PRD",
  status: "COMPLETED"
```
- If there are completed PRD artifacts in the document store, retrieve them for analysis with the `get_artifact` tool to obtain the full text for each:

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
- The template provided by the tool will serve as your guidepost for the output format of the PRD you create in the steps below.
- Adhere to the template strictly, particularly using ### header markdown and using `*<section>*:' for section labels.  Downstream management of this artifact depends on this.


### Generate initial tree view of current project** 
- generate a tree view of the project at `PROJECT_ROOT` or the workspace root if not specified, ommitting verbose directories.  This view is for your own conisderation of PRD output.
### Ask Clarifying Questions:
- If the `FULL AUTO` latch is enabled, skip clarifying questions and proceed to the next step.
- Before writing the PRD, ask clarifying questions of the user to gather sufficient detail. The goal is to understand the "what" and "why" of the feature, not necessarily the  detailed "how" (which the developer will figure out). Large scale architecture decisions will be made in the PRD so include questions that can help guide these choices. See `Clarifying Questions (Examples)` Below for guidance.
### Show all reference docs and confirm commencement of PRD creation
- Output a list of all guidance documents that you will include in the PRD output and ask the user to confirm to move on to next step with `ok`
### Generate PRD:
- Based on the initial prompt and the user's answers to the clarifying questions, generate a PRD using the structure provided by the template obtained by the mcp tool.  Do vary from the template, as automated processing of the PRD document relies on consisten format and structure.
- For nested artifacts ADR and REQ, each should be given a unique PROVISIONAL<id>, ALL <id>s should be distinct on the resulting document, even between different artifact types!
- Architecture Decision Records (ADR) should be labled with`ADR-PROVISIONAL<id>`
- Requirements should be labeled with `REQ-PROVISIONAL<id>`
- You may observe acceptance test artifacts in COMPLETED PRDs.  UACC and SACC acceptance tests are added once a PRD implementation is complete so do not add these test artifacts at this time!
- Save the generated document as `PRD-PROVISIONAL1.md` inside the `PROVISIONAL_STORE/` directory.
### Ask the user for review
- If the `FULL AUTO` latch is enabled, do not ask for review.  Skip review and finalize the PRD
- Ask the user to review the provisional PRD to ensure the requirements are satisfied.  Update and Edit as necessary, ask user `To finalize this PRD enter ok` to continue with finalize step.
### Finalize the PRD
- Use the `finalize_provisional_file` tool to convert provisional IDs to final IDs.  This will remove the provisional PRD and enter into the ReSpecT system.  Enter an informative name for the file_name_suffix so that backend users can understand the nature of the artifact by name.

```
Tool: finalize_provisional_file
Parameters:
  provisional_file_path: "PRD-PROVISIONAL1.md"
  file_nane_suffix: "optional_suffix_here"  # up to 50 chars, will be lowercased and underscore-delimited
```
This will convert all provisional ids to confirmed ids that are tracked by the ReSpecT system.  The tool will return the updated artifact id for the newly entered PRD. This artifact id will be referred to as `NEW_PRD_ID`

- Update the status to ACTIVE using the `update_artifact_status` tool:
```
Tool: update_artifact_status
Parameters:
  artifact_id: "NEW_PRD_ID"
  status: "ACTIVE"
```

### Generate PRD mode completion
- If the `FULL AUTO` latch is enabled, conclude `Generate PRD` mode by moving on to `Generate TASKPRD` mode.  Use tool get_mode_instructions with mode: "Generate PRD"
- Otherwise, report back to the user that the PRD generation is complete and simply ask what to do next with a simple suggestion that `Generate TASKPRD` mode typically follows.

## APPENDIX 1: Clarifying Questions (Examples)

The AI should adapt its questions based on the prompt, but here are some common areas to explore:

*   **Problem/Goal:** "What problem does this feature solve for the user?" or "What is the main goal we want to achieve with this feature?"
*   **Target User:** "Who is the primary user of this feature?"
*   **Core Functionality:** "Can you describe the key actions a user should be able to perform with this feature?"
*   **User Stories:** "Could you provide a few user stories? (e.g., As a [type of user], I want to [perform an action] so that [benefit].)"
*   **Acceptance Criteria:** "How will we know when this feature is successfully implemented? What are the key success criteria?"
*   **Scope/Boundaries:** "Are there any specific things this feature *should not* do (non-goals)?"
*   **Data Requirements:** "What kind of data does this feature need to display or manipulate?"
*   **Design/UI:** "Are there any existing design mockups or UI guidelines to follow?" or "Can you describe the desired look and feel?"
*   **Edge Cases:** "Are there any potential edge cases or error conditions we should consider?"

