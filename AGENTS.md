# Agent Instructions

## ReSpecT system slash command
- If the user begins with `/respect` regardless of case then you are to enter ReSpecT project management mode. Use the `get_mode_instructions` tool in the `ReSpecT MCP` MCP server to obtain the master ReSpect system instructions. Follow the instructions carefully to fulfill the responsabilites in this mode::

```
Tool: get_mode_instructions
Parameters:
  mode: ReSpecT Master"
```


## code change summary
- When code changes have been made run something like this to get a list of unstaged changes in git and show the results as part of your wrap up:
```bash -c '
modified_files=$(git diff --numstat | wc -l | xargs)
untracked_files=$(git ls-files --others --exclude-standard | wc -l | xargs)
total_files=$((modified_files + untracked_files))

if [ "$modified_files" -gt 0 ]; then
    insertions=$(git diff --shortstat | grep -o "[0-9]* insertion" | grep -o "[0-9]*" || echo 0)
    deletions=$(git diff --shortstat | grep -o "[0-9]* deletion" | grep -o "[0-9]*" || echo 0)
else
    insertions=0
    deletions=0
fi

echo "$total_files files changed +${insertions:-0} -${deletions:-0}"
echo

git diff --numstat | awk "{
    if (\$3 == \"\") next;
    filename = \$3;
    gsub(/.*\//, \"\", filename);
    printf \"%-40s +%-3s -%-3s\n\", filename, \$1, \$2;
}"

git ls-files --others --exclude-standard | awk "{
    filename = \$0;
    gsub(/.*\//, \"\", filename);
    printf \"%-40s +NEW -0  \n\", filename;
}"
'```