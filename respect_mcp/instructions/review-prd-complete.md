# Instructions for PRD Review and Completion mode
You have entered `PRD Review and Completion` mode.  Your goal is to assess the current state of the working PRD (ACTIVE or TESTING) and, summarize the state of the PRD and it's associated child artifacts and then mark artifacts completed that have been cleared by the user.


## Process

### MCP Server
- Ensure the `ReSpecT MCP` server is available and tools are enabled:
`get_document_repo_root`
`get_document_template`
`finalize_provisional_file`

## Find the working PRD (TESTING or ACTIVE)
- Use the `search_artifacts_by_type` tool to find the working PRD

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "PRD",
  status: "ACTIVE,TESTING"
```
- If more than one PRD is returned, report this to the user and ask them to choose one PRD to review and then complete these instructions.
- The working PRD id will be stored as `WORKING_PRD_ID`

## Obtain REQ, ADR, UACC and SACC artifact summary list for the working PRD
- Use the `search_artifacts_by_type` tool to find the nested items under the working PRD with their names and statuses

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "REQ,UACC,SACC",
  parent: "<WORKING_PRD_ID>"
```

## Pull details for ambiguous status artifacts
- Artifacts with status COMPLETED or PASSED are definitive and have been vetted previously to earn that state. 
- Nested REQ, UACC and SACC artifacts with status FAILED, TESTING, ACTIVE, NEW should be considered ambiguous and discussed with the user.  If the user is wishing to review and complete this PRD they may have good reason to fast track the status update for artifacts, but these should be highlighted and reported to the user for their review.


### Happy-path - all nested artifacts are complete/passed!
- Mark the PRD as complete:
```
Tool: update_artifact_status
Parameters:
  artifact_id: "<WORKING_PRD_ID>",
  status: "COMPLETED"
```
- This concludes the PRD review.  Report back on the status.

### Ambiguous nested artifact status path
- Report and review with the user.  

#### TEST artifact review
- Begin with review of the tests (UACC and SACC).  For each ambiguous state test artifact, obtain it's content for review:
```
Tool: get_artifact
Parameters:
  identifier: "<ARTIFACT_ID>"
```
- Any test not in the PASSED or CANCELLED state should be reported to the user for consideration. Their options are to mark them CANCELLED or PASSED. You may update the status with the `update_artifact_status` described previously.

#### REQ artifact review
- Now obtain all ambiguous REQ artifacts and review.
- REQs list related TASK and (U/S)ACC tests and their statuses.  Any Task with all of these references in the COMPLETED and PASSED states can be automatically set to COMPLETED status without user review.
- Summarize any REQ that is still ambiguous with the user and ask for their actions.  REQs can be put into CANCELLED or COMPLETED status

## Final review
- If status changes and review was required, take the time to pull and review the updated PRD content explicitly and review the final document
```
Tool: get_artifact
Parameters:
  identifier: "<WORKING_PRD_ID>"
```

- If the document appears to be settled, update its status to COMPLETED and all nested ADR artifacts to ACTIVE
```
Tool: update_artifact_status
Parameters:
  artifact_id: "<WORKING_PRD_ID>",
  status: "COMPLETED"
```
- get all nested ADR ids:
```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "ADR",
  parent: "<WORKING_PRD_ID>"
```
- for each ADR-<id> update to ACTIVE
```
Tool: update_artifact_status
Parameters:
  artifact_id: "ADR-<id>",
  status: "ACTIVE"
```
### Acceptance Test mode completion

- If the `FULL AUTO` latch is enabled, conclude `PRD Review and Completion` mode and disengage the FULL AUTO latch.
- Report back to the user that the PRD Review and Completion mode is complete and simply ask what to do next without suggesting specific steps.