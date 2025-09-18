````markdown
# Agent Instructions: Setup PRD Tests mode
You have entered the `Setup PRD Tests` module. Upon reading this your responsibility is to follow the directions below to transition the feature from implementation to testing readiness.

## Goal
- Verify if the active PRD has fully implemented requirements
- Adding Acceptance Tests (SACC or UACC) to the PRD
- Setting the PRD to TESTING 

## Process

### MCP Server
- Ensure the `ReSpecT MCP` server is available and tools are enabled:
`search_artifacts_by_type`
`get_artifact`
`update_artifact_status`
`get_document_template`
`add_artifact`

### Find the active PRD
- Use the `search_artifacts_by_type` tool to obtain the ACTIVE TASKPRD artifact id:

```
Tool: search_artifacts_by_type
Parameters:
	artifact_type: "PRD",
	status: "ACTIVE"
```
- If there is zero or more than one ACTIVE PRD, stop and report back why completion cannot proceed.
- Store the id as `ACTIVE_PRD_ID` and fetch the artifact text:

```
Tool: get_artifact
Parameters:
	identifier: "<ACTIVE_PRD_ID>"
```

### Find the implementing TASKPRD
- The PRD will reference related artifacts, note each TASKPRD id and:
- For each use the `get_artifact` tool to obtain the full TASKPRD content:
```
Tool: get_artifact
Parameters:
	identifier: "<TASKPRD-id"
```

### Determine PRD Testing status eligability
- For each `REQ-<n>` in the PRD artifact consider it to be:
  - `fully implemented` if it has complete task completion (i.e. every task in *Implementing Task*: has the completed status follwing it like: TASK-10 (COMPLETED))
  - `incomplete` if there are implenting tasks not marked COMPLETE
- If there are fully implemented REQs, then 
- If any REQs are incomplete, break this process and report to the user the artifact ids that are incompletely implemented and suggest a task generation step.

### Obtain acceptance test artifact templates
- You will be writing acceptance tests for either human testers (UACC), coding agent testers (SACC) or both.  Obtain the templates for these artifacts using the tool `get_document_template`:
```
	 Tool: get_document_template
	 Parameters:
		 artifact_type: "UACC"
```
```
	 Tool: get_document_template
	 Parameters:
		 artifact_type: "SACC"
```

### For each fully implemented REQ: Update status and add Acceptance Tests

- Update the REQ status to `TESTING`:
```
Tool: update_artifact_status
Parameters:
    artifact_id: "REQ-<n>"
    status: "TESTING"
```  
- If the `FULL AUTO` latch is enabled, only implement system SACC tests.  Codex should be run with full system permissions when this latch is enabled, giving the coding agent full access to run environment commands.
- Add one or more acceptance tests for this REQ using the templates obtained for either human or automated coding agent testers.  
- Use human UACC tests for tasks that require scripts to be executed, environment setup, or for direct UI interaction that can't be tested directly in a shell environment.  If SACC tests depend on environment setup, start with an initial UACC human test to set this up first.
- SACC tests are for actions that can be carried out by the conding agent independently.  Do not set up SACC tests that require environment setup with shell commands due to sandbox restrictions.  If a preliminary UACC test is defined that leads to environment setup, later SACC tests can test endpoint functionality by the system coding agent, just make reference to the dependency on environment setup.
- Each task generated will need a unique <id> that is populated in the PROVISIONAL<id> and [ ] <id>.1 steps in the template.  This id does not need to match the associated REQ id.
```
Tool: add_artifact
Parameters:
    parent_artifact_id: "<PARENT_PRD_ID>"
    new_artifact_type: "UACC" | "SACC"
    new_artifact_content: "<full artifact content>"
```

### Register the provisional ids
- It's critical that the provisional ids get registered with the ReSpecT manager.  Use tool register_provisional_ids
```
Tool: register_provisional_ids
Parameters:
    artifact_id: "PARENT_PRD_ID"
```  

### Set PRD  status
- If all REQs have been covered by acceptance tests:
- Update the PRD status to `TESTING`:
```
Tool: update_artifact_status
Parameters:
    artifact_id: "PARENT_PRD_ID"
    status: "TESTING"
```  

### Setup PRD Tests mode completion

- If the `FULL AUTO` latch is enabled, conclude `Setup PRD Tests` mode by moving on to `Acceptance Test` mode.  Use tool get_mode_instructions with mode: "Acceptance Test"
- Otherwise, report back to the user that the Setup PRD Tests mode is complete and simply ask what to do next with a simple suggestion that `Acceptance Test` mode typically follows.