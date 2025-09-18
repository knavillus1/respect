
# Agent Instructions - Generate tasks from a prd file
You have entered the `Generate TASKPRD` mode.  Upon reading this your responsability is to follow the directions in the instructions below.

## Goal
- To guide an AI assistant in creating a detailed, step-by-step task list in Markdown format based on an existing Product Requirements Document (PRD). The task list should guide a developer through implementation.

## Workspace Scope
- Do not search directories or read files outside of the Workspace Scope specified in the PRD (with exception of files referenced in the *Reference Files* section).  
- Do not include include any project management files in the Relevant Files section from the ReSpecT document root, with exception of specific guidance files referenced by the PRD.

## Process

### MCP Server
- Ensure the `ReSpecT MCP` server is available and tools are enabled:
`get_document_repo_root`
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

### Obrtain active PRD:
- Use the `search_artifacts_by_type` tool to obtain the active PRD artifact id:

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "PRD",
  status: "ACTIVE"
```
- If there are more than one active PRD warn the user, otherwise retrieve it an save as `PARENT_PRD_ID`. 
- Use the `get_artifact` tool to obtain the full text:

```
Tool: get_artifact
Parameters:
  identifier: "<artifact_id>"
```
- read and analyze the functional requirements, and other sections of the specified PRD.
- If Individual REQ artifacts have a status of COMPLETE, then you do not need to generate TASKs for them.  Only generate TASKs for REQs that have no status set.
- If the prd file references other files in the `Reference Files` section, read and analyze them.

### Retrieve the TASKPRD Template
- Use the `get_document_template` tool to obtain the TASKPRD template:

```
Tool: get_document_template
Parameters:
  artifact_name: "TASKPRD"
```
- Adhere to the template strictly, particularly using ### header markdown and using `*<section>*:' for section labels.  Downstream management of this artifact depends on this.

### Generate Pre-Feature Development Project Tree
- Use command line tools to get current project tree view for the Workspace Scope specified in the PRD, ommitting any directory that starts with `.` or verbose nested directories like venv, etc... 

### Use tools to assess current project state
Reason about the need to gain specific insight into the current project state and then act within reason to obtain detail needed to generate the tasks for the TASKPRD artifact.

### Generate Parent Tasks:
- Based on the PRD analysis, create the file and generate 6 high-level tasks of reasonable development effort that implement all or part of the feature. These tasks should focus on development of code and script assets, not execution and testing.  A separate testing phase will challenge the implementation by verifying runtime behavior.
- If the parent task is informed by a referenced file in the PRD (like a html design mockup), add them to the `*Reference*:` section.
- Consider REQ requirements documented in the PRD that are implemented by each task and reference them in `*Implements*:` section
- Use tools to generate a draft of the TASKPRD in the `PROVISIONAL_STORE` named `TASKPRD-PROVISIONAL1.md`, leaving the *Reference Files* section empty.

### Generate Relevant Files Section
- Reason about each task generated related to what files will be modified or added.
- Complete the *Relevant Files* section

## Critical Review of REQ relationships
- Retrieve the full parent PRD to put it forward in context using the `get_artifact` tool again.  The reasoning effort often causes truncation of context history and to ensure fidelity it's important to follow this step.

```
Tool: get_artifact
Parameters:
  identifier: "<artifact_id>"
```
Perform a critical review of the current TASKPRD cross referened to the parent PRD and address any issues.

### Ask the user for review
- If the `FULL AUTO` latch is enabled, skip user review and proceed to finalize the TASKPRD
- Ask the user to review the provisional TASKPRD to ensure the requirements are satisfied.  Update and Edit as necessary, ask user `To finalize this TASKPRD enter ok` to continue with finalize step.

### Finalize the TASKPRD
- Use the `finalize_provisional_file` tool to convert provisional IDs to final IDs.  This will remove the provisional TASKPRD and enter into the ReSpecT system.  Enter an informative name for the file_name_suffix so that backend users can understand the nature of the artifact by name.

```
Tool: finalize_provisional_file
Parameters:
  provisional_file_path: "TASKPRD-PROVISIONAL1.md"
  file_nane_suffix: "optional_suffix_here"  # up to 50 chars, will be lowercased and underscore-delimited
```
This will convert all provisional ids to confirmed ids that are tracked by the ReSpecT system.  The tool will return the updated artifact id for the newly entered PRD. This artifact id will be referred to as `NEW_TASKPRD_ID`

- Add the newly generated TASKPRD id as a reference in the parent PRD using the `add_reference` tool:
```
Tool: add_reference
Parameters:
  target_artifact_id: "<PARENT_PRD_ID>>"
  ref_artifact_id: "<NEW_TASKPRD_ID>"  
```

- update the status of the new TASKPRD to ACTIVE using the `update_artifact_status` tool:
```
Tool: update_artifact_status
Parameters:
  artifact_id: "NEW_TASKPRD_ID"
  status: "ACTIVE"
```

### Generate PRD mode completion
- If the `FULL AUTO` latch is enabled, conclude `Generate TASKPRD` mode by moving on to `Task Implementation` mode.  Use tool get_mode_instructions with mode: "Task Implementation"
- Otherwise, report back to the user that the TASKPRD generation is complete and simply ask what to do next with a simple suggestion that `Task Implementation` mode typically follows.

