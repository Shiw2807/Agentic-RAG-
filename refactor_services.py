#!/usr/bin/env python3
"""Script to refactor auth and billing services using the refactor agent."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'microservice-refactor-agent'))

from refactor_agent import RefactorAgent, SafetyLevel
import subprocess
import json


def run_tests(service_path):
    """Run tests for a service."""
    print(f"\nRunning tests for {service_path}...")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", f"{service_path}/tests/", "-v"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        print(result.stdout)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running tests: {e}")
        return False


def main():
    print("=== Microservice Refactoring Demo ===\n")
    
    # Initialize the refactor agent
    agent = RefactorAgent(
        repo_path=os.path.dirname(__file__),
        log_level="INFO"
    )
    
    # Define service paths
    service_paths = {
        "auth": "services/auth-service",
        "billing": "services/billing-service"
    }
    
    # Step 1: Run initial tests
    print("1. Running initial tests to ensure they pass...")
    auth_tests_pass = run_tests("services/auth-service")
    billing_tests_pass = run_tests("services/billing-service")
    
    print(f"\nAuth service tests: {'PASSED' if auth_tests_pass else 'FAILED'}")
    print(f"Billing service tests: {'PASSED' if billing_tests_pass else 'FAILED'}")
    
    # Step 2: Analyze the architecture
    print("\n2. Analyzing microservice architecture...")
    analysis = agent.analyze_architecture(service_paths=service_paths)
    
    print(f"\nAnalysis Results:")
    print(f"- Services found: {len(analysis.services)}")
    print(f"- Code smells detected: {len(analysis.code_smells)}")
    print(f"- Dependencies: {len(analysis.dependencies)}")
    
    # Display detected issues
    print("\nDetected Issues:")
    for i, smell in enumerate(analysis.code_smells[:5], 1):
        print(f"{i}. [{smell.severity}] {smell.type}: {smell.description}")
        if smell.suggested_fix:
            print(f"   Fix: {smell.suggested_fix}")
    
    # Step 3: Create refactoring plan
    print("\n3. Creating refactoring plan...")
    plan = agent.create_refactoring_plan(
        target_architecture="microservices",
        safety_level=SafetyLevel.HIGH,
        priorities=["security", "api_versioning", "god_service", "shared_database"]
    )
    
    print(f"\nRefactoring Plan:")
    print(f"- Total steps: {len(plan.steps)}")
    print(f"- Estimated effort: {plan.total_effort} hours")
    print(f"- Risk assessment: {plan.risk_assessment['risk_distribution']}")
    
    print("\nPlanned Refactoring Steps:")
    for i, step in enumerate(plan.steps[:10], 1):
        print(f"{i}. {step.description}")
        print(f"   Type: {step.type.value}, Risk: {step.risk_level}, Effort: {step.estimated_effort}h")
    
    # Step 4: Execute refactoring with Git commits
    print("\n4. Executing refactoring (with Git commits)...")
    
    # Initialize git if needed
    subprocess.run(["git", "init"], cwd=os.path.dirname(__file__))
    subprocess.run(["git", "add", "."], cwd=os.path.dirname(__file__))
    subprocess.run(["git", "commit", "-m", "Initial commit with legacy services"], cwd=os.path.dirname(__file__))
    
    # Execute refactoring
    results = agent.execute_refactoring(
        plan=plan,
        auto_commit=True,
        dry_run=False,  # Set to False to apply actual changes
        interactive=False
    )
    
    print(f"\nExecution Results:")
    successful = sum(1 for r in results if r.success)
    print(f"- Successful steps: {successful}/{len(results)}")
    
    # Display commits created
    print("\nCommits created:")
    for result in results:
        if result.success and result.commit_info:
            print(f"- {result.commit_info.message}")
    
    # Step 5: Analyze regression risks
    print("\n5. Regression Risk Analysis:")
    all_risks = []
    for result in results:
        all_risks.extend(result.regression_risks)
    
    high_risks = [r for r in all_risks if r.severity in ["critical", "high"]]
    medium_risks = [r for r in all_risks if r.severity == "medium"]
    
    print(f"- Critical/High risks: {len(high_risks)}")
    print(f"- Medium risks: {len(medium_risks)}")
    
    if high_risks:
        print("\nHigh Priority Risks:")
        for risk in high_risks[:5]:
            print(f"- [{risk.severity}] {risk.type}: {risk.description}")
            if risk.mitigation:
                print(f"  Mitigation: {risk.mitigation}")
    
    # Step 6: Run tests again
    print("\n6. Running tests after refactoring...")
    auth_tests_pass_after = run_tests("services/auth-service")
    billing_tests_pass_after = run_tests("services/billing-service")
    
    print(f"\nAuth service tests: {'PASSED' if auth_tests_pass_after else 'FAILED'}")
    print(f"Billing service tests: {'PASSED' if billing_tests_pass_after else 'FAILED'}")
    
    # Step 7: Generate final report
    print("\n7. Generating final report...")
    report = agent.generate_report()
    
    with open("refactoring_report.md", "w") as f:
        f.write(report)
    print("Report saved to refactoring_report.md")
    
    # Summary
    print("\n=== Refactoring Summary ===")
    print(f"✓ Analyzed {len(service_paths)} services")
    print(f"✓ Detected {len(analysis.code_smells)} code smells")
    print(f"✓ Created {len(plan.steps)} refactoring steps")
    print(f"✓ Successfully executed {successful}/{len(results)} steps")
    print(f"✓ Created {successful} Git commits")
    print(f"✓ Tests status: Auth={'✓' if auth_tests_pass_after else '✗'}, Billing={'✓' if billing_tests_pass_after else '✗'}")
    
    # Show git log
    print("\n=== Git History ===")
    subprocess.run(["git", "log", "--oneline", "-10"], cwd=os.path.dirname(__file__))


if __name__ == "__main__":
    main()