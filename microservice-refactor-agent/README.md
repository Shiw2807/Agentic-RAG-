# Microservice Refactor Agent

An intelligent agent that helps refactor legacy microservices and automates multi-commit Git workflows. The agent analyzes architectural changes, suggests safe migration steps, reviews diffs for regressions, and generates semantically meaningful commit messages.

## Features

- **Architecture Analysis**: Analyzes legacy microservice code to understand dependencies and structure
- **Migration Planning**: Suggests safe, incremental refactoring steps
- **Regression Detection**: Reviews code changes to identify potential regressions
- **Automated Git Workflow**: Creates multi-commit workflows with meaningful commit messages
- **Dependency Tracking**: Tracks and manages service dependencies during refactoring

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from refactor_agent import RefactorAgent

# Initialize the agent
agent = RefactorAgent(repo_path="./legacy-service")

# Analyze the microservice
analysis = agent.analyze_architecture()

# Generate refactoring plan
plan = agent.create_refactoring_plan(
    target_architecture="domain-driven",
    safety_level="high"
)

# Execute refactoring with automated commits
agent.execute_refactoring(plan, auto_commit=True)
```

## Architecture

The agent consists of several key components:

1. **Code Analyzer**: Parses and analyzes code structure
2. **Dependency Mapper**: Maps service dependencies
3. **Refactor Planner**: Creates safe migration strategies
4. **Regression Detector**: Identifies potential issues in changes
5. **Git Workflow Manager**: Handles multi-commit workflows
6. **Commit Message Generator**: Creates semantic commit messages

## Example Workflow

1. Analyze legacy microservice structure
2. Identify anti-patterns and improvement opportunities
3. Generate incremental refactoring plan
4. Execute changes with automatic regression checks
5. Create semantic commits for each logical change
6. Generate migration documentation