"""Legacy billing service with multiple issues."""

from flask import Flask, request, jsonify
import sqlite3
import datetime
import requests
import json

app = Flask(__name__)

# Shared database connection (anti-pattern)
DB_PATH = '/tmp/shared_database.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    return conn

# God class handling too many responsibilities
class BillingSystem:
    def __init__(self):
        self.db = get_db()
        self.init_db()
        self.tax_rate = 0.1  # Hardcoded business logic
        self.currency = 'USD'
        
    def init_db(self):
        cursor = self.db.cursor()
        # Multiple tables in same service (high coupling)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                status TEXT,
                created_at TIMESTAMP,
                due_date TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY,
                invoice_id INTEGER,
                amount REAL,
                method TEXT,
                status TEXT,
                processed_at TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                plan TEXT,
                price REAL,
                status TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refunds (
                id INTEGER PRIMARY KEY,
                payment_id INTEGER,
                amount REAL,
                reason TEXT,
                status TEXT,
                created_at TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credit_cards (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                number TEXT,
                cvv TEXT,
                expiry TEXT
            )
        ''')
        self.db.commit()
    
    def create_invoice(self, user_id, amount, due_days=30):
        cursor = self.db.cursor()
        # Direct SQL without parameterization
        query = f"""
            INSERT INTO invoices (user_id, amount, status, created_at, due_date) 
            VALUES ({user_id}, {amount}, 'pending', '{datetime.datetime.now()}', 
                    '{datetime.datetime.now() + datetime.timedelta(days=due_days)}')
        """
        cursor.execute(query)
        self.db.commit()
        return cursor.lastrowid
    
    def process_payment(self, invoice_id, amount, method, card_details=None):
        cursor = self.db.cursor()
        
        # Get invoice
        cursor.execute(f"SELECT * FROM invoices WHERE id = {invoice_id}")
        invoice = cursor.fetchone()
        
        if not invoice:
            return None
        
        # Complex nested logic
        if invoice[3] == 'paid':
            return {'error': 'Invoice already paid'}
        
        if amount < invoice[2]:
            return {'error': 'Insufficient amount'}
        
        # Process based on method
        if method == 'credit_card' and card_details:
            # Store card details (security issue!)
            cursor.execute(f"""
                INSERT INTO credit_cards (user_id, number, cvv, expiry)
                VALUES ({invoice[1]}, '{card_details['number']}', 
                        '{card_details['cvv']}', '{card_details['expiry']}')
            """)
        
        # Create payment record
        cursor.execute(f"""
            INSERT INTO payments (invoice_id, amount, method, status, processed_at)
            VALUES ({invoice_id}, {amount}, '{method}', 'completed', '{datetime.datetime.now()}')
        """)
        
        # Update invoice status
        cursor.execute(f"UPDATE invoices SET status = 'paid' WHERE id = {invoice_id}")
        
        self.db.commit()
        return {'payment_id': cursor.lastrowid, 'status': 'completed'}
    
    def create_subscription(self, user_id, plan, price):
        cursor = self.db.cursor()
        
        # Check if user already has active subscription
        cursor.execute(f"""
            SELECT * FROM subscriptions 
            WHERE user_id = {user_id} AND status = 'active'
        """)
        
        if cursor.fetchone():
            return {'error': 'User already has active subscription'}
        
        # Create subscription
        start_date = datetime.datetime.now()
        end_date = start_date + datetime.timedelta(days=30)
        
        cursor.execute(f"""
            INSERT INTO subscriptions (user_id, plan, price, status, start_date, end_date)
            VALUES ({user_id}, '{plan}', {price}, 'active', '{start_date}', '{end_date}')
        """)
        
        # Auto-create invoice
        self.create_invoice(user_id, price, 0)
        
        self.db.commit()
        return cursor.lastrowid
    
    def cancel_subscription(self, subscription_id):
        cursor = self.db.cursor()
        cursor.execute(f"""
            UPDATE subscriptions SET status = 'cancelled' 
            WHERE id = {subscription_id}
        """)
        self.db.commit()
    
    def process_refund(self, payment_id, amount, reason):
        cursor = self.db.cursor()
        
        # Get payment
        cursor.execute(f"SELECT * FROM payments WHERE id = {payment_id}")
        payment = cursor.fetchone()
        
        if not payment:
            return None
        
        if amount > payment[2]:
            return {'error': 'Refund amount exceeds payment'}
        
        # Create refund
        cursor.execute(f"""
            INSERT INTO refunds (payment_id, amount, reason, status, created_at)
            VALUES ({payment_id}, {amount}, '{reason}', 'pending', '{datetime.datetime.now()}')
        """)
        
        self.db.commit()
        return cursor.lastrowid
    
    def get_user_balance(self, user_id):
        cursor = self.db.cursor()
        
        # Complex calculation with multiple queries
        cursor.execute(f"""
            SELECT SUM(amount) FROM invoices 
            WHERE user_id = {user_id} AND status = 'pending'
        """)
        pending = cursor.fetchone()[0] or 0
        
        cursor.execute(f"""
            SELECT SUM(amount) FROM payments p
            JOIN invoices i ON p.invoice_id = i.id
            WHERE i.user_id = {user_id} AND p.status = 'completed'
        """)
        paid = cursor.fetchone()[0] or 0
        
        cursor.execute(f"""
            SELECT SUM(r.amount) FROM refunds r
            JOIN payments p ON r.payment_id = p.id
            JOIN invoices i ON p.invoice_id = i.id
            WHERE i.user_id = {user_id} AND r.status = 'completed'
        """)
        refunded = cursor.fetchone()[0] or 0
        
        return {
            'pending': pending,
            'paid': paid,
            'refunded': refunded,
            'balance': pending - paid + refunded
        }
    
    def generate_report(self, start_date, end_date):
        cursor = self.db.cursor()
        
        # Multiple complex queries
        results = {}
        
        # Total revenue
        cursor.execute(f"""
            SELECT SUM(amount) FROM payments 
            WHERE processed_at BETWEEN '{start_date}' AND '{end_date}'
            AND status = 'completed'
        """)
        results['total_revenue'] = cursor.fetchone()[0] or 0
        
        # Total refunds
        cursor.execute(f"""
            SELECT SUM(amount) FROM refunds
            WHERE created_at BETWEEN '{start_date}' AND '{end_date}'
            AND status = 'completed'
        """)
        results['total_refunds'] = cursor.fetchone()[0] or 0
        
        # Active subscriptions
        cursor.execute(f"""
            SELECT COUNT(*) FROM subscriptions
            WHERE status = 'active'
        """)
        results['active_subscriptions'] = cursor.fetchone()[0] or 0
        
        return results

# Global instance
billing = BillingSystem()

# Unversioned endpoints - too many in one service
@app.route('/invoice', methods=['POST'])
def create_invoice():
    data = request.json
    invoice_id = billing.create_invoice(
        data['user_id'],
        data['amount'],
        data.get('due_days', 30)
    )
    return jsonify({'invoice_id': invoice_id}), 201

@app.route('/payment', methods=['POST'])
def process_payment():
    data = request.json
    result = billing.process_payment(
        data['invoice_id'],
        data['amount'],
        data['method'],
        data.get('card_details')
    )
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result), 200

@app.route('/subscription', methods=['POST'])
def create_subscription():
    data = request.json
    result = billing.create_subscription(
        data['user_id'],
        data['plan'],
        data['price']
    )
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 400
    return jsonify({'subscription_id': result}), 201

@app.route('/subscription/<int:subscription_id>', methods=['DELETE'])
def cancel_subscription(subscription_id):
    billing.cancel_subscription(subscription_id)
    return jsonify({'message': 'Subscription cancelled'}), 200

@app.route('/refund', methods=['POST'])
def process_refund():
    data = request.json
    refund_id = billing.process_refund(
        data['payment_id'],
        data['amount'],
        data['reason']
    )
    if refund_id:
        return jsonify({'refund_id': refund_id}), 201
    return jsonify({'error': 'Refund failed'}), 400

@app.route('/balance/<int:user_id>', methods=['GET'])
def get_balance(user_id):
    balance = billing.get_user_balance(user_id)
    return jsonify(balance), 200

@app.route('/report', methods=['GET'])
def generate_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    report = billing.generate_report(start_date, end_date)
    return jsonify(report), 200

# Additional endpoints making it a god service
@app.route('/tax-calculate', methods=['POST'])
def calculate_tax():
    data = request.json
    amount = data['amount']
    tax = amount * billing.tax_rate
    return jsonify({'tax': tax, 'total': amount + tax}), 200

@app.route('/currency-convert', methods=['POST'])
def convert_currency():
    # Hardcoded conversion rates
    rates = {'USD': 1, 'EUR': 0.85, 'GBP': 0.73}
    data = request.json
    from_currency = data['from']
    to_currency = data['to']
    amount = data['amount']
    
    if from_currency in rates and to_currency in rates:
        converted = amount * rates[to_currency] / rates[from_currency]
        return jsonify({'converted': converted}), 200
    return jsonify({'error': 'Unsupported currency'}), 400

@app.route('/validate-card', methods=['POST'])
def validate_card():
    # Simplified card validation
    data = request.json
    card_number = data['number']
    
    if len(card_number) == 16 and card_number.isdigit():
        return jsonify({'valid': True}), 200
    return jsonify({'valid': False}), 200

if __name__ == '__main__':
    app.run(port=5002)