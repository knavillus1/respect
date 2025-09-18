# Agent Instructions
The user used the /respect slash command. Use these instructions to determine the mode.

## FULL AUTO Mode
If the user includes `FULL AUTO` after `/respect`, run all modes with the FULL AUTO latch enabled. Follow special follow-on mode instructions at the end of each mode when this latch is active.

## MCP Server
Ensure the `ReSpecT MCP` server is available with tools enabled using `get_mode_instructions`.

## Mode Detection and Execution

### Available Modes
- **Detect Project State**: User query is just `/respect`
- **Generate PRD**: Request to generate a PRD
- **Generate TASKPRD**: Request to generate tasks  
- **Failed Tests TASKPRD**: Request to fix failed tests
- **Task Implementation**: Request to execute tasks
- **Setup PRD Tests**: Request to setup tests for a PRD
- **Acceptance Test**: Request to run acceptance tests
- **PRD Review and Completion**: Request to review a completed PRD
- **Architecture Summary**: Request for architecture overview
- **Architecture Review**: Request for architecture review or refactor

### Execution Pattern
For any detected mode:

1. Use the `get_mode_instructions` tool:
   ```
   Tool: get_mode_instructions
   Parameters:
     mode: "<Detected Mode Name>"
   ```

2. Follow the returned instructions carefully to fulfill mode responsibilities

3. When complete, inform the user of completion status and ask what to do next (without suggesting next steps)