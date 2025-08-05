"""Tests for authentication service."""

import pytest
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, auth_manager


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Reset database for each test
        auth_manager.init_db()
        yield client


def test_register_user(client):
    """Test user registration."""
    response = client.post('/register', 
        json={
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com'
        }
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'user_id' in data


def test_login_valid_credentials(client):
    """Test login with valid credentials."""
    # First register a user
    client.post('/register',
        json={
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com'
        }
    )
    
    # Then try to login
    response = client.post('/login',
        json={
            'username': 'testuser',
            'password': 'testpass123'
        }
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'token' in data


def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post('/login',
        json={
            'username': 'nonexistent',
            'password': 'wrongpass'
        }
    )
    assert response.status_code == 401
    data = json.loads(response.data)
    assert 'error' in data


def test_validate_token(client):
    """Test token validation."""
    # Register and login
    client.post('/register',
        json={
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com'
        }
    )
    
    login_response = client.post('/login',
        json={
            'username': 'testuser',
            'password': 'testpass123'
        }
    )
    token = json.loads(login_response.data)['token']
    
    # Validate token
    response = client.post('/validate',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['username'] == 'testuser'


def test_logout(client):
    """Test logout functionality."""
    # Register and login
    client.post('/register',
        json={
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com'
        }
    )
    
    login_response = client.post('/login',
        json={
            'username': 'testuser',
            'password': 'testpass123'
        }
    )
    token = json.loads(login_response.data)['token']
    
    # Logout
    response = client.post('/logout',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 200


def test_change_password(client):
    """Test password change."""
    # Register and login
    client.post('/register',
        json={
            'username': 'testuser',
            'password': 'oldpass123',
            'email': 'test@example.com'
        }
    )
    
    login_response = client.post('/login',
        json={
            'username': 'testuser',
            'password': 'oldpass123'
        }
    )
    token = json.loads(login_response.data)['token']
    
    # Change password
    response = client.post('/change-password',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'old_password': 'oldpass123',
            'new_password': 'newpass123'
        }
    )
    assert response.status_code == 200
    
    # Try to login with new password
    response = client.post('/login',
        json={
            'username': 'testuser',
            'password': 'newpass123'
        }
    )
    assert response.status_code == 200


def test_get_users_no_auth(client):
    """Test getting users without authentication (security issue)."""
    # This test passes but highlights a security issue
    response = client.get('/users')
    assert response.status_code == 200


def test_delete_user_no_auth(client):
    """Test deleting user without authorization (security issue)."""
    # Register a user
    response = client.post('/register',
        json={
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com'
        }
    )
    user_id = json.loads(response.data)['user_id']
    
    # Delete without auth (security issue)
    response = client.delete(f'/users/{user_id}')
    assert response.status_code == 200