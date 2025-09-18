# Instructions for Architecture Summary mode
- You have entered the `Architecture Summary` mode.  The goal of this review is to perform an archtecure review of the current project and produce an ASD, architecure summary document.


## Process

### MCP Server
- Ensure the `ReSpecT MCP` server is available and tools are enabled:
`get_document_repo_root`
`finalize_provisional_file`

### Get Document Repository Root 
- Use `get_provisional_store` tool to verify environment setup and get the repository root path
```
Tool: get_provisional_store
Parameters:
  None
```
- The value of the document root will be referenced from now on as `PROVISIONAL_STORE`

### Get existing ASD artifact
- Use the `search_artifacts_by_type` tool to obtain the ACTIVE state ASD artifact id, if one exists.
```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "ASD",
  status: "ACTIVE"
```
- If there are more than one ASD warn the user, otherwise retrieve it an save as `ORIG_ASD_ID`. 
- Use the `get_artifact` tool to obtain the full text:

```
Tool: get_artifact
Parameters:
  identifier: "<ORIG_ASD_ID>"
```
### Get all ACTIVE ADR (Architechture decision record) not yet incorporated into an ASD
```
Tool: search_artifacts_by_type
Parameters:
  artifact_type: "ADR",
  status: "ACTIVE"
```
- If there are active ADRs, store the IDS as `EXISTING_ADR_IDS`

```
Tool: get_artifact
Parameters:
  identifier: "ADR-<id> in EXISTING_ADR_IDS"
```

### Get the ASD document template
- Use the `get_document_template` tool to obtain the ASD template:

```
Tool: get_document_template
Parameters:
  artifact_type: "ASD"
```
- The template provided by the tool will serve as your guidepost for the output format of the ASD you create in the steps below.  The ID ASD-PROVISIONAL1 should be used exactly as is, this id will be assigned later during finalization.

### Review the ASD, ADR and the project workspace 
- Confirm current architecture documentation in detail by cross referencing the workspace.   
- Check for discrepancies and undocumented architecture facts.
- Ignore the ReSpecT system document stores that begin with `respect*`

### Create the provisional ASD document
- Use the ASD document template and save `PROVISIONAL_STORE/ASD-PROVISIONAL1.md` with a draft ASD.

### Ask for user review and finalize
- Ask the user to review 
- Register the new artifact with:
```
Tool: finalize_provisional_file
Parameters:
  provisional_file_path: "ASD-PROVISIONAL1.md"
  file_nane_suffix: "optional_suffix_here"  # up to 50 chars, will be lowercased and underscore-delimited
```
- Note the new artifact id as `NEW_ASD_ID`
- Make this the ACTIVE ASD:
```
Tool: update_artifact_status
Parameters:
  artifact_id: "NEW_ASD_ID"
  status: "ACTIVE"
```

### Set existing ASD and ADR to REPLACED
```
Tool: update_artifact_status
Parameters:
  artifact_id: "ORIG_ASD_ID"
  status: "REPLACED"
```
```
Tool: update_artifact_status
Parameters:
  artifact_id: "Each ADR in EXISTING_ADR_IDS"
  status: "REPLACED"
```

### Mode Complete
- This concludes architecture summary creation.  Don't suggest specific next steps, just report that the process is finished and you're ready for more work.