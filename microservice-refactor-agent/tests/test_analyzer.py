"""Tests for the code and architecture analyzer components."""

import pytest
from pathlib import Path
import tempfile
import os

from refactor_agent.analyzer import CodeAnalyzer, ArchitectureAnalyzer
from refactor_agent.models import CodeSmell


class TestCodeAnalyzer:
    """Test cases for CodeAnalyzer."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample Python file
            sample_file = Path(tmpdir) / "service.py"
            sample_file.write_text("""
import requests
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/users')
def get_users():
    # High complexity function
    users = []
    for i in range(10):
        if i % 2 == 0:
            users.append({'id': i, 'name': f'User {i}'})
        else:
            for j in range(5):
                if j > 2:
                    users.append({'id': i*10+j, 'name': f'User {i}-{j}'})
    return jsonify(users)

class UserService:
    def __init__(self):
        self.db = None
    
    def get_user(self, user_id):
        query = f"SELECT * FROM users WHERE id = {user_id}"
        return self.db.execute(query)
""")
            yield tmpdir
    
    def test_analyze_file(self, temp_repo):
        """Test file analysis."""
        analyzer = CodeAnalyzer(temp_repo)
        result = analyzer.analyze_file("service.py")
        
        assert "error" not in result
        assert len(result["imports"]) == 2
        assert len(result["classes"]) == 1
        assert len(result["functions"]) == 2
        assert result["complexity"] > 1
        assert "flask" in result["api_endpoints"][0]["framework"]
    
    def test_extract_imports(self, temp_repo):
        """Test import extraction."""
        analyzer = CodeAnalyzer(temp_repo)
        result = analyzer.analyze_file("service.py")
        
        imports = result["imports"]
        assert any(imp["module"] == "requests" for imp in imports)
        assert any("flask" in imp["module"] for imp in imports)
    
    def test_extract_api_endpoints(self, temp_repo):
        """Test API endpoint extraction."""
        analyzer = CodeAnalyzer(temp_repo)
        result = analyzer.analyze_file("service.py")
        
        endpoints = result["api_endpoints"]
        assert len(endpoints) == 1
        assert endpoints[0]["path"] == "/api/users"
        assert endpoints[0]["method"] == "GET"
    
    def test_detect_sql_injection(self, temp_repo):
        """Test SQL injection detection in queries."""
        analyzer = CodeAnalyzer(temp_repo)
        result = analyzer.analyze_file("service.py")
        
        # The analyzer should detect the f-string SQL query
        queries = result["database_queries"]
        assert len(queries) > 0


class TestArchitectureAnalyzer:
    """Test cases for ArchitectureAnalyzer."""
    
    @pytest.fixture
    def multi_service_repo(self):
        """Create a repository with multiple services."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple services
            services = ["auth-service", "user-service", "billing-service"]
            
            for service in services:
                service_dir = Path(tmpdir) / service
                service_dir.mkdir()
                
                # Create main.py for each service
                main_file = service_dir / "main.py"
                if service == "auth-service":
                    main_file.write_text("""
from flask import Flask
app = Flask(__name__)

@app.route('/api/auth/login')
def login():
    return {'status': 'ok'}

@app.route('/api/auth/logout')
def logout():
    return {'status': 'ok'}
""")
                elif service == "user-service":
                    main_file.write_text("""
from flask import Flask
import requests

app = Flask(__name__)

@app.route('/api/users')
def get_users():
    # Call auth service
    auth = requests.get('http://auth-service/api/auth/verify')
    return {'users': []}

@app.route('/api/users/<id>')
def get_user(id):
    return {'id': id}
""")
                else:  # billing-service
                    main_file.write_text("""
from flask import Flask
app = Flask(__name__)

# Too many endpoints (god service)
""" + "\n".join([f"""
@app.route('/api/billing/{endpoint}')
def {endpoint}():
    return {{}}
""" for endpoint in [
    'invoice', 'payment', 'subscription', 'refund', 'credit',
    'debit', 'balance', 'history', 'report', 'export',
    'import', 'validate', 'process', 'cancel', 'approve',
    'reject', 'review', 'audit', 'reconcile', 'dispute',
    'charge', 'void', 'adjust'
]]))
            
            yield tmpdir, services
    
    def test_analyze_architecture(self, multi_service_repo):
        """Test architecture analysis."""
        tmpdir, services = multi_service_repo
        
        code_analyzer = CodeAnalyzer(tmpdir)
        arch_analyzer = ArchitectureAnalyzer(code_analyzer)
        
        service_paths = {
            service.replace('-service', ''): service 
            for service in services
        }
        
        analysis = arch_analyzer.analyze_architecture(service_paths)
        
        assert len(analysis.services) == 3
        assert len(analysis.code_smells) > 0
        assert analysis.metrics["total_services"] == 3
    
    def test_detect_god_service(self, multi_service_repo):
        """Test god service detection."""
        tmpdir, services = multi_service_repo
        
        code_analyzer = CodeAnalyzer(tmpdir)
        arch_analyzer = ArchitectureAnalyzer(code_analyzer)
        
        service_paths = {"billing": "billing-service"}
        analysis = arch_analyzer.analyze_architecture(service_paths)
        
        # Should detect god service smell
        god_service_smells = [
            smell for smell in analysis.code_smells 
            if smell.type == "god_service"
        ]
        
        assert len(god_service_smells) > 0
        assert god_service_smells[0].severity == "high"
    
    def test_calculate_metrics(self, multi_service_repo):
        """Test metrics calculation."""
        tmpdir, services = multi_service_repo
        
        code_analyzer = CodeAnalyzer(tmpdir)
        arch_analyzer = ArchitectureAnalyzer(code_analyzer)
        
        service_paths = {
            service.replace('-service', ''): service 
            for service in services
        }
        
        analysis = arch_analyzer.analyze_architecture(service_paths)
        
        assert "total_services" in analysis.metrics
        assert "avg_service_complexity" in analysis.metrics
        assert "coupling_score" in analysis.metrics
        assert analysis.metrics["total_services"] == 3