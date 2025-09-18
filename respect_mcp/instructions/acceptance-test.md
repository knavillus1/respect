# Acceptance Test mode
You have entered the `Acceptance Test` mode.

## Goal
To guide an AI assistant in performing system acceptance tests (SACC) and guiding the user to perform user acceptance tests (UACC).

## Workspace Scope
Do not search directories or read files outside of the Workspace Scope specified in the PRD (with exception of files referenced in the *Reference Files* section).  Do not open the ReSpecT artifact files directly or attempt to modify them.  Use ReSpecT MCP tools for all read and update access.

## Process

### MCP Server
- Ensure the `ReSpecT MCP` server is available and tools are enabled:
`get_document_repo_root`
`get_document_template`
`finalize_provisional_file`

### Obrtain TESTING state PRD:
- Use the `search_artifacts_by_type` tool to obtain the active PRD artifact id:

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "PRD",
  status: "TESTING",
  parent: "<TESTING_PRD_ID>"
```
- If there are more than one active PRD warn the user, otherwise retrieve it an save as `TESTING_PRD_ID`. 
- Use the `get_artifact` tool to obtain the full text:

```
Tool: get_artifact
Parameters:
  identifier: "<TESTING_PRD_ID>"
```
- Read and analyze the PRD, which should include acceptance tests in the `## Acceptance Tests` section.

### Obtain the list of acceptance tests in the NEW status and choose target acceptance test
- Use the `search_artifacts_by_type` tool to obtain the active PRD artifact id:

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "UACC,SACC",
  status: "NEW"
```
- If all acceptance tests are in the PASSED state, skip to the last section `### PRD Completion`
- Otherwise pick the first available UACC or SACC in the NEW state as `TARGET_ACC_ID`.
- Fetch the exact content of the artifact to get bring it to focus by using the tool `get_artifact` to obtain the contents of the artifact:
        ```
        Tool: get_artifact
        Parameters:
        identifier: "<TARGET_ACC_ID>"
        ```
### Complete the target acceptance test
- If the `FULL AUTO` latch is enabled, only SACC system tests should be available.  Complete all tests without user feedback
- For system acceptance test SACC:
    - Perform each step and as they are completed use the tool `mark_artifact_step_done` to update the entire body of the artifact:
        ```
        Tool: mark_artifact_step_done
        Parameters:
        artifact_id: "<TARGET_ACC_ID>"
        step_number: "<step number like 12.1>
        ```
- For user acceptance test UACC:
    - Guide the user to perform each step and report on observations
    - as they are completed use the tool `mark_artifact_step_done` to update the entire body of the artifact:
        ```
        Tool: mark_artifact_step_done
        Parameters:
        artifact_id: "<TARGET_ACC_ID>"
        step_number: "<step number like 12.1>
        ```
- If errors occur during testing that can be addressed with small code patches to address minor bugs, proactively fix these to achieve test success.  Do not attempt larger code refactors that require changes to interfaces or method signatures.  If a test case fails this spectacularly then it needs to be marked as FAILED below.  
- If step instructions are incorrect, but the intent is sound you may try alternative solutions that achieve the same goal.  If these alternatives work update the acceptance test record by:
    - Fetch the exact content of the artifact to get bring it to focus by using the tool `get_artifact` to obtain the contents of the artifact:
        ```
        Tool: get_artifact
        Parameters:
        identifier: "<TARGET_ACC_ID>"
        ```
    - Then update the artifact with your changes to the step using the tool `update_artifact_content` to update the entire body of the artifact:
        ```
        Tool: update_artifact_content
        Parameters:
        identifier: "<TARGET_ACC_ID>"
        content: "<full altered content of the artifact with corrected steps>"
        ```
### Test Failure
- If the acceptance test fails update the status of the acceptance test by using the tool `update_artifact_status` :
        ```
        Tool: update_artifact_status
        Parameters:
        artifact_id: "<TARGET_ACC_ID>"
        status: "FAILED"
        ```
    - Add a failure reason to the acceptance test:
        - Fetch the exact content of the artifact to get bring it to focus by using the tool `get_artifact` to obtain the contents of the artifact:
            ```
            Tool: get_artifact
            Parameters:
            identifier: "<TARGET_ACC_ID>"
            ```
        - Then update the artifact with your changes to the step using the tool `update_artifact_content` to update the entire body of the artifact:
            ```
            Tool: update_artifact_content
            Parameters:
            identifier: "<TARGET_ACC_ID>"
            content: "<full altered content of the artifact wiath failure notes>"
            ```

### Test Success
- If the acceptance test passes update the status of the acceptance test by using the tool `update_artifact_status` :
        ```
        Tool: update_artifact_status
        Parameters:
        artifact_id: "<TARGET_ACC_ID>"
        status: "PASSED"
        ```
- The acceptance test should reference requirements that are tested on a line like: `*Tests*: REQ-5, REQ-7`.  For each of these, update the status of the REQ artifact to COMPLETED using the tool `update_artifact_status` :
        ```
        Tool: update_artifact_status
        Parameters:
        artifact_id: "<REC_ID>"
        status: "COMPLETED"
        ```


### Acceptance Test mode completion

- If the `FULL AUTO` latch is enabled, conclude `Acceptance Test` mode by moving on to `PRD Review and Completion` mode.  Use tool get_mode_instructions with mode: "PRD Review and Completion"
- Otherwise, report back to the user that the Acceptance Test mode is complete and simply ask what to do next with a simple suggestion that `PRD Review and Completion` mode typically follows.
