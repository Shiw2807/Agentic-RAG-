"""Refactoring planning and strategy components."""

import uuid
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from collections import defaultdict
import networkx as nx

from .models import (
    RefactorType,
    SafetyLevel,
    RefactorStep,
    RefactorPlan,
    MigrationStrategy,
    ArchitectureAnalysis,
    CodeSmell
)


class RefactorPlanner:
    """Plans safe and incremental refactoring strategies."""
    
    def __init__(self):
        self.strategies = self._load_migration_strategies()
        
    def create_refactoring_plan(
        self,
        analysis: ArchitectureAnalysis,
        target_architecture: str,
        safety_level: SafetyLevel = SafetyLevel.HIGH,
        priorities: Optional[List[str]] = None
    ) -> RefactorPlan:
        """Create a comprehensive refactoring plan."""
        plan_id = str(uuid.uuid4())
        steps = []
        
        # Determine which refactoring steps are needed
        if target_architecture == "domain-driven":
            steps.extend(self._plan_ddd_migration(analysis, safety_level))
        elif target_architecture == "event-driven":
            steps.extend(self._plan_event_driven_migration(analysis, safety_level))
        elif target_architecture == "microservices":
            steps.extend(self._plan_microservices_migration(analysis, safety_level))
        else:
            # Generic improvements based on code smells
            steps.extend(self._plan_generic_improvements(analysis, safety_level))
        
        # Apply priorities if specified
        if priorities:
            steps = self._prioritize_steps(steps, priorities)
        
        # Order steps by dependencies
        steps = self._order_by_dependencies(steps)
        
        # Calculate total effort
        total_effort = sum(step.estimated_effort for step in steps)
        
        # Assess risks
        risk_assessment = self._assess_plan_risks(steps, analysis)
        
        # Define success criteria
        success_criteria = self._define_success_criteria(target_architecture, analysis)
        
        return RefactorPlan(
            id=plan_id,
            created_at=datetime.now(),
            target_architecture=target_architecture,
            safety_level=safety_level,
            steps=steps,
            total_effort=total_effort,
            risk_assessment=risk_assessment,
            success_criteria=success_criteria,
            rollback_plan=self._create_rollback_plan(steps)
        )
    
    def _plan_ddd_migration(self, analysis: ArchitectureAnalysis, safety_level: SafetyLevel) -> List[RefactorStep]:
        """Plan migration to Domain-Driven Design."""
        steps = []
        
        # Step 1: Identify and extract bounded contexts
        for service_name, service_data in analysis.services.items():
            if len(service_data["api_endpoints"]) > 10:
                # Service might contain multiple bounded contexts
                steps.append(RefactorStep(
                    id=f"extract-context-{service_name}",
                    type=RefactorType.SPLIT_SERVICE,
                    description=f"Extract bounded contexts from {service_name}",
                    target_files=[f for f in service_data["files"]],
                    estimated_effort=16,
                    risk_level="medium",
                    validation_steps=[
                        "Verify all endpoints still function",
                        "Check data consistency",
                        "Validate domain boundaries"
                    ],
                    commit_message=f"refactor: extract bounded contexts from {service_name}"
                ))
        
        # Step 2: Implement aggregates and entities
        steps.append(RefactorStep(
            id="implement-aggregates",
            type=RefactorType.RESTRUCTURE,
            description="Implement DDD aggregates and entities",
            target_files=[],  # Will be determined during execution
            dependencies=["extract-context-*"],
            estimated_effort=24,
            risk_level="low",
            validation_steps=[
                "Verify aggregate boundaries",
                "Check invariant enforcement",
                "Validate entity relationships"
            ],
            commit_message="refactor: implement DDD aggregates and entities"
        ))
        
        # Step 3: Create domain events
        steps.append(RefactorStep(
            id="create-domain-events",
            type=RefactorType.RESTRUCTURE,
            description="Implement domain events for cross-aggregate communication",
            target_files=[],
            dependencies=["implement-aggregates"],
            estimated_effort=16,
            risk_level="medium",
            validation_steps=[
                "Verify event publishing",
                "Check event handling",
                "Validate event sourcing if applicable"
            ],
            commit_message="feat: add domain events for aggregate communication"
        ))
        
        # Step 4: Implement repositories
        steps.append(RefactorStep(
            id="implement-repositories",
            type=RefactorType.INTERFACE_EXTRACTION,
            description="Create repository interfaces and implementations",
            target_files=[],
            dependencies=["implement-aggregates"],
            estimated_effort=12,
            risk_level="low",
            validation_steps=[
                "Verify data access patterns",
                "Check repository contracts",
                "Validate persistence logic"
            ],
            commit_message="refactor: implement repository pattern for data access"
        ))
        
        return steps
    
    def _plan_event_driven_migration(self, analysis: ArchitectureAnalysis, safety_level: SafetyLevel) -> List[RefactorStep]:
        """Plan migration to event-driven architecture."""
        steps = []
        
        # Step 1: Set up message broker
        steps.append(RefactorStep(
            id="setup-message-broker",
            type=RefactorType.RESTRUCTURE,
            description="Set up message broker infrastructure (Kafka/RabbitMQ)",
            target_files=["docker-compose.yml", "infrastructure/"],
            estimated_effort=8,
            risk_level="low",
            validation_steps=[
                "Verify broker connectivity",
                "Check topic/queue creation",
                "Validate message persistence"
            ],
            commit_message="feat: add message broker infrastructure"
        ))
        
        # Step 2: Convert synchronous calls to events
        for dep in analysis.dependencies:
            if dep.dependency_type == "api" and dep.strength > 0.5:
                steps.append(RefactorStep(
                    id=f"async-{dep.source}-{dep.target}",
                    type=RefactorType.RESTRUCTURE,
                    description=f"Convert sync call from {dep.source} to {dep.target} to async events",
                    target_files=[],  # Will be determined
                    dependencies=["setup-message-broker"],
                    estimated_effort=8,
                    risk_level="high" if safety_level == SafetyLevel.HIGH else "medium",
                    validation_steps=[
                        "Verify event publishing",
                        "Check event consumption",
                        "Validate data consistency",
                        "Test failure scenarios"
                    ],
                    commit_message=f"refactor: convert {dep.source}->{dep.target} to async events"
                ))
        
        # Step 3: Implement event sourcing (optional)
        if safety_level != SafetyLevel.LOW:
            steps.append(RefactorStep(
                id="implement-event-sourcing",
                type=RefactorType.DATABASE_MIGRATION,
                description="Implement event sourcing for critical aggregates",
                target_files=[],
                dependencies=["async-*"],
                estimated_effort=40,
                risk_level="high",
                validation_steps=[
                    "Verify event store",
                    "Check event replay",
                    "Validate projections",
                    "Test snapshot functionality"
                ],
                commit_message="feat: implement event sourcing for audit and replay"
            ))
        
        return steps
    
    def _plan_microservices_migration(self, analysis: ArchitectureAnalysis, safety_level: SafetyLevel) -> List[RefactorStep]:
        """Plan migration to proper microservices architecture."""
        steps = []
        
        # Step 1: Database per service
        services_with_shared_db = self._find_services_with_shared_db(analysis)
        for service_group in services_with_shared_db:
            steps.append(RefactorStep(
                id=f"separate-db-{'-'.join(service_group)}",
                type=RefactorType.DATABASE_MIGRATION,
                description=f"Separate databases for services: {service_group}",
                target_files=[],
                estimated_effort=24,
                risk_level="high",
                validation_steps=[
                    "Verify data migration",
                    "Check data consistency",
                    "Validate cross-service queries",
                    "Test rollback procedures"
                ],
                commit_message=f"refactor: implement database-per-service for {service_group}"
            ))
        
        # Step 2: API versioning
        for service_name, service_data in analysis.services.items():
            unversioned = [e for e in service_data["api_endpoints"] if '/v' not in e["path"]]
            if unversioned:
                steps.append(RefactorStep(
                    id=f"api-versioning-{service_name}",
                    type=RefactorType.API_VERSIONING,
                    description=f"Add API versioning to {service_name}",
                    target_files=[f for f in service_data["files"] if "api" in f or "route" in f],
                    estimated_effort=8,
                    risk_level="medium",
                    validation_steps=[
                        "Verify backward compatibility",
                        "Check version routing",
                        "Validate deprecation headers"
                    ],
                    commit_message=f"feat: add API versioning to {service_name}"
                ))
        
        # Step 3: Service mesh setup (for high safety level)
        if safety_level == SafetyLevel.HIGH:
            steps.append(RefactorStep(
                id="setup-service-mesh",
                type=RefactorType.RESTRUCTURE,
                description="Implement service mesh for observability and security",
                target_files=["kubernetes/", "istio/"],
                dependencies=["api-versioning-*"],
                estimated_effort=32,
                risk_level="medium",
                validation_steps=[
                    "Verify mesh connectivity",
                    "Check mTLS configuration",
                    "Validate traffic policies",
                    "Test circuit breakers"
                ],
                commit_message="feat: add service mesh for improved microservices management"
            ))
        
        return steps
    
    def _plan_generic_improvements(self, analysis: ArchitectureAnalysis, safety_level: SafetyLevel) -> List[RefactorStep]:
        """Plan generic improvements based on code smells."""
        steps = []
        
        # Group code smells by type
        smells_by_type = defaultdict(list)
        for smell in analysis.code_smells:
            smells_by_type[smell.type].append(smell)
        
        # Address god services
        for smell in smells_by_type.get("god_service", []):
            steps.append(RefactorStep(
                id=f"split-god-service-{smell.location}",
                type=RefactorType.SPLIT_SERVICE,
                description=smell.suggested_fix or f"Split {smell.location} into smaller services",
                target_files=[],
                estimated_effort=40,
                risk_level="high",
                validation_steps=[
                    "Verify service boundaries",
                    "Check data consistency",
                    "Validate API contracts",
                    "Test integration points"
                ],
                commit_message=f"refactor: split {smell.location} into focused services"
            ))
        
        # Address high complexity
        for smell in smells_by_type.get("high_complexity", []):
            steps.append(RefactorStep(
                id=f"reduce-complexity-{smell.location}",
                type=RefactorType.RESTRUCTURE,
                description=smell.suggested_fix or f"Reduce complexity in {smell.location}",
                target_files=[],
                estimated_effort=16,
                risk_level="low",
                validation_steps=[
                    "Verify functionality preserved",
                    "Check test coverage",
                    "Validate performance"
                ],
                commit_message=f"refactor: reduce complexity in {smell.location}"
            ))
        
        # Remove dead code
        if any(smell.type == "dead_code" for smell in analysis.code_smells):
            steps.append(RefactorStep(
                id="remove-dead-code",
                type=RefactorType.REMOVE_DEAD_CODE,
                description="Remove unused code and dependencies",
                target_files=[],
                estimated_effort=8,
                risk_level="low",
                validation_steps=[
                    "Verify no runtime dependencies",
                    "Check test coverage",
                    "Validate build process"
                ],
                commit_message="chore: remove dead code and unused dependencies"
            ))
        
        return steps
    
    def _find_services_with_shared_db(self, analysis: ArchitectureAnalysis) -> List[List[str]]:
        """Find groups of services sharing databases."""
        shared_db_groups = []
        processed = set()
        
        for service1, data1 in analysis.services.items():
            if service1 in processed:
                continue
                
            group = [service1]
            tables1 = set(data1.get("database_tables", []))
            
            for service2, data2 in analysis.services.items():
                if service2 != service1 and service2 not in processed:
                    tables2 = set(data2.get("database_tables", []))
                    if tables1 & tables2:  # Shared tables
                        group.append(service2)
            
            if len(group) > 1:
                shared_db_groups.append(group)
                processed.update(group)
        
        return shared_db_groups
    
    def _prioritize_steps(self, steps: List[RefactorStep], priorities: List[str]) -> List[RefactorStep]:
        """Reorder steps based on priorities."""
        priority_map = {p: i for i, p in enumerate(priorities)}
        
        def get_priority(step: RefactorStep) -> int:
            # Check if step type or description matches priorities
            for priority, index in priority_map.items():
                if priority in step.type.value or priority in step.description.lower():
                    return index
            return len(priorities)  # Lowest priority
        
        return sorted(steps, key=get_priority)
    
    def _order_by_dependencies(self, steps: List[RefactorStep]) -> List[RefactorStep]:
        """Order steps respecting dependencies."""
        # Build dependency graph
        graph = nx.DiGraph()
        step_map = {step.id: step for step in steps}
        
        for step in steps:
            graph.add_node(step.id)
            for dep in step.dependencies:
                if dep.endswith("*"):
                    # Wildcard dependency
                    prefix = dep[:-1]
                    for other_id in step_map:
                        if other_id.startswith(prefix):
                            graph.add_edge(other_id, step.id)
                elif dep in step_map:
                    graph.add_edge(dep, step.id)
        
        # Topological sort
        try:
            ordered_ids = list(nx.topological_sort(graph))
            return [step_map[step_id] for step_id in ordered_ids if step_id in step_map]
        except nx.NetworkXUnfeasible:
            # Circular dependency - return original order
            return steps
    
    def _assess_plan_risks(self, steps: List[RefactorStep], analysis: ArchitectureAnalysis) -> Dict[str, Any]:
        """Assess risks in the refactoring plan."""
        risk_counts = defaultdict(int)
        for step in steps:
            risk_counts[step.risk_level] += 1
        
        high_risk_steps = [s for s in steps if s.risk_level == "high"]
        
        return {
            "risk_distribution": dict(risk_counts),
            "high_risk_count": len(high_risk_steps),
            "total_risk_score": sum(
                3 if s.risk_level == "high" else 2 if s.risk_level == "medium" else 1
                for s in steps
            ),
            "mitigation_strategies": [
                "Implement comprehensive testing before high-risk changes",
                "Use feature flags for gradual rollout",
                "Maintain rollback procedures for each step",
                "Monitor system metrics during migration"
            ],
            "critical_paths": self._identify_critical_paths(steps)
        }
    
    def _identify_critical_paths(self, steps: List[RefactorStep]) -> List[List[str]]:
        """Identify critical dependency paths in the plan."""
        # Build dependency graph
        graph = nx.DiGraph()
        for step in steps:
            graph.add_node(step.id)
            for dep in step.dependencies:
                if not dep.endswith("*") and any(s.id == dep for s in steps):
                    graph.add_edge(dep, step.id)
        
        # Find longest paths (critical paths)
        critical_paths = []
        if graph.number_of_nodes() > 0:
            try:
                # Find all paths and get the longest ones
                for source in [n for n in graph.nodes() if graph.in_degree(n) == 0]:
                    for target in [n for n in graph.nodes() if graph.out_degree(n) == 0]:
                        paths = list(nx.all_simple_paths(graph, source, target))
                        critical_paths.extend(paths)
                
                # Sort by length and return top 3
                critical_paths.sort(key=len, reverse=True)
                return critical_paths[:3]
            except:
                pass
        
        return critical_paths
    
    def _define_success_criteria(self, target_architecture: str, analysis: ArchitectureAnalysis) -> List[str]:
        """Define success criteria for the refactoring."""
        criteria = [
            "All existing functionality preserved",
            "No degradation in performance metrics",
            "All tests passing with >80% coverage",
            "No increase in error rates"
        ]
        
        if target_architecture == "domain-driven":
            criteria.extend([
                "Clear bounded contexts established",
                "Aggregates enforce business invariants",
                "Domain events enable loose coupling"
            ])
        elif target_architecture == "event-driven":
            criteria.extend([
                "All synchronous dependencies converted to events",
                "Message delivery guarantees implemented",
                "Event replay capability verified"
            ])
        elif target_architecture == "microservices":
            criteria.extend([
                "Each service has its own database",
                "API versioning implemented",
                "Service discovery and load balancing functional"
            ])
        
        # Add metrics-based criteria
        if analysis.metrics.get("coupling_score", 0) > 0.3:
            criteria.append(f"Coupling score reduced below 0.3 (current: {analysis.metrics['coupling_score']:.2f})")
        
        return criteria
    
    def _create_rollback_plan(self, steps: List[RefactorStep]) -> str:
        """Create a rollback plan for the refactoring."""
        return """
Rollback Procedure:
1. Identify the failed step and its dependencies
2. Revert git commits in reverse order of application
3. Restore database backups if database migrations were involved
4. Redeploy previous service versions
5. Verify system functionality with smoke tests
6. Monitor error rates and performance metrics
7. Document lessons learned and adjust plan

Rollback checkpoints are created after each high-risk step.
Automated rollback triggers on:
- Test failure rate > 10%
- Error rate increase > 5%
- Performance degradation > 20%
"""
    
    def _load_migration_strategies(self) -> Dict[str, MigrationStrategy]:
        """Load predefined migration strategies."""
        return {
            "strangler-fig": MigrationStrategy(
                name="Strangler Fig Pattern",
                description="Gradually replace legacy system by routing traffic to new services",
                phases=[
                    {"name": "Identify boundaries", "duration": 5},
                    {"name": "Create facade", "duration": 3},
                    {"name": "Implement new services", "duration": 20},
                    {"name": "Route traffic gradually", "duration": 10},
                    {"name": "Decommission legacy", "duration": 5}
                ],
                prerequisites=["API gateway", "Feature flags", "Monitoring"],
                risks=["Data synchronization", "Increased complexity during transition"],
                estimated_duration=43,
                resource_requirements={"developers": 4, "devops": 2}
            ),
            "big-bang": MigrationStrategy(
                name="Big Bang Migration",
                description="Replace entire system at once during maintenance window",
                phases=[
                    {"name": "Complete development", "duration": 30},
                    {"name": "Extensive testing", "duration": 10},
                    {"name": "Data migration", "duration": 2},
                    {"name": "Cutover", "duration": 1}
                ],
                prerequisites=["Complete test coverage", "Rollback plan", "Data migration tools"],
                risks=["High risk of failure", "Extended downtime", "No gradual validation"],
                estimated_duration=43,
                resource_requirements={"developers": 6, "devops": 3, "qa": 4}
            ),
            "parallel-run": MigrationStrategy(
                name="Parallel Run Pattern",
                description="Run old and new systems in parallel, comparing results",
                phases=[
                    {"name": "Implement new system", "duration": 25},
                    {"name": "Setup parallel infrastructure", "duration": 5},
                    {"name": "Run in parallel", "duration": 15},
                    {"name": "Validate and switch", "duration": 5}
                ],
                prerequisites=["Double infrastructure", "Result comparison tools", "Traffic replication"],
                risks=["Increased costs", "Complex result reconciliation"],
                estimated_duration=50,
                resource_requirements={"developers": 5, "devops": 3, "qa": 3}
            )
        }