"""Main refactor agent orchestrating all components."""

import os
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import logging

from .models import (
    SafetyLevel,
    RefactorPlan,
    RefactorResult,
    CodeChange,
    ArchitectureAnalysis
)
from .analyzer import CodeAnalyzer, ArchitectureAnalyzer
from .planner import RefactorPlanner
from .regression import RegressionDetector
from .git_manager import GitWorkflowManager
from .refactorings import RefactoringEngine


class RefactorAgent:
    """Main agent orchestrating microservice refactoring."""
    
    def __init__(
        self,
        repo_path: str,
        config_path: Optional[str] = None,
        log_level: str = "INFO"
    ):
        self.repo_path = Path(repo_path)
        self.config = self._load_config(config_path)
        
        # Set up logging
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.code_analyzer = CodeAnalyzer(repo_path)
        self.architecture_analyzer = ArchitectureAnalyzer(self.code_analyzer)
        self.planner = RefactorPlanner()
        self.regression_detector = RegressionDetector()
        self.git_manager = GitWorkflowManager(repo_path)
        self.refactoring_engine = RefactoringEngine(repo_path)
        
        # State tracking
        self.current_analysis = None
        self.current_plan = None
        self.execution_history = []
        
    def analyze_architecture(
        self,
        service_paths: Optional[Dict[str, str]] = None
    ) -> ArchitectureAnalysis:
        """Analyze the microservice architecture."""
        self.logger.info("Starting architecture analysis")
        
        # Auto-detect services if not provided
        if not service_paths:
            service_paths = self._auto_detect_services()
            self.logger.info(f"Auto-detected {len(service_paths)} services")
        
        # Perform analysis
        analysis = self.architecture_analyzer.analyze_architecture(service_paths)
        self.current_analysis = analysis
        
        # Log summary
        self.logger.info(f"Analysis complete: {len(analysis.services)} services, "
                        f"{len(analysis.dependencies)} dependencies, "
                        f"{len(analysis.code_smells)} code smells detected")
        
        # Save analysis results
        self._save_analysis(analysis)
        
        return analysis
    
    def create_refactoring_plan(
        self,
        target_architecture: str = "microservices",
        safety_level: SafetyLevel = SafetyLevel.HIGH,
        priorities: Optional[List[str]] = None,
        analysis: Optional[ArchitectureAnalysis] = None
    ) -> RefactorPlan:
        """Create a refactoring plan based on analysis."""
        if not analysis and not self.current_analysis:
            raise ValueError("No analysis available. Run analyze_architecture first.")
        
        analysis = analysis or self.current_analysis
        
        self.logger.info(f"Creating refactoring plan for {target_architecture} architecture")
        
        # Create plan
        plan = self.planner.create_refactoring_plan(
            analysis=analysis,
            target_architecture=target_architecture,
            safety_level=safety_level,
            priorities=priorities
        )
        
        self.current_plan = plan
        
        # Log plan summary
        self.logger.info(f"Plan created: {len(plan.steps)} steps, "
                        f"{plan.total_effort} hours estimated effort")
        
        # Save plan
        self._save_plan(plan)
        
        return plan
    
    def execute_refactoring(
        self,
        plan: Optional[RefactorPlan] = None,
        auto_commit: bool = True,
        dry_run: bool = False,
        interactive: bool = False
    ) -> List[RefactorResult]:
        """Execute the refactoring plan."""
        if not plan and not self.current_plan:
            raise ValueError("No plan available. Create a refactoring plan first.")
        
        plan = plan or self.current_plan
        results = []
        
        self.logger.info(f"Starting refactoring execution (dry_run={dry_run})")
        
        # Create workflow if using git
        workflow = None
        if auto_commit and not dry_run:
            workflow = self.git_manager.create_refactoring_workflow(plan.id)
            self.logger.info(f"Created feature branch: {workflow['feature_branch']}")
        
        # Execute each step
        for i, step in enumerate(plan.steps):
            self.logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step.description}")
            
            if interactive:
                response = input(f"Execute step '{step.description}'? (y/n/skip): ")
                if response.lower() == 'skip':
                    self.logger.info("Skipping step")
                    continue
                elif response.lower() != 'y':
                    self.logger.info("Aborting execution")
                    break
            
            # Execute step
            result = self._execute_step(step, workflow, dry_run, auto_commit)
            results.append(result)
            
            # Check for failures
            if not result.success:
                self.logger.error(f"Step failed: {result.error}")
                if not interactive or input("Continue despite failure? (y/n): ").lower() != 'y':
                    break
            
            # Log progress
            self._log_progress(i + 1, len(plan.steps), result)
        
        # Generate final report
        if workflow and auto_commit and not dry_run:
            pr_description = self.git_manager.create_pull_request_description(workflow, results)
            self._save_pr_description(workflow['plan_id'], pr_description)
            self.logger.info("Generated pull request description")
        
        # Save execution results
        self._save_execution_results(plan.id, results)
        
        return results
    
    def _execute_step(
        self,
        step,
        workflow: Optional[Dict[str, Any]],
        dry_run: bool,
        auto_commit: bool
    ) -> RefactorResult:
        """Execute a single refactoring step."""
        try:
            # Simulate changes for now (in real implementation, would apply actual refactoring)
            changes = self._apply_refactoring(step, dry_run)
            
            # Detect regression risks
            risks = self.regression_detector.analyze_changes(changes, {
                "step": step,
                "analysis": self.current_analysis
            })
            
            # Generate regression report
            if risks:
                report = self.regression_detector.generate_regression_report(risks, step)
                self.logger.warning(f"Regression risks detected:\n{report}")
            
            # Commit changes if requested
            if auto_commit and workflow and not dry_run and changes:
                result = self.git_manager.execute_step_with_commit(
                    step, changes, risks, workflow
                )
            else:
                result = RefactorResult(
                    step_id=step.id,
                    success=True,
                    changes=changes,
                    regression_risks=risks
                )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing step: {str(e)}")
            return RefactorResult(
                step_id=step.id,
                success=False,
                changes=[],
                regression_risks=[],
                error=str(e)
            )
    
    def _apply_refactoring(self, step, dry_run: bool) -> List[CodeChange]:
        """Apply refactoring changes using the refactoring engine."""
        if dry_run:
            # In dry run mode, simulate changes
            changes = []
            for file_path in step.target_files[:3]:  # Limit for simulation
                changes.append(CodeChange(
                    file_path=file_path,
                    change_type="modify",
                    diff=f"--- a/{file_path}\n+++ b/{file_path}\n@@ -1,3 +1,3 @@\n-old code\n+new refactored code\n",
                    line_changes={"added": 10, "removed": 5},
                    semantic_changes=[f"Refactored according to {step.type.value}"]
                ))
            return changes
        
        # Use the refactoring engine to apply actual changes
        return self.refactoring_engine.apply_refactoring(step)
    
    def _auto_detect_services(self) -> Dict[str, str]:
        """Auto-detect microservices in the repository."""
        services = {}
        
        # Look for common microservice patterns
        patterns = [
            "services/*/",
            "microservices/*/",
            "apps/*/",
            "src/services/*/",
            "*-service/",
            "*-api/",
            "*-worker/"
        ]
        
        for pattern in patterns:
            for path in self.repo_path.glob(pattern):
                if path.is_dir() and not path.name.startswith('.'):
                    # Check if it looks like a service (has code files)
                    if any(path.glob("**/*.py")) or any(path.glob("**/*.js")):
                        service_name = path.name.replace('-service', '').replace('-api', '')
                        services[service_name] = str(path.relative_to(self.repo_path))
        
        # Also check for docker-compose.yml to identify services
        compose_file = self.repo_path / "docker-compose.yml"
        if compose_file.exists():
            # Would parse docker-compose.yml to find services
            pass
        
        return services
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file."""
        default_config = {
            "safety_level": "high",
            "auto_detect_services": True,
            "commit_style": "conventional",
            "max_changes_per_commit": 20,
            "regression_threshold": 0.7
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def _save_analysis(self, analysis: ArchitectureAnalysis) -> None:
        """Save analysis results to file."""
        output_dir = self.repo_path / ".refactor" / "analysis"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file = output_dir / f"analysis-{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(analysis.dict(), f, indent=2, default=str)
        
        self.logger.info(f"Analysis saved to {output_file}")
    
    def _save_plan(self, plan: RefactorPlan) -> None:
        """Save refactoring plan to file."""
        output_dir = self.repo_path / ".refactor" / "plans"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"plan-{plan.id}.json"
        
        with open(output_file, 'w') as f:
            json.dump(plan.dict(), f, indent=2, default=str)
        
        self.logger.info(f"Plan saved to {output_file}")
    
    def _save_execution_results(self, plan_id: str, results: List[RefactorResult]) -> None:
        """Save execution results to file."""
        output_dir = self.repo_path / ".refactor" / "results"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file = output_dir / f"results-{plan_id}-{timestamp}.json"
        
        results_data = [r.dict() for r in results]
        
        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        self.logger.info(f"Results saved to {output_file}")
    
    def _save_pr_description(self, plan_id: str, description: str) -> None:
        """Save pull request description to file."""
        output_dir = self.repo_path / ".refactor" / "pr"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"pr-{plan_id}.md"
        
        with open(output_file, 'w') as f:
            f.write(description)
        
        self.logger.info(f"PR description saved to {output_file}")
    
    def _log_progress(self, current: int, total: int, result: RefactorResult) -> None:
        """Log execution progress."""
        percentage = (current / total) * 100
        status = "✓" if result.success else "✗"
        
        self.logger.info(f"Progress: {current}/{total} ({percentage:.1f}%) {status}")
        
        if result.regression_risks:
            high_risks = [r for r in result.regression_risks if r.severity in ["critical", "high"]]
            if high_risks:
                self.logger.warning(f"High-risk regressions: {len(high_risks)}")
    
    def generate_report(self) -> str:
        """Generate a comprehensive refactoring report."""
        report = "# Microservice Refactoring Report\n\n"
        
        if self.current_analysis:
            report += "## Architecture Analysis\n\n"
            report += f"- Services analyzed: {len(self.current_analysis.services)}\n"
            report += f"- Dependencies found: {len(self.current_analysis.dependencies)}\n"
            report += f"- Code smells detected: {len(self.current_analysis.code_smells)}\n"
            report += f"- Average complexity: {self.current_analysis.metrics.get('avg_service_complexity', 0):.1f}\n\n"
            
            if self.current_analysis.recommendations:
                report += "### Recommendations\n\n"
                for rec in self.current_analysis.recommendations:
                    report += f"- {rec}\n"
                report += "\n"
        
        if self.current_plan:
            report += "## Refactoring Plan\n\n"
            report += f"- Target architecture: {self.current_plan.target_architecture}\n"
            report += f"- Safety level: {self.current_plan.safety_level.value}\n"
            report += f"- Total steps: {len(self.current_plan.steps)}\n"
            report += f"- Estimated effort: {self.current_plan.total_effort} hours\n\n"
            
            report += "### Steps Overview\n\n"
            for i, step in enumerate(self.current_plan.steps[:10]):
                report += f"{i+1}. {step.description} ({step.risk_level} risk)\n"
            
            if len(self.current_plan.steps) > 10:
                report += f"... and {len(self.current_plan.steps) - 10} more steps\n"
        
        return report