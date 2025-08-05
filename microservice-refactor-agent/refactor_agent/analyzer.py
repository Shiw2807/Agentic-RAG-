"""Code and architecture analysis components."""

import ast
import os
import re
from typing import Dict, List, Set, Tuple, Any, Optional
from pathlib import Path
import networkx as nx
from collections import defaultdict

from .models import (
    ServiceDependency,
    CodeSmell,
    ArchitectureAnalysis,
    CodeChange
)


class CodeAnalyzer:
    """Analyzes code structure and identifies patterns."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.file_cache = {}
        
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single file for structure and patterns."""
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}
            
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        try:
            tree = ast.parse(content)
            return {
                "imports": self._extract_imports(tree),
                "classes": self._extract_classes(tree),
                "functions": self._extract_functions(tree),
                "complexity": self._calculate_complexity(tree),
                "dependencies": self._extract_dependencies(content),
                "api_endpoints": self._extract_api_endpoints(content),
                "database_queries": self._extract_db_queries(content),
            }
        except SyntaxError as e:
            return {"error": f"Syntax error in {file_path}: {str(e)}"}
    
    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, str]]:
        """Extract import statements."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "type": "import"
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append({
                        "module": f"{module}.{alias.name}",
                        "alias": alias.asname,
                        "type": "from_import"
                    })
        return imports
    
    def _extract_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract class definitions."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({
                    "name": node.name,
                    "methods": methods,
                    "bases": [self._get_name(base) for base in node.bases],
                    "decorators": [self._get_name(d) for d in node.decorator_list],
                    "line_number": node.lineno
                })
        return classes
    
    def _extract_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract function definitions."""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "decorators": [self._get_name(d) for d in node.decorator_list],
                    "returns": self._get_name(node.returns) if node.returns else None,
                    "line_number": node.lineno,
                    "complexity": self._calculate_function_complexity(node)
                })
        return functions
    
    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        return complexity
    
    def _calculate_function_complexity(self, func_node: ast.FunctionDef) -> int:
        """Calculate complexity for a single function."""
        complexity = 1
        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
        return complexity
    
    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract external dependencies from code."""
        # Look for common dependency patterns
        patterns = [
            r'requests\.(get|post|put|delete)\s*\(',
            r'boto3\.client\s*\(',
            r'redis\.Redis\s*\(',
            r'psycopg2\.connect\s*\(',
            r'pymongo\.MongoClient\s*\(',
            r'kafka\.KafkaProducer\s*\(',
            r'celery\.Celery\s*\(',
        ]
        
        dependencies = set()
        for pattern in patterns:
            if re.search(pattern, content):
                service = pattern.split(r'\.')[0].replace('\\', '')
                dependencies.add(service)
                
        return list(dependencies)
    
    def _extract_api_endpoints(self, content: str) -> List[Dict[str, str]]:
        """Extract API endpoint definitions."""
        endpoints = []
        
        # Flask/FastAPI patterns
        patterns = [
            (r'@app\.(route|get|post|put|delete)\s*\([\'"]([^\'"]+)[\'"]\)', 'flask'),
            (r'@router\.(get|post|put|delete)\s*\([\'"]([^\'"]+)[\'"]\)', 'fastapi'),
            (r'@api\.(route|resource)\s*\([\'"]([^\'"]+)[\'"]\)', 'flask-restful'),
        ]
        
        for pattern, framework in patterns:
            for match in re.finditer(pattern, content):
                method = match.group(1).upper() if match.group(1) not in ['route', 'resource'] else 'GET'
                endpoints.append({
                    "path": match.group(2),
                    "method": method,
                    "framework": framework
                })
                
        return endpoints
    
    def _extract_db_queries(self, content: str) -> List[Dict[str, str]]:
        """Extract database query patterns."""
        queries = []
        
        # SQL patterns
        sql_patterns = [
            (r'(SELECT|INSERT|UPDATE|DELETE)\s+.*?\s+FROM\s+(\w+)', 'sql'),
            (r'db\.session\.(query|add|delete|commit)\s*\(', 'sqlalchemy'),
            (r'\.objects\.(all|filter|get|create|update|delete)\s*\(', 'django-orm'),
        ]
        
        for pattern, query_type in sql_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                queries.append({
                    "type": query_type,
                    "operation": match.group(1) if match.groups() else "unknown",
                    "table": match.group(2) if len(match.groups()) > 1 else "unknown"
                })
                
        return queries
    
    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, str):
            return node
        return "unknown"


class ArchitectureAnalyzer:
    """Analyzes microservice architecture and dependencies."""
    
    def __init__(self, code_analyzer: CodeAnalyzer):
        self.code_analyzer = code_analyzer
        self.dependency_graph = nx.DiGraph()
        
    def analyze_architecture(self, service_paths: Dict[str, str]) -> ArchitectureAnalysis:
        """Analyze the overall microservice architecture."""
        services = {}
        dependencies = []
        code_smells = []
        
        # Analyze each service
        for service_name, service_path in service_paths.items():
            service_analysis = self._analyze_service(service_name, service_path)
            services[service_name] = service_analysis
            
            # Detect code smells
            smells = self._detect_code_smells(service_name, service_analysis)
            code_smells.extend(smells)
        
        # Build dependency graph
        dependencies = self._build_dependency_graph(services)
        
        # Calculate architecture metrics
        metrics = self._calculate_metrics(services, dependencies)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(services, dependencies, code_smells)
        
        # Identify risk areas
        risk_areas = self._identify_risk_areas(services, dependencies)
        
        return ArchitectureAnalysis(
            services=services,
            dependencies=dependencies,
            code_smells=code_smells,
            metrics=metrics,
            recommendations=recommendations,
            risk_areas=risk_areas
        )
    
    def _analyze_service(self, service_name: str, service_path: str) -> Dict[str, Any]:
        """Analyze a single microservice."""
        analysis = {
            "name": service_name,
            "path": service_path,
            "files": [],
            "total_lines": 0,
            "complexity": 0,
            "api_endpoints": [],
            "database_tables": set(),
            "external_dependencies": set(),
            "internal_calls": []
        }
        
        # Analyze all Python files in the service
        for root, _, files in os.walk(self.code_analyzer.repo_path / service_path):
            for file in files:
                if file.endswith('.py'):
                    rel_path = os.path.relpath(root, self.code_analyzer.repo_path) + '/' + file
                    file_analysis = self.code_analyzer.analyze_file(rel_path)
                    
                    if "error" not in file_analysis:
                        analysis["files"].append(rel_path)
                        analysis["complexity"] += file_analysis.get("complexity", 0)
                        analysis["api_endpoints"].extend(file_analysis.get("api_endpoints", []))
                        
                        # Extract database tables
                        for query in file_analysis.get("database_queries", []):
                            if query.get("table") != "unknown":
                                analysis["database_tables"].add(query["table"])
                        
                        # Extract dependencies
                        for dep in file_analysis.get("dependencies", []):
                            analysis["external_dependencies"].add(dep)
                            
        analysis["database_tables"] = list(analysis["database_tables"])
        analysis["external_dependencies"] = list(analysis["external_dependencies"])
        
        return analysis
    
    def _detect_code_smells(self, service_name: str, service_analysis: Dict[str, Any]) -> List[CodeSmell]:
        """Detect code smells in a service."""
        smells = []
        
        # God service (too many endpoints)
        if len(service_analysis["api_endpoints"]) > 20:
            smells.append(CodeSmell(
                type="god_service",
                severity="high",
                location=service_name,
                description=f"Service has {len(service_analysis['api_endpoints'])} endpoints, consider splitting",
                suggested_fix="Split into smaller, focused services based on domain boundaries"
            ))
        
        # High complexity
        avg_complexity = service_analysis["complexity"] / max(len(service_analysis["files"]), 1)
        if avg_complexity > 10:
            smells.append(CodeSmell(
                type="high_complexity",
                severity="medium",
                location=service_name,
                description=f"Average file complexity is {avg_complexity:.1f}",
                suggested_fix="Refactor complex functions and classes"
            ))
        
        # Shared database
        if len(service_analysis["database_tables"]) > 0:
            for other_service, other_analysis in service_analysis.items():
                if other_service != service_name:
                    shared_tables = set(service_analysis["database_tables"]) & set(other_analysis.get("database_tables", []))
                    if shared_tables:
                        smells.append(CodeSmell(
                            type="shared_database",
                            severity="high",
                            location=f"{service_name} and {other_service}",
                            description=f"Services share database tables: {shared_tables}",
                            suggested_fix="Consider database-per-service pattern or API-based data access"
                        ))
        
        return smells
    
    def _build_dependency_graph(self, services: Dict[str, Dict[str, Any]]) -> List[ServiceDependency]:
        """Build service dependency graph."""
        dependencies = []
        
        for service_name, service_data in services.items():
            # Check for API calls between services
            for endpoint in service_data.get("api_endpoints", []):
                # Look for calls to this endpoint in other services
                for other_service, other_data in services.items():
                    if other_service != service_name:
                        # Simple heuristic: check if endpoint path appears in other service's code
                        # In real implementation, would do more sophisticated analysis
                        if self._check_api_dependency(endpoint["path"], other_data):
                            dep = ServiceDependency(
                                source=other_service,
                                target=service_name,
                                dependency_type="api",
                                strength=0.7,
                                calls=[endpoint["path"]]
                            )
                            dependencies.append(dep)
                            self.dependency_graph.add_edge(other_service, service_name, weight=0.7)
        
        return dependencies
    
    def _check_api_dependency(self, endpoint_path: str, service_data: Dict[str, Any]) -> bool:
        """Check if a service depends on an API endpoint."""
        # Simplified check - in reality would parse code more thoroughly
        endpoint_pattern = endpoint_path.replace('/', r'\/')
        for file_path in service_data.get("files", []):
            # Would actually read and parse file content
            # For now, return False as placeholder
            pass
        return False
    
    def _calculate_metrics(self, services: Dict[str, Dict[str, Any]], 
                          dependencies: List[ServiceDependency]) -> Dict[str, float]:
        """Calculate architecture metrics."""
        metrics = {
            "total_services": len(services),
            "total_dependencies": len(dependencies),
            "avg_service_complexity": sum(s["complexity"] for s in services.values()) / max(len(services), 1),
            "coupling_score": len(dependencies) / max(len(services) * (len(services) - 1), 1),
            "avg_endpoints_per_service": sum(len(s["api_endpoints"]) for s in services.values()) / max(len(services), 1)
        }
        
        # Calculate centrality metrics if we have dependencies
        if self.dependency_graph.number_of_nodes() > 0:
            centrality = nx.degree_centrality(self.dependency_graph)
            metrics["max_centrality"] = max(centrality.values()) if centrality else 0
            metrics["avg_centrality"] = sum(centrality.values()) / len(centrality) if centrality else 0
        
        return metrics
    
    def _generate_recommendations(self, services: Dict[str, Dict[str, Any]], 
                                 dependencies: List[ServiceDependency],
                                 code_smells: List[CodeSmell]) -> List[str]:
        """Generate architecture improvement recommendations."""
        recommendations = []
        
        # Check for circular dependencies
        if self.dependency_graph.number_of_nodes() > 0:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            if cycles:
                recommendations.append(f"Remove circular dependencies between services: {cycles}")
        
        # Check for overly complex services
        for service_name, service_data in services.items():
            if service_data["complexity"] > 100:
                recommendations.append(f"Consider breaking down {service_name} - complexity score: {service_data['complexity']}")
        
        # Check for missing API versioning
        unversioned_apis = []
        for service_name, service_data in services.items():
            for endpoint in service_data.get("api_endpoints", []):
                if '/v' not in endpoint["path"]:
                    unversioned_apis.append(f"{service_name}:{endpoint['path']}")
        
        if unversioned_apis:
            recommendations.append(f"Add API versioning to endpoints: {unversioned_apis[:5]}...")
        
        # Database recommendations
        services_with_db = [s for s, d in services.items() if d.get("database_tables")]
        if len(services_with_db) > 1:
            recommendations.append("Consider implementing database-per-service pattern for better isolation")
        
        return recommendations
    
    def _identify_risk_areas(self, services: Dict[str, Dict[str, Any]], 
                            dependencies: List[ServiceDependency]) -> List[Dict[str, Any]]:
        """Identify high-risk areas in the architecture."""
        risk_areas = []
        
        # High coupling risk
        if self.dependency_graph.number_of_nodes() > 0:
            centrality = nx.degree_centrality(self.dependency_graph)
            for node, score in centrality.items():
                if score > 0.5:
                    risk_areas.append({
                        "type": "high_coupling",
                        "service": node,
                        "risk_score": score,
                        "description": f"{node} is highly coupled with {int(score * len(services))} other services"
                    })
        
        # Single point of failure
        for service_name, service_data in services.items():
            dependents = [d.source for d in dependencies if d.target == service_name]
            if len(dependents) > len(services) * 0.5:
                risk_areas.append({
                    "type": "single_point_of_failure",
                    "service": service_name,
                    "risk_score": len(dependents) / len(services),
                    "description": f"{service_name} is a dependency for {len(dependents)} services"
                })
        
        return risk_areas