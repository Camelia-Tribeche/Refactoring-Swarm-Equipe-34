# Refactoring Swarm

> An autonomous multi-agent software maintenance system that analyzes, refactors, and validates Python projects using collaborative AI agents.

## Overview

Refactoring Swarm is a research-oriented software engineering project developed as part of the Software Engineering (IGL) laboratory at the École Nationale Supérieure d'Informatique (ESI).

The objective is to automate software maintenance by orchestrating multiple Large Language Model (LLM) agents that collaboratively inspect, repair, and validate Python code with minimal human intervention.

Instead of relying on a single AI assistant, the system distributes responsibilities among specialized agents, creating an autonomous refactoring workflow capable of improving code quality while preserving correctness.

---

## Architecture

The system is composed of three specialized AI agents.

### 🔍 Auditor Agent

Responsible for:

- Reading the target project
- Running static code analysis
- Detecting code smells and quality issues
- Producing a refactoring plan

---

### 🔧 Fixer Agent

Responsible for:

- Reading the Auditor's report
- Refactoring Python files
- Fixing detected issues
- Improving code readability and maintainability
- Applying changes iteratively until quality requirements are met

---

### ⚖️ Judge Agent

Responsible for:

- Executing unit tests
- Validating that the refactored code still works correctly
- Returning execution logs to the Fixer if failures occur
- Approving the final version when all tests pass

This creates a **self-healing feedback loop** where the Fixer continuously improves the project until it satisfies the required quality standards.

---

## Workflow

```
Python Project
      │
      ▼
┌─────────────────┐
│ Auditor Agent   │
│ Static Analysis │
└─────────────────┘
      │
      ▼
 Refactoring Plan
      │
      ▼
┌─────────────────┐
│  Fixer Agent    │
│ Refactoring     │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  Judge Agent    │
│ Unit Testing    │
└─────────────────┘
      │
 ┌────┴─────┐
 │          │
 ▼          ▼
Fail      Success
 │          │
 └──► Fixer End
```

---

## Features

- Multi-agent architecture
- Autonomous software maintenance
- Static code analysis
- Automatic Python refactoring
- Unit test execution
- Self-healing feedback loop
- Iterative improvement
- Structured experiment logging
- Secure sandbox execution

---

## Tech Stack

### Backend

- Python

### AI

- Large Language Models (LLMs)

### Agent Orchestration

- LangGraph / CrewAI / AutoGen *(depending on implementation)*

### Code Analysis

- Pylint

### Testing

- Pytest

### Data

- JSON experiment logs

---

## Project Structure

```
refactoring-swarm/
│
├── agents/
│   ├── auditor.py
│   ├── fixer.py
│   └── judge.py
│
├── tools/
│   ├── static_analysis.py
│   ├── file_manager.py
│   ├── sandbox.py
│   └── testing.py
│
├── prompts/
│
├── logs/
│   └── experiment_data.json
│
├── sandbox/
│
├── tests/
│
├── main.py
│
└── README.md
```

---

## How It Works

1. The user provides a Python project.
2. The Auditor inspects the source code.
3. Static analysis identifies quality issues.
4. A refactoring strategy is generated.
5. The Fixer modifies the source files.
6. The Judge executes unit tests.
7. If tests fail, the Fixer receives the error logs and attempts another repair.
8. The process repeats until all tests pass or the maximum number of iterations is reached.

---

## Objectives

The project aims to:

- Automate software maintenance
- Improve Python code quality
- Reduce technical debt
- Preserve software functionality
- Explore collaborative AI agent systems
- Evaluate autonomous software engineering workflows

---

## Evaluation Metrics

The system is evaluated according to three main criteria:

- **Performance**
  - Unit test success
  - Improved static analysis score

- **Technical Robustness**
  - Stable execution
  - Controlled iteration loop
  - Secure sandbox environment

- **Experiment Data**
  - Complete execution logs
  - Valid telemetry data
  - Action history for every agent

---

## Future Improvements

- Support additional programming languages
- Parallel agent execution
- Automatic pull request generation
- Integration with GitHub Actions
- Support for additional static analysis tools
- Human-in-the-loop review mode
- Performance benchmarking dashboard

---

## Team

Developed as part of the Software Engineering (IGL) practical project at

**École Nationale Supérieure d'Informatique (ESI)**
