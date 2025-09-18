# ReSpecT system Auto detect project state mode
These instructions will guide the coding agent to use ReSpecT mcp tools to assess the project state in order to determine the plausible next steps in the project development process.  Do not take action to perform any implementation in this step, just determine the next mode

### MCP Server
- Ensure the `ReSpecT MCP` server is available and tools are enabled:
- You can use `search_artifacts_by_type` (artifact_type, status=,parent=) to search for all artifacts of a certain type and optionally for a certain status (default to all) or cetain parent artifact id (default to all).
- You can use `search_artifacts_by_id` (identifier, search_references=true) to find a specific artifact and also all artifacts that reference it with the context of the reference.  This will help, for instance, to find child TASKPRDs for a parent PRD.

## The PRD record is core to the current status of the project.
- Use the `search_artifacts_by_type` tool to find all PRDs and get their status:

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "PRD"
```
The expected state is that all PRDs will be COMPLETED with exception of one, usually the last.  This PRD will have state NEW, ACTIVE, or TESTING (These are collectively `WORKING` states).  If there is more than one PRD with one of these states then there is ambiguity and you must stop and inform the user that only one PRD can be in a non-completed state at a time.
- For the single `WORKING` PRD (call it `WORKING_PRD_ID`) use the `search_artifacts_by_id` to pull the primary artifacts and all artifacts that reference it.  This will show you the TASKPRD artifacts that are children of the working PRD:
```
Tool: search_artifacts_by_id
Parameters:
  artifact_id: "<WORKING_PRD_ID>"
```

## Determine the mode
0. NEW PRD -> Ask the user if they would like to make the NEW PRD the active PRD and if so run the `update_artifact_status' tool to set the status to ACTIVE.
1. ACTIVE PRD, but no related TASKPRD -> `Generate TASKPRD` mode
2. ACTIVE PRD, ACTIVE TASKPRD -> `Task Implementation` mode
3. ACTIVE PRD, COMPLETED TASKPRD -> `Setup PRD Tests` mode
4. TESTING PRD -> if there is a PRD in TESTING mode, determine the test artifact (UACC and SACC) status with the `search_artifacts_by_type` tool
    ```
    Tool: search_artifacts_by_type
    Parameters:
      artifact_type: "UACC,SACC",
      parent: "<WORKING_PRD_ID>"
    ```
    - If there are NEW tests then the mode should be `Acceptance Test` where you will perform or guide testing tasks.
    - If all tests have PASSED then the mode should be `PRD Review and Completion` where you will help review the PRD before marking it complete.
    - If there are FAILED tests then the mode should be `Failed Tests TASKPRD` where you will guide an effort to produce a followup TASKPRD to address the failure.


Inform the user of your intent to enter the mode and request affirmation.
