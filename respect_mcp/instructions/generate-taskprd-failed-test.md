
# Agent Instructions - Failed Tests TASKPRD mode
You have entered the TASKPRD creation module for failed test cases.  Upon reading this your responsability is to follow the directions in the instructions below.

## Goal
To guide an AI assistant in creating a detailed, TASKPRD based on an existing Product Requirements Document (PRD) to address failed tests. The task list should guide a developer through implementation.

## Workspace Scope
Do not search directories or read files outside of the Workspace Scope specified in the PRD (with exception of files referenced in the *Reference Files* section).  

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


### Obrtain active PRD:
- Use the `search_artifacts_by_type` tool to obtain the TESTING state PRD artifact id:

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "PRD",
  status: "TESTING"
```
- If there are more than one PRD warn the user, otherwise retrieve it an save as `PARENT_PRD_ID`. 
- Use the `get_artifact` tool to obtain the full text:

```
Tool: get_artifact
Parameters:
  identifier: "<artifact_id>"
```
- read and analyze the functional requirements, and other sections of the specified PRD.
- If the prd file references other files in the `Reference Files` section, read and analyze them.

### Retrieve related TASKPRD artifacts to see task history
- The PRD should reference one or more TASKPRD ids near the header with `Referenced by: `
- For each child TASKPRD-<id>, use the `get_artifact` tool to obtain the full text:

```
Tool: get_artifact
Parameters:
  identifier: "TASKPRD-<id>"
```

### Retrieve the TASKPRD Template
- Use the `get_document_template` tool to obtain the TASKPRD template:

```
Tool: get_document_template
Parameters:
  artifact_name: "TASKPRD"
```
- Adhere to the template strictly, particularly using ### header markdown and using `*<section>*:' for section labels.  Downstream management of this artifact depends on this.  This TASKPRD is focused on addressing failed test cases so it's likely that the Architecture section will not be relevant.

### Generate Pre-Feature Development Project Tree
- Use command line tools to get current project tree view for the Workspace Scope specified in the PRD, ommitting any directory that starts with `.` or verbose nested directories like venv, etc... 

### Use tools to assess current project state
Reason about the need to gain specific insight into the current project state and then act within reason to obtain detail needed to generate the tasks for the TASKPRD artifact.

### List failed test cases for which to generate tasks to fix 
- Use the `search_artifacts_by_type` tool to obtain the TESTING state PRD artifact id:

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "UACC,SACC",
  status: "FAILED",
  parent: "PARENT_PRD_ID"
```

### Generate tasks in a TASKPRD artifact to address failed tests
- Using the TASKPRD document template:
- One task to address each failed UACC/SACC test.
- In the  `*Implements*:` section add reference to the UACC/SACC artifact id the task addresses.
- The FAILED test case should have failure notes, if so include them in the TASK content.
- Use tools to generate a draft of the TASKPRD in the `PROVISIONAL_STORE` named `TASKPRD-PROVISIONAL1.md`, leaving the *Reference Files* section empty.

### Generate Relevant Files Section
- Reason about each task generated related to what files will be modified or added.
- Complete the *Relevant Files* section in the TASKPRD document template.

## Critical Review of UACC/SACC relationships
- Retrieve the full parent PRD to put it forward in context using the `get_artifact` tool again.  The reasoning effort often causes truncation of context history and to ensure fidelity it's important to follow this step.

```
Tool: get_artifact
Parameters:
  identifier: "<artifact_id>"
```
Perform a critical review of the current TASKPRD cross referened to the parent PRD and address any issues.

### Ask the user for review
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

- Ask the user if they would like to make the newly created PRD the active PRD, but do not offer to enter the Task Implementation mode yet.  If they reply in the affirmative then update the status using the `update_artifact_status` tool:
```
Tool: update_artifact_status
Parameters:
  artifact_id: "NEW_TASKPRD_ID"
  status: "ACTIVE"
```

This action will conclude the Create PRD module work.  Inform the user of the status with a short summary of work performed.  Suggest the net mode is Task Implementation mode, but do not suggest other specific further actions.  If the user affirms they want to move on to Task Implementation mode use the `get_mode_instructions` tool in the `ReSpecT MCP` MCP server to obtain the mode instructions. Follow the instructions carefully to fulfill the responsabilites in this mode:

```
Tool: get_mode_instructions
Parameters:
  mode: "Task Implementation"
```
