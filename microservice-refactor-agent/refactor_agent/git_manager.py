"""Git workflow management and commit message generation."""

import os
import re
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import git
from datetime import datetime
import json

from .models import (
    CommitInfo,
    CodeChange,
    RefactorStep,
    RefactorResult,
    RegressionRisk
)


class CommitMessageGenerator:
    """Generates semantic commit messages based on changes."""
    
    def __init__(self):
        self.type_patterns = {
            "feat": ["add", "implement", "create", "introduce"],
            "fix": ["fix", "resolve", "correct", "repair"],
            "refactor": ["refactor", "restructure", "reorganize", "optimize"],
            "test": ["test", "testing", "coverage", "spec"],
            "docs": ["document", "documentation", "readme", "comment"],
            "style": ["format", "style", "lint", "prettier"],
            "perf": ["performance", "optimize", "speed", "efficiency"],
            "chore": ["update", "upgrade", "configure", "setup"],
            "build": ["build", "compile", "bundle", "package"],
            "ci": ["ci", "pipeline", "workflow", "automation"]
        }
        
    def generate_commit_message(
        self,
        step: RefactorStep,
        changes: List[CodeChange],
        risks: List[RegressionRisk]
    ) -> CommitInfo:
        """Generate a semantic commit message for the changes."""
        # Determine commit type
        commit_type = self._determine_commit_type(step, changes)
        
        # Determine scope
        scope = self._determine_scope(changes)
        
        # Generate message
        message = self._generate_message(step, changes, commit_type, scope)
        
        # Generate body
        body = self._generate_body(step, changes, risks)
        
        # Generate footer
        footer = self._generate_footer(step, risks)
        
        # Check for breaking changes
        breaking_change = self._is_breaking_change(risks)
        
        return CommitInfo(
            message=message,
            type=commit_type,
            scope=scope,
            breaking_change=breaking_change,
            files=[c.file_path for c in changes],
            body=body,
            footer=footer
        )
    
    def _determine_commit_type(self, step: RefactorStep, changes: List[CodeChange]) -> str:
        """Determine the commit type based on the refactoring step."""
        step_type = step.type.value.lower()
        
        # Check step description for type indicators
        description_lower = step.description.lower()
        for commit_type, keywords in self.type_patterns.items():
            if any(keyword in description_lower for keyword in keywords):
                return commit_type
        
        # Map refactor types to commit types
        type_mapping = {
            "extract_service": "refactor",
            "merge_services": "refactor",
            "split_service": "refactor",
            "rename": "refactor",
            "restructure": "refactor",
            "dependency_injection": "refactor",
            "interface_extraction": "refactor",
            "database_migration": "feat",
            "api_versioning": "feat",
            "remove_dead_code": "chore"
        }
        
        return type_mapping.get(step_type, "refactor")
    
    def _determine_scope(self, changes: List[CodeChange]) -> Optional[str]:
        """Determine the scope of changes."""
        if not changes:
            return None
        
        # Find common directory or service name
        paths = [Path(c.file_path) for c in changes]
        
        # If all files are in the same directory
        directories = set(p.parent for p in paths)
        if len(directories) == 1:
            dir_name = directories.pop().name
            if dir_name not in [".", "", "src", "lib"]:
                return dir_name
        
        # Look for service name patterns
        service_pattern = re.compile(r'(service|api|worker|gateway)[-_]?(\w+)')
        for path in paths:
            match = service_pattern.search(str(path))
            if match:
                return match.group(0).replace('_', '-')
        
        # Use the most common parent directory
        if len(paths) > 1:
            common_parts = set()
            for path in paths:
                parts = path.parts
                if len(parts) > 1:
                    common_parts.add(parts[0])
            
            if len(common_parts) == 1:
                return common_parts.pop()
        
        return None
    
    def _generate_message(
        self,
        step: RefactorStep,
        changes: List[CodeChange],
        commit_type: str,
        scope: Optional[str]
    ) -> str:
        """Generate the main commit message."""
        # Use custom message if provided
        if step.commit_message:
            return step.commit_message
        
        # Extract key action from description
        description = step.description.lower()
        
        # Remove common prefixes
        prefixes = ["implement", "create", "add", "update", "refactor", "fix"]
        for prefix in prefixes:
            if description.startswith(prefix + " "):
                description = description[len(prefix) + 1:]
                break
        
        # Format message
        if scope:
            message = f"{commit_type}({scope}): {description}"
        else:
            message = f"{commit_type}: {description}"
        
        # Ensure message is not too long
        if len(message) > 72:
            # Try to shorten
            words = description.split()
            while len(f"{commit_type}({scope}): {' '.join(words)}") > 72 and len(words) > 3:
                words.pop()
            message = f"{commit_type}({scope}): {' '.join(words)}..." if scope else f"{commit_type}: {' '.join(words)}..."
        
        return message
    
    def _generate_body(
        self,
        step: RefactorStep,
        changes: List[CodeChange],
        risks: List[RegressionRisk]
    ) -> Optional[str]:
        """Generate the commit body with details."""
        body_parts = []
        
        # Add step details
        if step.description != step.commit_message:
            body_parts.append(f"- {step.description}")
        
        # Summarize changes
        change_summary = self._summarize_changes(changes)
        if change_summary:
            body_parts.append("\nChanges:")
            body_parts.extend(f"- {item}" for item in change_summary)
        
        # Add validation steps
        if step.validation_steps:
            body_parts.append("\nValidation:")
            body_parts.extend(f"- {step}" for step in step.validation_steps[:3])
        
        # Add high-risk warnings
        high_risks = [r for r in risks if r.severity in ["critical", "high"]]
        if high_risks:
            body_parts.append("\nRisks addressed:")
            for risk in high_risks[:3]:
                body_parts.append(f"- {risk.type}: {risk.description}")
        
        return "\n".join(body_parts) if body_parts else None
    
    def _summarize_changes(self, changes: List[CodeChange]) -> List[str]:
        """Summarize the changes made."""
        summary = []
        
        # Count changes by type
        by_type = {}
        for change in changes:
            by_type.setdefault(change.change_type, []).append(change)
        
        # Summarize each type
        for change_type, type_changes in by_type.items():
            if change_type == "modify":
                total_added = sum(c.line_changes.get("added", 0) for c in type_changes)
                total_removed = sum(c.line_changes.get("removed", 0) for c in type_changes)
                summary.append(f"Modified {len(type_changes)} files (+{total_added}/-{total_removed} lines)")
            elif change_type == "add":
                summary.append(f"Added {len(type_changes)} new files")
            elif change_type == "delete":
                summary.append(f"Removed {len(type_changes)} files")
            elif change_type == "rename":
                summary.append(f"Renamed {len(type_changes)} files")
        
        # Add semantic changes if available
        all_semantic = []
        for change in changes:
            all_semantic.extend(change.semantic_changes)
        
        if all_semantic:
            # Get unique semantic changes
            unique_semantic = list(set(all_semantic))[:3]
            summary.extend(unique_semantic)
        
        return summary
    
    def _generate_footer(self, step: RefactorStep, risks: List[RegressionRisk]) -> Optional[str]:
        """Generate commit footer with references and breaking changes."""
        footer_parts = []
        
        # Add breaking change notice
        breaking_risks = [r for r in risks if r.type == "api_change" and r.severity in ["critical", "high"]]
        if breaking_risks:
            footer_parts.append("BREAKING CHANGE: API modifications may affect existing clients")
            for risk in breaking_risks[:2]:
                footer_parts.append(f"  - {risk.description}")
        
        # Add references
        if step.id:
            footer_parts.append(f"\nRef: {step.id}")
        
        # Add rollback info if high risk
        if step.risk_level == "high" and step.rollback_strategy:
            footer_parts.append(f"\nRollback: {step.rollback_strategy}")
        
        return "\n".join(footer_parts) if footer_parts else None
    
    def _is_breaking_change(self, risks: List[RegressionRisk]) -> bool:
        """Determine if changes include breaking changes."""
        return any(
            risk.type == "api_change" and risk.severity in ["critical", "high"]
            for risk in risks
        )
    
    def format_conventional_commit(self, commit_info: CommitInfo) -> str:
        """Format commit info as a conventional commit message."""
        # Header
        header = commit_info.message
        
        # Full message
        parts = [header]
        
        if commit_info.body:
            parts.append("")  # Empty line
            parts.append(commit_info.body)
        
        if commit_info.footer:
            parts.append("")  # Empty line
            parts.append(commit_info.footer)
        
        return "\n".join(parts)


