# TrainAiCad

User-approved sheet-metal CAD production rules and tools: PDF / image / customer DXF DATA → canonical geometry JSON → verified DXF. Built to run locally with Claude Code: the AI reads the drawing and decides; deterministic tools do the tables, arithmetic, geometry checks and DXF export.

- Start a job: open the repo in Claude Code and say `E2E` with the source files → [JOB_CARD.md](JOB_CARD.md).
- Rules: [rules/](rules/) (one short card per topic; [rules/CENSUS.md](rules/CENSUS.md) maps drawing keywords to cards).
- Tables: [data/](data/) (read by `tools/lookup.py`, never by eye).
- Maintenance and approval flow: [CLAUDE.md](CLAUDE.md).

```sh
pip install -r requirements.txt
python -m pytest tests -q
```

The optional Windows dashboard LuanAppTools now lives in its own repository. Every DXF still needs human inspection.
