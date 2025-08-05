"""Tests for Git workflow management."""

import pytest
import tempfile
from pathlib import Path
import git

from refactor_agent.git_manager import CommitMessageGenerator, GitWorkflowManager
from refactor_agent.models import (
    RefactorStep, RefactorType, CodeChange, RegressionRisk, CommitInfo
)


class TestCommitMessageGenerator:
    """Test cases for CommitMessageGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Create a commit message generator."""
        return CommitMessageGenerator()
    
    @pytest.fixture
    def sample_step(self):
        """Create a sample refactor step."""
        return RefactorStep(
            id="step-123",
            type=RefactorType.API_VERSIONING,
            description="Add API versioning to user service",
            target_files=["api/users.py", "api/routes.py"],
            estimated_effort=4,
            risk_level="medium"
        )
    
    @pytest.fixture
    def sample_changes(self):
        """Create sample code changes."""
        return [
            CodeChange(
                file_path="api/users.py",
                change_type="modify",
                diff="...",
                line_changes={"added": 10, "removed": 5},
                semantic_changes=["Added version prefix to endpoints"]
            ),
            CodeChange(
                file_path="api/routes.py",
                change_type="modify",
                diff="...",
                line_changes={"added": 5, "removed": 2},
                semantic_changes=["Updated route definitions"]
            )
        ]
    
    def test_generate_commit_message(self, generator, sample_step, sample_changes):
        """Test commit message generation."""
        risks = [
            RegressionRisk(
                type="api_change",
                severity="high",
                description="API endpoints modified",
                affected_components=["api/users.py"]
            )
        ]
        
        commit_info = generator.generate_commit_message(sample_step, sample_changes, risks)
        
        assert commit_info.type == "feat"
        assert commit_info.scope == "api"
        assert "versioning" in commit_info.message.lower()
        assert commit_info.breaking_change is True
        assert len(commit_info.files) == 2
    
    def test_determine_commit_type(self, generator, sample_step, sample_changes):
        """Test commit type determination."""
        # Test different step types
        test_cases = [
            (RefactorType.DATABASE_MIGRATION, "feat"),
            (RefactorType.REMOVE_DEAD_CODE, "chore"),
            (RefactorType.RESTRUCTURE, "refactor"),
            (RefactorType.INTERFACE_EXTRACTION, "refactor")
        ]
        
        for refactor_type, expected_type in test_cases:
            sample_step.type = refactor_type
            commit_type = generator._determine_commit_type(sample_step, sample_changes)
            assert commit_type == expected_type
    
    def test_format_conventional_commit(self, generator):
        """Test conventional commit formatting."""
        commit_info = CommitInfo(
            message="feat(auth): add OAuth2 support",
            type="feat",
            scope="auth",
            breaking_change=True,
            files=["auth/oauth.py"],
            body="- Implemented OAuth2 flow\n- Added token validation",
            footer="BREAKING CHANGE: Auth API endpoints changed"
        )
        
        formatted = generator.format_conventional_commit(commit_info)
        
        assert formatted.startswith("feat(auth): add OAuth2 support")
        assert "Implemented OAuth2 flow" in formatted
        assert "BREAKING CHANGE:" in formatted
    
    def test_long_message_truncation(self, generator, sample_changes):
        """Test that long messages are truncated properly."""
        long_step = RefactorStep(
            id="step-long",
            type=RefactorType.RESTRUCTURE,
            description="This is a very long description that exceeds the conventional commit message length limit and should be truncated",
            target_files=["file.py"],
            estimated_effort=1,
            risk_level="low"
        )
        
        commit_info = generator.generate_commit_message(long_step, sample_changes, [])
        
        assert len(commit_info.message) <= 72
        assert commit_info.message.endswith("...")


