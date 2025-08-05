"""Regression detection and risk analysis components."""

import re
import ast
from typing import List, Dict, Any, Set, Tuple, Optional
from difflib import unified_diff
import json

from .models import (
    RegressionRisk,
    CodeChange,
    RefactorStep
)


class RegressionDetector:
    """Detects potential regressions in code changes."""
    
    def __init__(self):
        self.api_patterns = self._compile_api_patterns()
        self.behavior_patterns = self._compile_behavior_patterns()
        
    def analyze_changes(self, changes: List[CodeChange], context: Dict[str, Any]) -> List[RegressionRisk]:
        """Analyze code changes for potential regressions."""
        risks = []
        
        for change in changes:
            # Analyze different types of changes
            if change.change_type in ["modify", "delete"]:
                risks.extend(self._analyze_modification(change, context))
            elif change.change_type == "add":
                risks.extend(self._analyze_addition(change, context))
            elif change.change_type == "rename":
                risks.extend(self._analyze_rename(change, context))
        
        # Analyze cross-file impacts
        risks.extend(self._analyze_cross_file_impacts(changes, context))
        
        # Deduplicate and prioritize risks
        risks = self._deduplicate_risks(risks)
        
        return sorted(risks, key=lambda r: self._risk_priority(r), reverse=True)
    
    def _analyze_modification(self, change: CodeChange, context: Dict[str, Any]) -> List[RegressionRisk]:
        """Analyze modifications for regressions."""
        risks = []
        
        # Parse the diff
        diff_lines = change.diff.split('\n')
        removed_lines = [l[1:] for l in diff_lines if l.startswith('-') and not l.startswith('---')]
        added_lines = [l[1:] for l in diff_lines if l.startswith('+') and not l.startswith('+++')]
        
        # Check for API changes
        api_risks = self._check_api_changes(removed_lines, added_lines, change.file_path)
        risks.extend(api_risks)
        
        # Check for behavior changes
        behavior_risks = self._check_behavior_changes(removed_lines, added_lines, change.file_path)
        risks.extend(behavior_risks)
        
        # Check for performance impacts
        perf_risks = self._check_performance_impacts(removed_lines, added_lines, change.file_path)
        risks.extend(perf_risks)
        
        # Check for security impacts
        security_risks = self._check_security_impacts(removed_lines, added_lines, change.file_path)
        risks.extend(security_risks)
        
        return risks
    
    def _check_api_changes(self, removed: List[str], added: List[str], file_path: str) -> List[RegressionRisk]:
        """Check for API breaking changes."""
        risks = []
        
        # Check for removed endpoints
        for pattern_name, pattern in self.api_patterns.items():
            removed_matches = []
            for line in removed:
                if pattern.search(line):
                    removed_matches.append(line.strip())
            
            if removed_matches:
                # Check if they were replaced
                added_matches = [l for l in added if pattern.search(l)]
                
                if not added_matches:
                    risks.append(RegressionRisk(
                        type="api_change",
                        severity="critical",
                        description=f"API endpoint removed: {removed_matches[0]}",
                        affected_components=[file_path],
                        mitigation="Add deprecation notice and migration path",
                        test_suggestions=[
                            "Test all client applications",
                            "Verify API backward compatibility",
                            "Check API documentation updates"
                        ]
                    ))
                else:
                    # Endpoint modified
                    risks.append(RegressionRisk(
                        type="api_change",
                        severity="high",
                        description=f"API endpoint modified in {file_path}",
                        affected_components=[file_path],
                        mitigation="Ensure backward compatibility or version the API",
                        test_suggestions=[
                            "Test with existing API clients",
                            "Verify request/response format compatibility",
                            "Update API tests"
                        ]
                    ))
        
        # Check for parameter changes
        param_changes = self._detect_parameter_changes(removed, added)
        for param_change in param_changes:
            risks.append(RegressionRisk(
                type="api_change",
                severity="high" if param_change["removed"] else "medium",
                description=f"Function parameters changed: {param_change['function']}",
                affected_components=[file_path],
                mitigation="Update all callers or maintain backward compatibility",
                test_suggestions=[
                    f"Test all calls to {param_change['function']}",
                    "Verify parameter validation",
                    "Check default parameter values"
                ]
            ))
        
        return risks
    
    def _check_behavior_changes(self, removed: List[str], added: List[str], file_path: str) -> List[RegressionRisk]:
        """Check for behavioral changes."""
        risks = []
        
        # Check for changed conditionals
        removed_conditions = [l for l in removed if any(kw in l for kw in ['if ', 'elif ', 'while ', 'for '])]
        added_conditions = [l for l in added if any(kw in l for kw in ['if ', 'elif ', 'while ', 'for '])]
        
        if removed_conditions and added_conditions:
            risks.append(RegressionRisk(
                type="behavior_change",
                severity="high",
                description="Control flow logic modified",
                affected_components=[file_path],
                mitigation="Ensure all edge cases are covered",
                test_suggestions=[
                    "Test all conditional branches",
                    "Verify edge cases",
                    "Check boundary conditions"
                ]
            ))
        
        # Check for changed return values
        removed_returns = [l for l in removed if 'return ' in l]
        added_returns = [l for l in added if 'return ' in l]
        
        if removed_returns != added_returns:
            risks.append(RegressionRisk(
                type="behavior_change",
                severity="high",
                description="Return values modified",
                affected_components=[file_path],
                mitigation="Verify all callers handle new return values",
                test_suggestions=[
                    "Test return value compatibility",
                    "Check error handling",
                    "Verify type consistency"
                ]
            ))
        
        # Check for exception handling changes
        removed_exceptions = [l for l in removed if any(kw in l for kw in ['except ', 'raise ', 'try:'])]
        added_exceptions = [l for l in added if any(kw in l for kw in ['except ', 'raise ', 'try:'])]
        
        if removed_exceptions or added_exceptions:
            risks.append(RegressionRisk(
                type="behavior_change",
                severity="medium",
                description="Exception handling modified",
                affected_components=[file_path],
                mitigation="Ensure error handling remains robust",
                test_suggestions=[
                    "Test error scenarios",
                    "Verify exception propagation",
                    "Check error messages"
                ]
            ))
        
        return risks
    
    def _check_performance_impacts(self, removed: List[str], added: List[str], file_path: str) -> List[RegressionRisk]:
        """Check for potential performance impacts."""
        risks = []
        
        # Check for added loops
        removed_loops = len([l for l in removed if any(kw in l for kw in ['for ', 'while '])])
        added_loops = len([l for l in added if any(kw in l for kw in ['for ', 'while '])])
        
        if added_loops > removed_loops:
            risks.append(RegressionRisk(
                type="performance",
                severity="medium",
                description="Additional loops added, potential performance impact",
                affected_components=[file_path],
                mitigation="Profile code and optimize if necessary",
                test_suggestions=[
                    "Run performance benchmarks",
                    "Test with large datasets",
                    "Monitor resource usage"
                ]
            ))
        
        # Check for database query changes
        db_patterns = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', '.query(', '.filter(', '.all()', '.first()']
        removed_queries = sum(1 for l in removed if any(p in l for p in db_patterns))
        added_queries = sum(1 for l in added if any(p in l for p in db_patterns))
        
        if added_queries > removed_queries:
            risks.append(RegressionRisk(
                type="performance",
                severity="high",
                description="Additional database queries detected",
                affected_components=[file_path],
                mitigation="Consider query optimization or caching",
                test_suggestions=[
                    "Profile database queries",
                    "Check for N+1 query problems",
                    "Test query performance"
                ]
            ))
        
        # Check for synchronous I/O in async context
        if any('async ' in l for l in added):
            sync_io = [l for l in added if any(p in l for p in ['open(', 'requests.', 'urllib.'])]
            if sync_io:
                risks.append(RegressionRisk(
                    type="performance",
                    severity="high",
                    description="Synchronous I/O in async function",
                    affected_components=[file_path],
                    mitigation="Use async I/O libraries",
                    test_suggestions=[
                        "Test async performance",
                        "Check for blocking operations",
                        "Monitor event loop"
                    ]
                ))
        
        return risks
    
    def _check_security_impacts(self, removed: List[str], added: List[str], file_path: str) -> List[RegressionRisk]:
        """Check for security impacts."""
        risks = []
        
        # Check for SQL injection risks
        sql_patterns = [
            r'\.format\s*\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE)',
            r'%\s*\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE)',
            r'\+.*(?:SELECT|INSERT|UPDATE|DELETE)',
        ]
        
        for pattern in sql_patterns:
            if any(re.search(pattern, l, re.IGNORECASE) for l in added):
                risks.append(RegressionRisk(
                    type="security",
                    severity="critical",
                    description="Potential SQL injection vulnerability",
                    affected_components=[file_path],
                    mitigation="Use parameterized queries",
                    test_suggestions=[
                        "Test with malicious input",
                        "Run security scanning tools",
                        "Review query construction"
                    ]
                ))
                break
        
        # Check for removed authentication/authorization
        auth_patterns = ['@login_required', '@requires_auth', 'check_permission', 'authenticate']
        removed_auth = any(any(p in l for p in auth_patterns) for l in removed)
        added_auth = any(any(p in l for p in auth_patterns) for l in added)
        
        if removed_auth and not added_auth:
            risks.append(RegressionRisk(
                type="security",
                severity="critical",
                description="Authentication/authorization checks removed",
                affected_components=[file_path],
                mitigation="Ensure proper access controls remain in place",
                test_suggestions=[
                    "Test unauthorized access attempts",
                    "Verify permission checks",
                    "Audit access logs"
                ]
            ))
        
        # Check for hardcoded secrets
        secret_patterns = [
            r'(?:password|secret|key|token)\s*=\s*["\'][^"\']+["\']',
            r'(?:AWS|AZURE|GCP)_[A-Z_]+\s*=\s*["\'][^"\']+["\']'
        ]
        
        for pattern in secret_patterns:
            if any(re.search(pattern, l, re.IGNORECASE) for l in added):
                risks.append(RegressionRisk(
                    type="security",
                    severity="critical",
                    description="Hardcoded secrets detected",
                    affected_components=[file_path],
                    mitigation="Use environment variables or secret management service",
                    test_suggestions=[
                        "Scan for exposed secrets",
                        "Verify secret rotation",
                        "Check environment configuration"
                    ]
                ))
                break
        
        return risks
    
    def _detect_parameter_changes(self, removed: List[str], added: List[str]) -> List[Dict[str, Any]]:
        """Detect function parameter changes."""
        changes = []
        
        # Simple pattern matching for function definitions
        func_pattern = r'def\s+(\w+)\s*\(([^)]*)\)'
        
        removed_funcs = {}
        for line in removed:
            match = re.search(func_pattern, line)
            if match:
                func_name = match.group(1)
                params = [p.strip() for p in match.group(2).split(',') if p.strip()]
                removed_funcs[func_name] = params
        
        added_funcs = {}
        for line in added:
            match = re.search(func_pattern, line)
            if match:
                func_name = match.group(1)
                params = [p.strip() for p in match.group(2).split(',') if p.strip()]
                added_funcs[func_name] = params
        
        # Compare parameters
        for func_name in set(removed_funcs.keys()) & set(added_funcs.keys()):
            if removed_funcs[func_name] != added_funcs[func_name]:
                changes.append({
                    "function": func_name,
                    "removed": list(set(removed_funcs[func_name]) - set(added_funcs[func_name])),
                    "added": list(set(added_funcs[func_name]) - set(removed_funcs[func_name]))
                })
        
        return changes
    
    def _analyze_addition(self, change: CodeChange, context: Dict[str, Any]) -> List[RegressionRisk]:
        """Analyze new file additions."""
        risks = []
        
        # Check if new dependencies are introduced
        if 'import' in change.diff or 'require' in change.diff:
            risks.append(RegressionRisk(
                type="behavior_change",
                severity="low",
                description="New dependencies introduced",
                affected_components=[change.file_path],
                mitigation="Verify dependency compatibility and security",
                test_suggestions=[
                    "Check dependency versions",
                    "Run security audit",
                    "Test in isolated environment"
                ]
            ))
        
        return risks
    
    def _analyze_rename(self, change: CodeChange, context: Dict[str, Any]) -> List[RegressionRisk]:
        """Analyze file renames."""
        risks = []
        
        risks.append(RegressionRisk(
            type="api_change",
            severity="medium",
            description=f"File renamed: {change.file_path}",
            affected_components=[change.file_path],
            mitigation="Update all imports and references",
            test_suggestions=[
                "Verify all imports are updated",
                "Check configuration files",
                "Test module loading"
            ]
        ))
        
        return risks
    
    def _analyze_cross_file_impacts(self, changes: List[CodeChange], context: Dict[str, Any]) -> List[RegressionRisk]:
        """Analyze impacts across multiple files."""
        risks = []
        
        # Check for interface changes that affect multiple files
        modified_interfaces = set()
        for change in changes:
            if change.change_type == "modify" and any(
                keyword in change.diff for keyword in ['class ', 'interface ', 'trait ']
            ):
                modified_interfaces.add(change.file_path)
        
        if len(modified_interfaces) > 1:
            risks.append(RegressionRisk(
                type="behavior_change",
                severity="high",
                description="Multiple interfaces modified simultaneously",
                affected_components=list(modified_interfaces),
                mitigation="Ensure all implementations are updated consistently",
                test_suggestions=[
                    "Run integration tests",
                    "Verify interface contracts",
                    "Check for version mismatches"
                ]
            ))
        
        # Check for cascading changes
        if len(changes) > 10:
            risks.append(RegressionRisk(
                type="behavior_change",
                severity="medium",
                description="Large number of files changed",
                affected_components=[c.file_path for c in changes[:5]] + ["..."],
                mitigation="Consider breaking into smaller, incremental changes",
                test_suggestions=[
                    "Run comprehensive test suite",
                    "Perform staged rollout",
                    "Monitor system behavior closely"
                ]
            ))
        
        return risks
    
    def _compile_api_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for API detection."""
        return {
            "flask_route": re.compile(r'@app\.route\s*\([\'"]([^\'"]+)[\'"]\)'),
            "fastapi_route": re.compile(r'@(app|router)\.(get|post|put|delete|patch)\s*\([\'"]([^\'"]+)[\'"]\)'),
            "django_url": re.compile(r'path\s*\([\'"]([^\'"]+)[\'"]'),
            "express_route": re.compile(r'(app|router)\.(get|post|put|delete|patch)\s*\([\'"]([^\'"]+)[\'"]'),
        }
    
    def _compile_behavior_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for behavior detection."""
        return {
            "function_def": re.compile(r'def\s+(\w+)\s*\(([^)]*)\)'),
            "class_def": re.compile(r'class\s+(\w+)'),
            "conditional": re.compile(r'(if|elif|while|for)\s+'),
            "exception": re.compile(r'(try:|except\s+|raise\s+)'),
            "return": re.compile(r'return\s+'),
        }
    
    def _deduplicate_risks(self, risks: List[RegressionRisk]) -> List[RegressionRisk]:
        """Remove duplicate risks."""
        seen = set()
        unique_risks = []
        
        for risk in risks:
            key = (risk.type, risk.description, tuple(risk.affected_components))
            if key not in seen:
                seen.add(key)
                unique_risks.append(risk)
        
        return unique_risks
    
    def _risk_priority(self, risk: RegressionRisk) -> int:
        """Calculate risk priority for sorting."""
        severity_scores = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        
        type_scores = {
            "security": 4,
            "api_change": 3,
            "behavior_change": 2,
            "performance": 1
        }
        
        return (
            severity_scores.get(risk.severity, 0) * 10 +
            type_scores.get(risk.type, 0)
        )
    
    def generate_regression_report(self, risks: List[RegressionRisk], step: RefactorStep) -> str:
        """Generate a detailed regression report."""
        if not risks:
            return f"No regression risks detected for step: {step.description}"
        
        report = f"# Regression Analysis Report\n\n"
        report += f"**Step**: {step.description}\n"
        report += f"**Type**: {step.type.value}\n"
        report += f"**Risk Level**: {step.risk_level}\n\n"
        
        report += "## Detected Risks\n\n"
        
        # Group by severity
        by_severity = {}
        for risk in risks:
            by_severity.setdefault(risk.severity, []).append(risk)
        
        for severity in ["critical", "high", "medium", "low"]:
            if severity in by_severity:
                report += f"### {severity.upper()} Severity\n\n"
                for risk in by_severity[severity]:
                    report += f"**{risk.type}**: {risk.description}\n"
                    report += f"- Affected: {', '.join(risk.affected_components)}\n"
                    if risk.mitigation:
                        report += f"- Mitigation: {risk.mitigation}\n"
                    if risk.test_suggestions:
                        report += f"- Tests needed:\n"
                        for test in risk.test_suggestions:
                            report += f"  - {test}\n"
                    report += "\n"
        
        report += "## Recommendations\n\n"
        report += "1. Address all critical and high severity risks before proceeding\n"
        report += "2. Implement suggested tests for each risk area\n"
        report += "3. Consider breaking large changes into smaller steps\n"
        report += "4. Set up monitoring for affected components\n"
        
        return report