"""Legacy authentication service with various code smells."""

from flask import Flask, request, jsonify
import jwt
import datetime
import hashlib
import sqlite3
import os

app = Flask(__name__)
SECRET_KEY = "hardcoded-secret-key-123"  # Security issue: hardcoded secret

# Database connection - shared with other services (anti-pattern)
def get_db():
    conn = sqlite3.connect('/tmp/shared_database.db')
    return conn

# God class with too many responsibilities
class AuthManager:
    def __init__(self):
        self.db = get_db()
        self.init_db()
    
    def init_db(self):
        cursor = self.db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                email TEXT,
                role TEXT,
                created_at TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                token TEXT,
                expires_at TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                action TEXT,
                timestamp TIMESTAMP
            )
        ''')
        self.db.commit()
    
    def hash_password(self, password):
        # Weak hashing algorithm
        return hashlib.md5(password.encode()).hexdigest()
    
    def create_user(self, username, password, email, role='user'):
        cursor = self.db.cursor()
        # SQL injection vulnerability
        query = f"INSERT INTO users (username, password, email, role, created_at) VALUES ('{username}', '{self.hash_password(password)}', '{email}', '{role}', '{datetime.datetime.now()}')"
        cursor.execute(query)
        self.db.commit()
        return cursor.lastrowid
    
    def authenticate(self, username, password):
        cursor = self.db.cursor()
        # Another SQL injection vulnerability
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{self.hash_password(password)}'"
        cursor.execute(query)
        user = cursor.fetchone()
        
        if user:
            # Complex nested logic
            token = jwt.encode({
                'user_id': user[0],
                'username': user[1],
                'role': user[4],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, SECRET_KEY, algorithm='HS256')
            
            # Store session
            cursor.execute(f"INSERT INTO sessions (user_id, token, expires_at) VALUES ({user[0]}, '{token}', '{datetime.datetime.utcnow() + datetime.timedelta(hours=24)}')")
            self.db.commit()
            
            # Log action
            cursor.execute(f"INSERT INTO audit_logs (user_id, action, timestamp) VALUES ({user[0]}, 'login', '{datetime.datetime.now()}')")
            self.db.commit()
            
            return token
        return None
    
    def validate_token(self, token):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            return payload
        except:
            return None
    
    def get_user_permissions(self, user_id):
        # Complex permission logic mixed with data access
        cursor = self.db.cursor()
        cursor.execute(f"SELECT role FROM users WHERE id = {user_id}")
        role = cursor.fetchone()
        
        if role:
            if role[0] == 'admin':
                return ['read', 'write', 'delete', 'admin']
            elif role[0] == 'user':
                return ['read', 'write']
            else:
                return ['read']
        return []
    
    def logout(self, token):
        cursor = self.db.cursor()
        cursor.execute(f"DELETE FROM sessions WHERE token = '{token}'")
        self.db.commit()
    
    def change_password(self, user_id, old_password, new_password):
        # No password strength validation
        cursor = self.db.cursor()
        cursor.execute(f"SELECT password FROM users WHERE id = {user_id}")
        current = cursor.fetchone()
        
        if current and current[0] == self.hash_password(old_password):
            cursor.execute(f"UPDATE users SET password = '{self.hash_password(new_password)}' WHERE id = {user_id}")
            self.db.commit()
            return True
        return False
    
    def get_all_users(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM users")
        return cursor.fetchall()
    
    def delete_user(self, user_id):
        cursor = self.db.cursor()
        cursor.execute(f"DELETE FROM users WHERE id = {user_id}")
        cursor.execute(f"DELETE FROM sessions WHERE user_id = {user_id}")
        cursor.execute(f"DELETE FROM audit_logs WHERE user_id = {user_id}")
        self.db.commit()

# Global instance (anti-pattern)
auth_manager = AuthManager()

# Unversioned API endpoints
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    token = auth_manager.authenticate(data['username'], data['password'])
    if token:
        return jsonify({'token': token}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    user_id = auth_manager.create_user(
        data['username'], 
        data['password'], 
        data['email'],
        data.get('role', 'user')
    )
    return jsonify({'user_id': user_id}), 201

@app.route('/validate', methods=['POST'])
def validate():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    payload = auth_manager.validate_token(token)
    if payload:
        return jsonify(payload), 200
    return jsonify({'error': 'Invalid token'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    auth_manager.logout(token)
    return jsonify({'message': 'Logged out'}), 200

@app.route('/users', methods=['GET'])
def get_users():
    # No authentication check!
    users = auth_manager.get_all_users()
    return jsonify(users), 200

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    # No authorization check!
    auth_manager.delete_user(user_id)
    return jsonify({'message': 'User deleted'}), 200

@app.route('/change-password', methods=['POST'])
def change_password():
    data = request.json
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    payload = auth_manager.validate_token(token)
    
    if payload:
        success = auth_manager.change_password(
            payload['user_id'],
            data['old_password'],
            data['new_password']
        )
        if success:
            return jsonify({'message': 'Password changed'}), 200
    return jsonify({'error': 'Failed to change password'}), 400

if __name__ == '__main__':
    app.run(port=5001)