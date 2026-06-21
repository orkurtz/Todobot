# Create Tech Stack

Establish the factual tech stack by checking global standards and scanning local project manifests before engaging the user.

## Important Guidelines
- **Always use AskUserQuestion tool** when interacting.
- **Merge context** — Compare global standards against local CLI findings.
- **Execute OS-appropriate terminal commands** to achieve this goal. Dynamically translate standard Unix concepts (`tree`, `grep`, `cat`, `ls`) into the native commands of the user's current host operating system.
- **Explain Purpose/Usage** — For every technology listed in the final tech stack, write a line or two explaining exactly what we use it for in this specific project.
- **Read ONLY what you need** — Read manifest files only. Do NOT read source code files. Do NOT load directories into context beyond what's needed for discovery.

## Process

### Step 1: Check Global Standards
Check if `agent-os/standards/global/tech-stack.md` exists. If it does, read it to extract the baseline technologies.

### Step 2: Deterministic Local Discovery
Do NOT rely on a hardcoded list of files. You must dynamically discover the project type.
1. Execute OS-appropriate terminal commands (translating Unix concepts like `ls -la` or `tree -L 2`) in the project root to identify which dependency manifest files exist (e.g., `package.json`, `Cargo.toml`, `pom.xml`, `requirements.txt`, `composer.json`, `build.gradle`, `.csproj`, `go.mod`, etc.).
2. Execute OS-appropriate terminal commands (translating concepts like `cat` or `grep`) to read ONLY the identified dependency manifest files. Do NOT read source code.
3. Analyze the raw output to identify the core frameworks, libraries, and database drivers actually installed.

### Step 3: Present and Confirm
Synthesize the findings and use AskUserQuestion based on what was found, making sure to ask the user to provide or confirm a brief explanation (a line or two) of what each technology is used for in the project.

**Scenario A: Global Standard EXISTS**
```
I found a global tech stack standard:
[Summarize global tech]

I also scanned your local manifests and found:
[Summarize local CLI findings, or "No local manifests detected"]

How should we establish the tech stack for this project?

1. Use the Global Standard exactly as-is
2. Use the Local CLI findings
3. Different (I'll specify manually)

(Choose 1, 2, or 3)

After choosing, please also specify what we use each of these technologies for in the project (a line or two each).
```

**Scenario B: NO Global Standard, but Local CLI data FOUND**
```
I scanned the project manifests and identified the following tech stack:

Frontend: [Extracted tech or N/A]
Backend: [Extracted tech or N/A]
Database: [Extracted tech or N/A]
Other: [Extracted tools]

Is this accurate and complete? If so, please tell me what we use each of these technologies for in the project (a line or two each), or provide corrections/additions along with their purpose.
```

**Scenario C: NO Global Standard AND NO Local Manifests FOUND**
```
I couldn't detect existing global standards or local project manifests.
What technologies does this project use, and what is each used for?

Please describe:
- Frontend: (e.g., React, Vue, vanilla JS, or N/A; and its purpose in the project)
- Backend: (e.g., Rails, Node, Django, or N/A; and its purpose in the project)
- Database: (e.g., PostgreSQL, MongoDB, or N/A; and its purpose in the project)
- Other: (hosting, APIs, tools, etc.; and their purpose in the project)
```

### Step 4: Generate File
Create `agent-os/product/tech-stack.md` using the selected/provided data. For every technology listed in the final tech stack, write a line or two explaining exactly what it is used for in the project:

```markdown
# Tech Stack

## Frontend
- **[Tech Name]**: [A line or two describing what we use this technology for in the project]

## Backend
- **[Tech Name]**: [A line or two describing what we use this technology for in the project]

## Database
- **[Tech Name]**: [A line or two describing what we use this technology for in the project]

## Other
- **[Tech Name]**: [A line or two describing what we use this technology for in the project]
```

### Step 5: Confirm Completion

After creating the file, output to user:

```
✓ Tech stack documented: agent-os/product/tech-stack.md

Review this file to ensure accuracy.
You can edit it directly or run /create-tech-stack again to update.

Next steps:
- Run /discover-standards to extract coding conventions from your codebase
- Run /shape-spec (in plan mode) when ready to plan a feature
```
