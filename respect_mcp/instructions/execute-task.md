# Agent Instructions: Task Implementation mode
You have entered the `Task Implementation` module.  Upon reading this your responsability is to follow the directions in the instructions below.

## Goal
- The goal of this module is to implement uncompleted tasks in an Active TASKPRD artifact.  
- When all tasks are complete, update the status of the TASKPRD to COMPLETED
- If the `FULL AUTO` latch is enabled, adhere to FULL AUTO path instructions
- If the user's request suggested that their intent is to run all of the available tasks, then you are in `CONTINUOUS` mode.  In this case iterate these steps until all tasks are completed. `CONTINUOUS` mode is superceeded by `FULL AUTO` mode, but should not trigger FULL AUTO mode.

## Process

### MCP Server
- Ensure the `ReSpecT MCP` server is available and tools are enabled:
`search_artifacts_by_type`
`search_artifacts_by_type`

### Find the current TASKPRD document
- Use the `search_artifacts_by_type` tool to obtain the active TASKPRD artifact id:

```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "TASKPRD",
  status: "ACTIVE"
```
If there is no active TASKPRD, or there is more than one active TASKPRD, stop and report back to the user that you cannot obtain a task to execute on and explain why. 

Store the active TASKPRD artifact id as `ACTIVE_TASKPRD_ID`

### Obtain the active TASKPRD artifact
-  Use the `get_artifact` tool to obtain the full text of the active TASKPRD artifact:

```
Tool: get_artifact
Parameters:
  identifier: "<ACTIVE_TASKPRD_ID>"
```

### Identify the task to execute
- Look at the list of TASK artifacts in the `## Implementation Tasks` section.  Each task will list a status under it's header.  
- If a task is listed as ACTIVE, then this is your task to continue with.  Store the artifact id (`TASK<id>`) as `ACTIVE_TASK_ID`, move on the next step
- Otherwise, choose the next sequential task and store the artifact id (`TASK-<id>`) as `NEXT_TASK_ID`. Use the `update_artifact_status` tool to update the status of this task to ACTIVE:
```
Tool: update_artifact_status
Parameters:
  artifact_id: "<NEXT_TASK_ID>"
  status: "ACTIVE"
``` 
and store the now active artifact id as `ACTIVE_TASK_ID`

### Obtain the parent PRD for context
- The TASKPRD artifact will declare a parent PRD after `*Parent*:`.  Store this artifact id (`PRD-<id>`) as `PARENT_PRD_ID`.
- use the `get_artifact` tool to obtain the parent PRD artifact text:

```
Tool: get_artifact
Parameters:
  identifier: "<PARENT_PRD_ID>"
```

### Research project and referenced documents
- Review the TASKPRD and PRD files, and if necessary read referenced files specified in those documents to provide context for the task at hand so you have sufficient background to plan the steps required to fulfill the task objectives.  

### Obtain fresh copy of the active task
- use the `get_artifact` tool to obtain the active TASK artifact text:

```
Tool: get_artifact
Parameters:
  identifier: "<ACTIVE_TASK_ID>"
```
- If you have continued work on an existing ACTIVE TASK, then the task will show implementation steps with indication of which steps have been completed.  Review for any changes needed and if no modifications to the plan are needed, skip the next step.  Otherwise, add task steps in the next step

### Add task steps
- Update the TASK with a steps section after the status line.  Task steps should focus on development of code assets, not execution and verification.  A separate acceptance test phase will challenge runtime behaivor and address bugs and issues.
- Leave two spaces at the end of each line so markdown renders without issue  Strictly adhere to the format below becuase the step update depends on the convention of the format you add here:
``` markdown 
### TASK-12: 
`Status`: NEW  
[ ] 12.1 Step one description    
[ ] 12.2 Step two description   
*Implements*: REQ-3, REQ-7  
```
- Use the tool `update_artifact_text` to update the entire body of the artifact:
```
Tool: update_artifact_text
Parameters:
  identifier: "<ACTIVE_TASK_ID>"
  content: "<Updated task content with steps added>
```

### Execute TASK steps to fulfill task objectives
- The current step is `CURRENT_TASK_STEP`
- In all reasoning ouput begin with a header to declare the state which will result in better context memory:
`**** <ACTIVE_TASKPRD_ID> - <ACTIVE_TASK_ID> - <CURRENT_TASK_STEP> ****`
- Address and fix any compliation or build issue created during code changes
- Run unit tests using the specified test protocol
- Adhere to best practice software engineering principles
- perform each step and as they are completed use the tool `mark_artifact_step_done` to update the entire body of the artifact:
```
Tool: mark_artifact_step_done
Parameters:
  artifact_id: "<ACTIVE_TASK_ID>"
  step_number: "<step number like 12.1>
```

### Task completion
- If you complete all steps: perform final diligence on the project state
- Ensure build, compilation and tests run
- Use the `update_artifact_status` tool to update the status of this task to completed:
```
Tool: update_artifact_status
Parameters:
  artifact_id: "<ACTIVE_TASK_ID>"
  status: "COMPLETED"
``` 
- If the mode is `CONTINUOUS` mode or if the `FULL AUTO` latch is enabled, repeat steps until all TASKPRD tasks are complete.

### TASKPRD completeion
- When all TASKPRD tasks are marked complete use the `update_artifact_status` tool to update the status of this TASKPRD artitfact to completed:
```
Tool: update_artifact_status
Parameters:
  artifact_id: "<ACTIVE_TASKPRD_ID>"
  status: "COMPLETED"
``` 

- If the `FULL AUTO` latch is enabled, conclude `Task Implementation` mode by moving on to `Setup PRD Tests` mode.  Use tool get_mode_instructions with mode: "Setup PRD Tests"
- Otherwise, report back to the user that the Task Implementation is complete and simply ask what to do next with a simple suggestion that `Setup PRD Tests` mode typically follows.