class TestGitWorkflowManager:
    """Test cases for GitWorkflowManager."""
    
    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = git.Repo.init(tmpdir)
            
            # Create initial commit
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# Test file\n")
            repo.index.add(["test.py"])
            repo.index.commit("Initial commit")
            
            yield tmpdir, repo
    
    @pytest.fixture
    def git_manager(self, temp_git_repo):
        """Create a git workflow manager."""
        tmpdir, _ = temp_git_repo
        return GitWorkflowManager(tmpdir)
    
    def test_create_feature_branch(self, git_manager):
        """Test feature branch creation."""
        branch_name = git_manager.create_feature_branch("test-feature")
        
        assert branch_name.startswith("refactor/test-feature-")
        assert git_manager.repo.active_branch.name == branch_name
    
    def test_stage_and_commit(self, git_manager, temp_git_repo):
        """Test staging and committing changes."""
        tmpdir, _ = temp_git_repo
        
        # Create a new file
        new_file = Path(tmpdir) / "new_feature.py"
        new_file.write_text("def new_feature():\n    pass\n")
        
        # Create commit info
        commit_info = CommitInfo(
            message="feat: add new feature",
            type="feat",
            scope=None,
            breaking_change=False,
            files=["new_feature.py"],
            body="Added new feature implementation"
        )
        
        # Commit changes
        success, commit_id = git_manager.commit_changes(commit_info, verify=False)
        
        assert success is True
        assert commit_id is not None
        
        # Verify commit
        commit = git_manager.repo.commit(commit_id)
        assert "feat: add new feature" in commit.message
        assert "new_feature.py" in commit.stats.files
    
    def test_create_refactoring_workflow(self, git_manager):
        """Test refactoring workflow creation."""
        workflow = git_manager.create_refactoring_workflow("plan-123")
        
        assert workflow["plan_id"] == "plan-123"
        assert workflow["feature_branch"] is not None
        assert workflow["status"] == "initialized"
        assert len(workflow["commits"]) == 0
    
    def test_execute_step_with_commit(self, git_manager, temp_git_repo):
        """Test executing a step with commit."""
        tmpdir, _ = temp_git_repo
        
        # Create workflow
        workflow = git_manager.create_refactoring_workflow("plan-456")
        
        # Create step
        step = RefactorStep(
            id="step-1",
            type=RefactorType.RESTRUCTURE,
            description="Refactor module structure",
            target_files=["module.py"],
            estimated_effort=2,
            risk_level="low"
        )
        
        # Create file change
        module_file = Path(tmpdir) / "module.py"
        module_file.write_text("# Refactored module\n")
        
        changes = [
            CodeChange(
                file_path="module.py",
                change_type="add",
                diff="...",
                line_changes={"added": 1, "removed": 0},
                semantic_changes=["Created new module"]
            )
        ]
        
        # Execute step
        result = git_manager.execute_step_with_commit(step, changes, [], workflow)
        
        assert result.success is True
        assert len(workflow["commits"]) == 1
        assert workflow["commits"][0]["step_id"] == "step-1"
    
    def test_create_pull_request_description(self, git_manager):
        """Test PR description generation."""
        workflow = {
            "plan_id": "plan-789",
            "commits": [
                {
                    "step_id": "step-1",
                    "commit_id": "abc123",
                    "message": "refactor: extract user service"
                }
            ]
        }
        
        results = [
            RefactorResult(
                step_id="step-1",
                success=True,
                changes=[],
                regression_risks=[
                    RegressionRisk(
                        type="api_change",
                        severity="high",
                        description="API endpoints changed",
                        affected_components=["api/users.py"],
                        test_suggestions=["Test all API endpoints"]
                    )
                ],
                commit_info=CommitInfo(
                    message="refactor: extract user service",
                    type="refactor",
                    body="- Extracted user logic to separate service"
                )
            )
        ]
        
        pr_description = git_manager.create_pull_request_description(workflow, results)
        
        assert "Refactoring Plan: plan-789" in pr_description
        assert "extract user service" in pr_description
        assert "API endpoints changed" in pr_description
        assert "Test all API endpoints" in pr_description