class GitWorkflowManager:
    """Manages Git operations and multi-commit workflows."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        try:
            self.repo = git.Repo(repo_path)
        except git.InvalidGitRepositoryError:
            # Initialize repo if it doesn't exist
            self.repo = git.Repo.init(repo_path)
        
        self.commit_generator = CommitMessageGenerator()
        
    def create_feature_branch(self, branch_name: str, base_branch: str = "main") -> str:
        """Create a new feature branch."""
        # Ensure we're on the base branch
        try:
            self.repo.git.checkout(base_branch)
        except git.GitCommandError:
            # Base branch doesn't exist, use current branch
            base_branch = self.repo.active_branch.name
        
        # Create and checkout new branch
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        full_branch_name = f"refactor/{branch_name}-{timestamp}"
        
        self.repo.git.checkout("-b", full_branch_name)
        
        return full_branch_name
    
    def stage_changes(self, files: List[str]) -> List[str]:
        """Stage files for commit."""
        staged = []
        
        for file_path in files:
            try:
                self.repo.index.add([file_path])
                staged.append(file_path)
            except Exception as e:
                print(f"Failed to stage {file_path}: {e}")
        
        return staged
    
    def commit_changes(
        self,
        commit_info: CommitInfo,
        verify: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """Create a commit with the given information."""
        try:
            # Stage files
            if commit_info.files:
                staged = self.stage_changes(commit_info.files)
                if not staged:
                    return False, "No files could be staged"
            
            # Format commit message
            message = self.commit_generator.format_conventional_commit(commit_info)
            
            # Create commit
            commit = self.repo.index.commit(message)
            
            # Verify if requested
            if verify:
                # Run any pre-configured hooks or checks
                if not self._verify_commit(commit):
                    # Rollback commit
                    self.repo.git.reset("--soft", "HEAD~1")
                    return False, "Commit verification failed"
            
            return True, commit.hexsha
            
        except Exception as e:
            return False, str(e)
    
    def create_refactoring_workflow(
        self,
        plan_id: str,
        base_branch: str = "main"
    ) -> Dict[str, Any]:
        """Create a complete refactoring workflow."""
        workflow = {
            "plan_id": plan_id,
            "base_branch": base_branch,
            "feature_branch": None,
            "commits": [],
            "status": "initialized",
            "created_at": datetime.now().isoformat()
        }
        
        # Create feature branch
        branch_name = f"refactor-{plan_id[:8]}"
        workflow["feature_branch"] = self.create_feature_branch(branch_name, base_branch)
        
        # Save workflow metadata
        self._save_workflow_metadata(workflow)
        
        return workflow
    
    def execute_step_with_commit(
        self,
        step: RefactorStep,
        changes: List[CodeChange],
        risks: List[RegressionRisk],
        workflow: Dict[str, Any]
    ) -> RefactorResult:
        """Execute a refactoring step and commit changes."""
        # Generate commit info
        commit_info = self.commit_generator.generate_commit_message(step, changes, risks)
        
        # Create commit
        success, commit_id = self.commit_changes(commit_info)
        
        if success:
            # Update workflow
            workflow["commits"].append({
                "step_id": step.id,
                "commit_id": commit_id,
                "timestamp": datetime.now().isoformat(),
                "message": commit_info.message
            })
            self._save_workflow_metadata(workflow)
            
            return RefactorResult(
                step_id=step.id,
                success=True,
                changes=changes,
                regression_risks=risks,
                commit_info=commit_info
            )
        else:
            return RefactorResult(
                step_id=step.id,
                success=False,
                changes=changes,
                regression_risks=risks,
                error=f"Failed to commit: {commit_id}"
            )
    
    def create_pull_request_description(
        self,
        workflow: Dict[str, Any],
        results: List[RefactorResult]
    ) -> str:
        """Generate a pull request description."""
        pr_description = f"# Refactoring Plan: {workflow['plan_id']}\n\n"
        
        pr_description += "## Summary\n\n"
        pr_description += f"This PR implements an automated refactoring plan with {len(results)} steps.\n\n"
        
        pr_description += "## Changes\n\n"
        for result in results:
            if result.commit_info:
                pr_description += f"- **{result.commit_info.message}**\n"
                if result.commit_info.body:
                    body_lines = result.commit_info.body.split('\n')
                    for line in body_lines[:3]:
                        if line.strip():
                            pr_description += f"  {line}\n"
        
        pr_description += "\n## Risk Assessment\n\n"
        all_risks = []
        for result in results:
            all_risks.extend(result.regression_risks)
        
        high_risks = [r for r in all_risks if r.severity in ["critical", "high"]]
        if high_risks:
            pr_description += "### High Priority Risks\n\n"
            for risk in high_risks[:5]:
                pr_description += f"- **{risk.type}**: {risk.description}\n"
                if risk.mitigation:
                    pr_description += f"  - Mitigation: {risk.mitigation}\n"
        
        pr_description += "\n## Testing\n\n"
        pr_description += "The following tests should be performed:\n\n"
        
        # Collect unique test suggestions
        test_suggestions = set()
        for result in results:
            for risk in result.regression_risks:
                test_suggestions.update(risk.test_suggestions)
        
        for test in list(test_suggestions)[:10]:
            pr_description += f"- [ ] {test}\n"
        
        pr_description += "\n## Rollback Plan\n\n"
        pr_description += "If issues are discovered, rollback can be performed by:\n"
        pr_description += "1. Reverting commits in reverse order\n"
        pr_description += "2. Restoring from backup branch\n"
        pr_description += "3. Running rollback scripts for database changes\n"
        
        return pr_description
    
    def _verify_commit(self, commit: git.Commit) -> bool:
        """Verify a commit meets quality standards."""
        # Check commit message format
        message = commit.message
        if not re.match(r'^(feat|fix|docs|style|refactor|test|chore|perf|ci|build)(\(.+\))?: .+', message):
            return False
        
        # Check file changes
        stats = commit.stats.total
        if stats['lines'] > 1000:  # Too many changes in one commit
            return False
        
        return True
    
    def _save_workflow_metadata(self, workflow: Dict[str, Any]) -> None:
        """Save workflow metadata to file."""
        metadata_dir = self.repo_path / ".refactor"
        metadata_dir.mkdir(exist_ok=True)
        
        metadata_file = metadata_dir / f"workflow-{workflow['plan_id']}.json"
        with open(metadata_file, 'w') as f:
            json.dump(workflow, f, indent=2)
    
    def rollback_to_commit(self, commit_id: str) -> Tuple[bool, str]:
        """Rollback to a specific commit."""
        try:
            self.repo.git.reset("--hard", commit_id)
            return True, f"Rolled back to commit {commit_id}"
        except Exception as e:
            return False, f"Rollback failed: {str(e)}"
    
    def create_backup_branch(self, branch_name: str) -> str:
        """Create a backup branch before risky operations."""
        backup_name = f"backup/{branch_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.repo.git.branch(backup_name)
        return backup_name
    
    def analyze_commit_impact(self, commit_id: str) -> Dict[str, Any]:
        """Analyze the impact of a commit."""
        commit = self.repo.commit(commit_id)
        
        impact = {
            "commit_id": commit_id,
            "author": str(commit.author),
            "timestamp": commit.committed_datetime.isoformat(),
            "message": commit.message,
            "files_changed": len(commit.stats.files),
            "lines_added": commit.stats.total['insertions'],
            "lines_removed": commit.stats.total['deletions'],
            "affected_files": list(commit.stats.files.keys())
        }
        
        return impact