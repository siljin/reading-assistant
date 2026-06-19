# Reading Assistant Orchestrator

Use this workflow when the user asks for an end-to-end report using the chat
agent's reasoning. The repository scripts do deterministic work only; the agent
fills `analysis.json`.

## Boundary

- Scripts may pull papers, validate files, and render HTML.
- The chat agent performs the LLM reasoning step by reading `source.md` and
  completing `analysis.json`.
- Do not add or request an LLM API key.
- Do not automate ChatGPT/Claude browser UI, scrape a subscription session, run a
  daemon, or start a server.

## End-To-End Flow

1. Read `paper-reading-assistant/SKILL.md` and
   `paper-reading-assistant/references/analysis-rubric.md`.
2. Pull exactly one paper:
   ```bash
   python paper-reading-assistant/scripts/pull_paper.py --profile profiles/medical-ai.json
   ```
   Use a different profile only if the user names one.
3. Identify the created slug from the command output or from:
   ```bash
   python paper-reading-assistant/scripts/workflow_status.py --latest
   ```
4. Read `papers/<slug>/source.md`.
5. Complete `papers/<slug>/analysis.json` using the paper-reading skill:
   - fill paper metadata, headline, summaries, novelty, methods, results,
     limitations, implementation notes, implications, and knowledge graph;
   - build an adaptive `report_plan`;
   - include a `learning_path` section and a `quiz` section.
6. Check readiness:
   ```bash
   python paper-reading-assistant/scripts/workflow_status.py --slug <slug>
   ```
   Continue editing until the status is `ready-to-render` or `rendered`.
7. Render:
   ```bash
   python paper-reading-assistant/scripts/render_report.py \
     --input papers/<slug>/analysis.json \
     --output papers/<slug>/report.html \
     --slug <slug>
   ```
8. Verify:
   ```bash
   python3 -m unittest discover -v
   python3 -m py_compile paper-reading-assistant/scripts/*.py
   git diff --check
   ```
9. Report the headline and the path to `papers/<slug>/report.html`.

## Stop Conditions

Stop and tell the user what happened when:

- `pull_paper.py` reports no eligible paper.
- `source.md` lacks enough abstract/source detail to analyze the paper.
- `workflow_status.py` reports invalid JSON or missing required fields after a
  reasonable completion pass.
- `render_report.py` fails after the JSON is corrected.
- Verification fails and the cause is not local to the current change.
