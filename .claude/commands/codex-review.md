Review the current working tree changes using OpenAI Codex.

Run the following command to get a code review from Codex:

```bash
git diff HEAD -- . ':!*.lock' ':!*.bin' | codex exec --full-auto "You are a senior code reviewer. Review the following diff for:

1. Security issues (injection, trust boundaries, auth bypass)
2. Race conditions or state management bugs
3. Logic errors or edge cases
4. Resource leaks or cleanup issues
5. API contract mismatches between server and client

Format your response as:
- High: description and file:line reference
- Medium: description and file:line reference
- Low: description and file:line reference

End with a Validation section noting whether the build passes.
Focus on real bugs, not style. Skip issues that are clearly pre-existing."
```

After the command completes, present the Codex review findings to the user. If there are actionable items, ask the user which ones they'd like to address.
