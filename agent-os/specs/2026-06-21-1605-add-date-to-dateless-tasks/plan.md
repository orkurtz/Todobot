# Plan: Add Date to Dateless Tasks Command

## State Tracking & Execution Rules
Future agents MUST strictly update this file during execution.
- [x] Completed: src/services/task_service.py, src/routes/webhook.py, README.md
- [ ] Pending
- [/] In Progress

**PONYTAIL RULE (YAGNI & MINIMIZATION):** Before writing any new code or creating new files, you MUST run through the Ponytail checklist:
  1. Is this feature/code absolutely necessary? (YAGNI)
  2. Does the standard library or native platform features already solve this?
  3. Can we reuse an existing utility, helper, or package in the codebase instead of writing new code?
  4. Can the solution be simplified or written in fewer lines?
  *Goal:* Act like the "laziest senior developer." Do not write code you don't need. Keep it simple, minimal, and clean.

**VERIFICATION GATE:** Before changing any task to `[x]`, you MUST:
  1. Read the project manifest (package.json, pyproject.toml, Cargo.toml, go.mod, etc.) to find the defined lint/check/typecheck script.
  2. Run ONLY scripts explicitly defined in that manifest. NEVER invent commands.
  3. If no lint script exists → run a syntax-only check (e.g., `node --check file.js` or `python -m py_compile file.py`). Use OS-appropriate commands.
  4. If no manifest exists → skip and note: "No manifest detected — manual review advised."
  5. Scan output for: "error", "Error", "FAILED", "Cannot find". Exit code 0 with zero errors required. Warnings are acceptable but must be noted.
  6. If errors exist → remain in `[/]` and fix. Mark `[x]` ONLY upon a clean result.

**RECOVERY RULE:** If you find a `[/] In Progress` item at session start, re-read the files from the previous `[x]` completed entries, verify the partial work, then decide: resume or reset to `[ ]`.

**POST-TASK CHECKLIST:** After completing each task, output:
- [ ] Updated plan.md state marker to `[x]`
- [ ] Listed all modified files in the `[x]` entry
- [ ] Ran Verification Gate — result: [clean / warnings noted / errors fixed]

Do NOT rewrite task text. Only mutate the state markers.

## Task 1: Save Spec Documentation
Create `agent-os/specs/2026-06-21-1605-add-date-to-dateless-tasks/` with:
- plan.md (this plan)
- shape.md (shaping decisions and context)
- standards.md (relevant standards that apply)
- references.md (pointers to similar code)

## Task 2: Implement assign_due_date_to_dateless_tasks in TaskService
- [x] Implement `assign_due_date_to_dateless_tasks` in `src/services/task_service.py` to target pending, non-recurring tasks without a due date, assigning them to the next full hour in Israel.

## Task 3: Map the new command "הוסף תאריך למשימות" in Webhook
- [x] Map "הוסף תאריך למשימות" (and English variations) in `src/routes/webhook.py`'s `handle_basic_commands` to `task_service.assign_due_date_to_dateless_tasks`.

## Task 4: Update Help and Documentation
- [x] Update help strings in `src/routes/webhook.py` to document the new command.
- [x] Update `README.md` to document the new command.

## Task 5: Verify Changes
- [x] Run syntax checks via `python -m py_compile` on modified files.
