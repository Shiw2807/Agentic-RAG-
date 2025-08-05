#!/usr/bin/env python3
"""Example usage of the Microservice Refactor Agent."""

from refactor_agent import RefactorAgent, SafetyLevel


def main():
    # Initialize the agent with a repository path
    agent = RefactorAgent(
        repo_path="./example-microservice",  # Path to your microservice repo
        log_level="INFO"
    )
    
    print("=== Microservice Refactor Agent Demo ===\n")
    
    # Step 1: Analyze the current architecture
    print("1. Analyzing microservice architecture...")
    analysis = agent.analyze_architecture()
    
    print(f"\nAnalysis Results:")
    print(f"- Services found: {len(analysis.services)}")
    print(f"- Dependencies: {len(analysis.dependencies)}")
    print(f"- Code smells: {len(analysis.code_smells)}")
    print(f"- Coupling score: {analysis.metrics.get('coupling_score', 0):.2f}")
    
    # Display code smells
    if analysis.code_smells:
        print("\nTop Code Smells:")
        for smell in analysis.code_smells[:3]:
            print(f"- [{smell.severity}] {smell.type}: {smell.description}")
    
    # Step 2: Create a refactoring plan
    print("\n2. Creating refactoring plan...")
    plan = agent.create_refactoring_plan(
        target_architecture="domain-driven",  # Options: domain-driven, event-driven, microservices
        safety_level=SafetyLevel.HIGH,
        priorities=["api_versioning", "database_migration", "god_service"]
    )
    
    print(f"\nRefactoring Plan:")
    print(f"- Target: {plan.target_architecture}")
    print(f"- Steps: {len(plan.steps)}")
    print(f"- Estimated effort: {plan.total_effort} hours")
    print(f"- Risk distribution: {plan.risk_assessment['risk_distribution']}")
    
    # Display plan steps
    print("\nPlanned Steps:")
    for i, step in enumerate(plan.steps[:5]):
        print(f"{i+1}. {step.description}")
        print(f"   Type: {step.type.value}, Risk: {step.risk_level}, Effort: {step.estimated_effort}h")
    
    if len(plan.steps) > 5:
        print(f"... and {len(plan.steps) - 5} more steps")
    
    # Step 3: Execute refactoring (dry run)
    print("\n3. Executing refactoring (dry run)...")
    results = agent.execute_refactoring(
        plan=plan,
        auto_commit=False,  # Set to True to create actual commits
        dry_run=True,       # Set to False to apply actual changes
        interactive=False   # Set to True for step-by-step confirmation
    )
    
    print(f"\nExecution Results:")
    successful = sum(1 for r in results if r.success)
    print(f"- Successful steps: {successful}/{len(results)}")
    
    # Display regression risks
    all_risks = []
    for result in results:
        all_risks.extend(result.regression_risks)
    
    high_risks = [r for r in all_risks if r.severity in ["critical", "high"]]
    if high_risks:
        print(f"\nHigh-Priority Regression Risks:")
        for risk in high_risks[:3]:
            print(f"- [{risk.severity}] {risk.type}: {risk.description}")
            if risk.mitigation:
                print(f"  Mitigation: {risk.mitigation}")
    
    # Step 4: Generate report
    print("\n4. Generating final report...")
    report = agent.generate_report()
    
    # Save report
    with open("refactoring_report.md", "w") as f:
        f.write(report)
    print("Report saved to refactoring_report.md")
    
    print("\n=== Demo Complete ===")
    print("\nNext steps:")
    print("1. Review the generated refactoring plan")
    print("2. Run with dry_run=False to apply changes")
    print("3. Use auto_commit=True to create Git commits")
    print("4. Review the pull request description")


def advanced_example():
    """Advanced example with custom configuration."""
    
    # Custom configuration
    config = {
        "safety_level": "high",
        "auto_detect_services": True,
        "commit_style": "conventional",
        "max_changes_per_commit": 15,
        "regression_threshold": 0.8
    }
    
    # Save config
    import json
    with open("refactor_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    # Initialize with config
    agent = RefactorAgent(
        repo_path="./legacy-monolith",
        config_path="refactor_config.json"
    )
    
    # Analyze with specific service paths
    service_paths = {
        "auth": "services/authentication",
        "user": "services/user-management",
        "billing": "services/billing",
        "notification": "services/notifications"
    }
    
    analysis = agent.analyze_architecture(service_paths=service_paths)
    
    # Create plan with specific migration strategy
    plan = agent.create_refactoring_plan(
        target_architecture="event-driven",
        safety_level=SafetyLevel.MEDIUM,
        priorities=["shared_database", "high_coupling", "god_service"]
    )
    
    # Execute with interactive mode
    results = agent.execute_refactoring(
        plan=plan,
        auto_commit=True,
        dry_run=False,
        interactive=True  # Will prompt for each step
    )
    
    return results


if __name__ == "__main__":
    main()
    
    # Uncomment to run advanced example
    # advanced_example()