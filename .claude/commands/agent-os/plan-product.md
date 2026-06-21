# Plan Product

Establish foundational product documentation through an interactive conversation. Creates mission and roadmap files in `agent-os/product/`.

## Important Guidelines

- **Always use AskUserQuestion tool** when asking the user anything
- **Keep it lightweight** — gather enough to create useful docs without over-documenting
- **One question at a time** — NEVER ask more than one question per message. NEVER proceed to the next question before receiving the user's answer. If the answer is unclear, ask ONE clarifying follow-up before moving on.
- **State is on disk, not in memory** — Always re-read `roadmap.md` before updating markers. Never assume task status from conversation history.

## Process

### Step 1: Determine Lifecycle State

Use AskUserQuestion:

```
Is this a brand new project or an existing project? (Choose: New / Existing)
```

**Mandate waiting for the user's response before proceeding.**

### Step 2: Gather Product Vision (for mission.md)

Update the process to branch based on the answer from Step 1. Ensure questions are asked sequentially, waiting for an answer after each.

#### Path: NEW Project
Use AskUserQuestion sequentially, waiting for a response after each question:

1. **Describe the product you want to build. What is it and what does it do?**
2. **What specific problem does this solve, and who has this problem?**
3. **What's your planned approach — key technologies, integrations, or architecture ideas?**
4. **What does "done" look like for v1? What's the minimum to consider it launched?**

#### Path: EXISTING Project
Use AskUserQuestion sequentially, waiting for a response after each question:

1. **What specific change or upgrade are you making?**
2. **How do you plan to approach it technically? (libraries, patterns, architecture changes)**
3. **What is the current state — what works, what is broken, what already exists?**
4. **What could block this? (dependencies, breaking changes, performance concerns)**

### Step 3: Gather Roadmap (for roadmap.md)

Update the process to branch based on the answer from Step 1. Ask sequentially, waiting for an answer after each.

#### Path: NEW Project
Use AskUserQuestion sequentially, waiting for a response after each question:

1. **What are the must-have features for launch (MVP)?**
2. **What features are planned for post-launch?**

#### Path: EXISTING Project
Use AskUserQuestion sequentially, waiting for a response after each question:

1. **What are the major features or architectural changes required for this new phase?**
2. **What are the exact technical or business acceptance criteria for this new phase to be considered "Complete"?**

### Step 4: Generate Files

Create the `agent-os/product/` directory if it doesn't exist.

Generate each file based on the information gathered:

#### mission.md

```markdown
# Product Mission

## Background & Problem

[Insert background, problem, or current situation from Step 2]

## Scope / Audience

[Insert target audience or scope of upgrade from Step 2]

## Solution & Constraints

[Insert solution description and any constraints/considerations from Step 2]
```

#### roadmap.md

```markdown
# Product Roadmap

## State Tracking & Execution Rules
Future agents MUST strictly update this file during execution.
- `[ ]` Pending
- `[/] In Progress` — update to this BEFORE writing any code
- `[x] Completed: [comma-separated modified files]`

**VERIFICATION GATE:** Before changing any task to `[x]`, you MUST:
  1. Read the project manifest (package.json, pyproject.toml, Cargo.toml, go.mod, etc.) to find the defined lint/check/typecheck script.
  2. Run ONLY scripts explicitly defined in that manifest. NEVER invent commands.
  3. If no lint script exists → run a syntax-only check (e.g., `node --check file.js` or `python -m py_compile file.py`). Use OS-appropriate commands.
  4. If no manifest exists → skip and note: "No manifest detected — manual review advised."
  5. Scan output for: "error", "Error", "FAILED", "Cannot find". Exit code 0 with zero errors required. Warnings are acceptable but must be noted.
  6. If errors exist → remain in `[/]` and fix. Mark `[x]` ONLY upon a clean result.

**RECOVERY RULE:** If you find a `[/] In Progress` item at session start, re-read the files from the previous `[x]` completed entries, verify the partial work, then decide: resume or reset to `[ ]`.

Do NOT rewrite task text. Only mutate the state markers.

[Depending on Step 1, generate the appropriate section below]

### For NEW Projects:
## Phase 1: MVP

- [ ] [Insert must-have features for launch - from Step 3]

## Phase 2: Post-Launch

- [ ] [Insert planned future features - from Step 3, or "To be determined" if they said none yet]

### For EXISTING Projects:
## Current State

- [ ] [Insert current stage / situation description from Step 2]

## New Phase

- [ ] [Insert major feature / architectural change required - from Step 3]
- [ ] [Insert acceptance criteria - from Step 3]
```


### Step 5: Confirm Completion

After creating all files, output to user:

```
✓ Product documentation created:

  agent-os/product/mission.md
  agent-os/product/roadmap.md

Review these files to ensure they accurately capture your product vision.
You can edit them directly or run /plan-product again to update.

Next steps:
- Run /create-tech-stack to document your technology choices
- Run /shape-spec (in plan mode) when you're ready to plan a feature
```

## Tips

- If the user provides very brief answers, that's fine — the docs can be expanded later
- If they want to skip a section, create the file with a placeholder like "To be defined"
- The `/shape-spec` command will read these files when planning features, so having them populated helps with context
