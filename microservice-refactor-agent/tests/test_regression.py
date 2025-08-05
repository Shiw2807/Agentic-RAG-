"""Tests for regression detection component."""

import pytest
from refactor_agent.regression import RegressionDetector
from refactor_agent.models import CodeChange, RefactorStep, RefactorType


class TestRegressionDetector:
    """Test cases for RegressionDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create a regression detector instance."""
        return RegressionDetector()
    
    @pytest.fixture
    def api_change(self):
        """Create a sample API change."""
        return CodeChange(
            file_path="api/routes.py",
            change_type="modify",
            diff="""--- a/api/routes.py
+++ b/api/routes.py
@@ -10,7 +10,7 @@
     return jsonify(users)
 
-@app.route('/api/users/<id>')
+@app.route('/api/v2/users/<id>')
 def get_user(id):
     return jsonify({'id': id})
""",
            line_changes={"added": 1, "removed": 1},
            semantic_changes=["Modified API endpoint path"]
        )
    
    @pytest.fixture
    def behavior_change(self):
        """Create a sample behavior change."""
        return CodeChange(
            file_path="services/user_service.py",
            change_type="modify",
            diff="""--- a/services/user_service.py
+++ b/services/user_service.py
@@ -5,8 +5,10 @@
 def process_user(user_data):
-    if user_data.get('age') >= 18:
+    if user_data.get('age') >= 21:
         user_data['status'] = 'adult'
+    elif user_data.get('age') >= 18:
+        user_data['status'] = 'young_adult'
     else:
         user_data['status'] = 'minor'
     return user_data
""",
            line_changes={"added": 4, "removed": 2},
            semantic_changes=["Modified age validation logic"]
        )
    
    def test_detect_api_changes(self, detector, api_change):
        """Test API change detection."""
        risks = detector.analyze_changes([api_change], {})
        
        api_risks = [r for r in risks if r.type == "api_change"]
        assert len(api_risks) > 0
        assert api_risks[0].severity in ["high", "critical"]
        assert "endpoint" in api_risks[0].description.lower()
    
    def test_detect_behavior_changes(self, detector, behavior_change):
        """Test behavior change detection."""
        risks = detector.analyze_changes([behavior_change], {})
        
        behavior_risks = [r for r in risks if r.type == "behavior_change"]
        assert len(behavior_risks) > 0
        assert behavior_risks[0].severity == "high"
        assert "control flow" in behavior_risks[0].description.lower()
    
    def test_detect_sql_injection(self, detector):
        """Test SQL injection detection."""
        sql_change = CodeChange(
            file_path="db/queries.py",
            change_type="modify",
            diff="""--- a/db/queries.py
+++ b/db/queries.py
@@ -3,5 +3,5 @@
 def get_user(user_id):
-    query = "SELECT * FROM users WHERE id = %s"
-    return db.execute(query, (user_id,))
+    query = f"SELECT * FROM users WHERE id = {user_id}"
+    return db.execute(query)
""",
            line_changes={"added": 2, "removed": 2},
            semantic_changes=["Modified SQL query construction"]
        )
        
        risks = detector.analyze_changes([sql_change], {})
        
        security_risks = [r for r in risks if r.type == "security"]
        assert len(security_risks) > 0
        assert security_risks[0].severity == "critical"
        assert "sql injection" in security_risks[0].description.lower()
    
    def test_detect_performance_impact(self, detector):
        """Test performance impact detection."""
        perf_change = CodeChange(
            file_path="services/data_processor.py",
            change_type="modify",
            diff="""--- a/services/data_processor.py
+++ b/services/data_processor.py
@@ -5,6 +5,10 @@
 def process_data(items):
     results = []
     for item in items:
-        results.append(transform(item))
+        for i in range(10):
+            temp = transform(item)
+            for j in range(100):
+                temp = enhance(temp)
+            results.append(temp)
     return results
""",
            line_changes={"added": 6, "removed": 1},
            semantic_changes=["Added nested loops"]
        )
        
        risks = detector.analyze_changes([perf_change], {})
        
        perf_risks = [r for r in risks if r.type == "performance"]
        assert len(perf_risks) > 0
        assert "loops" in perf_risks[0].description.lower()
    
    def test_generate_regression_report(self, detector, api_change):
        """Test regression report generation."""
        risks = detector.analyze_changes([api_change], {})
        
        step = RefactorStep(
            id="test-step",
            type=RefactorType.API_VERSIONING,
            description="Add API versioning",
            target_files=["api/routes.py"],
            estimated_effort=4,
            risk_level="medium"
        )
        
        report = detector.generate_regression_report(risks, step)
        
        assert "Regression Analysis Report" in report
        assert "Add API versioning" in report
        assert "Detected Risks" in report
        assert "Recommendations" in report
    
    def test_risk_prioritization(self, detector):
        """Test that risks are properly prioritized."""
        changes = [
            CodeChange(
                file_path="api/auth.py",
                change_type="modify",
                diff="""--- a/api/auth.py
+++ b/api/auth.py
@@ -1,3 +1,2 @@
-@login_required
 def sensitive_operation():
     pass
""",
                line_changes={"added": 0, "removed": 1},
                semantic_changes=["Removed authentication"]
            ),
            CodeChange(
                file_path="utils/helpers.py",
                change_type="modify",
                diff="""--- a/utils/helpers.py
+++ b/utils/helpers.py
@@ -1,2 +1,2 @@
-def helper():
+def helper_function():
     pass
""",
                line_changes={"added": 1, "removed": 1},
                semantic_changes=["Renamed function"]
            )
        ]
        
        risks = detector.analyze_changes(changes, {})
        
        # Security risk should be prioritized first
        assert risks[0].type == "security"
        assert risks[0].severity == "critical"