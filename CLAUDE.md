# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Public-demos is a static demo platform by Collinear AI showcasing AI agent capabilities through interactive web-based task viewers and evaluation environments. It contains four demos served as pure HTML/CSS/JS with embedded JSON data.

## Build & Development

No build step is needed for most demos — open HTML files directly or serve with any static file server.

**Long-horizon tasks** is the exception. It has a Python build step that compiles YAML data into a self-contained HTML file:

```bash
cd demos/long-horizon-tasks
python build.py
# Requires PyYAML (auto-installed via pip if missing)
# Reads personas.yaml, rubrics.yaml, project_dag.md from each scenario_*/
# Outputs compiled index.html with all data embedded
```

There are no test suites, linters, or CI pipelines configured.

## Architecture

**Landing page** (`index.html`): 4-column responsive card grid linking to each demo. Uses `brand.css` for shared styling.

**Four demos under `demos/`:**

- **sample-viewer/** — GDPVal: displays AI agent task outputs across 21 professional domains. `manifest.json` indexes domain JSON files, each containing input data, golden outputs, agent outputs from multiple models, and agent reasoning trajectories. All rendering is client-side vanilla JS.

- **long-horizon-tasks/** — Multi-day business scenarios with persona-driven task dependencies. Each `scenario_*/` directory contains `personas.yaml` (org structure, 8+ detailed personas), `rubrics.yaml` (1-5 scoring criteria), `verifiers.py` (programmatic action log validators), and `project_dag.md` (task dependency graph in Mermaid). `build.py` compiles these into `dashboard_template.html` to produce the final `index.html`.

- **rl-gym-personal-assistant/** — OpenClaw: tool execution traces and scoring across 10+ simulated tools. Single self-contained `index.html`.

- **rl-gym-visual-explorer/** — B2B: HR recruiting and FX financial analysis workflows. Single self-contained `index.html`.

- **swe-bench-zig/** — SWE-Bench style coding benchmark in Zig (low-resource language). Aggregates 4 PRs from zigtools/zls into one long-horizon task. Includes Harbor-format benchmark files in `harbor-task/`, evaluation results from Claude Opus 4.6 (2 runs), and 54-check verification. Self-contained `index.html` with embedded data.

## Styling Conventions

- Orange accent `#ee8443` on light backgrounds, CSS variables for light/dark theming
- Archivo font family (files in `fonts/`)
- Responsive breakpoints: 4-column → 2-column → 1-column
- No CSS frameworks; all styles are inline or in `brand.css`
