"""Tests for billing service."""

import pytest
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, billing


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Reset database for each test
        billing.init_db()
        yield client


def test_create_invoice(client):
    """Test invoice creation."""
    response = client.post('/invoice',
        json={
            'user_id': 1,
            'amount': 100.0,
            'due_days': 30
        }
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'invoice_id' in data


def test_process_payment(client):
    """Test payment processing."""
    # First create an invoice
    invoice_response = client.post('/invoice',
        json={
            'user_id': 1,
            'amount': 100.0
        }
    )
    invoice_id = json.loads(invoice_response.data)['invoice_id']
    
    # Process payment
    response = client.post('/payment',
        json={
            'invoice_id': invoice_id,
            'amount': 100.0,
            'method': 'credit_card',
            'card_details': {
                'number': '1234567812345678',
                'cvv': '123',
                'expiry': '12/25'
            }
        }
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'completed'


def test_payment_insufficient_amount(client):
    """Test payment with insufficient amount."""
    # Create invoice
    invoice_response = client.post('/invoice',
        json={
            'user_id': 1,
            'amount': 100.0
        }
    )
    invoice_id = json.loads(invoice_response.data)['invoice_id']
    
    # Try to pay less
    response = client.post('/payment',
        json={
            'invoice_id': invoice_id,
            'amount': 50.0,
            'method': 'credit_card'
        }
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_create_subscription(client):
    """Test subscription creation."""
    response = client.post('/subscription',
        json={
            'user_id': 1,
            'plan': 'premium',
            'price': 29.99
        }
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'subscription_id' in data


def test_duplicate_subscription(client):
    """Test creating duplicate subscription."""
    # Create first subscription
    client.post('/subscription',
        json={
            'user_id': 1,
            'plan': 'premium',
            'price': 29.99
        }
    )
    
    # Try to create another
    response = client.post('/subscription',
        json={
            'user_id': 1,
            'plan': 'basic',
            'price': 9.99
        }
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_cancel_subscription(client):
    """Test subscription cancellation."""
    # Create subscription
    sub_response = client.post('/subscription',
        json={
            'user_id': 1,
            'plan': 'premium',
            'price': 29.99
        }
    )
    sub_id = json.loads(sub_response.data)['subscription_id']
    
    # Cancel it
    response = client.delete(f'/subscription/{sub_id}')
    assert response.status_code == 200


def test_process_refund(client):
    """Test refund processing."""
    # Create invoice and payment
    invoice_response = client.post('/invoice',
        json={
            'user_id': 1,
            'amount': 100.0
        }
    )
    invoice_id = json.loads(invoice_response.data)['invoice_id']
    
    payment_response = client.post('/payment',
        json={
            'invoice_id': invoice_id,
            'amount': 100.0,
            'method': 'credit_card'
        }
    )
    payment_id = json.loads(payment_response.data)['payment_id']
    
    # Process refund
    response = client.post('/refund',
        json={
            'payment_id': payment_id,
            'amount': 50.0,
            'reason': 'Customer request'
        }
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'refund_id' in data


def test_get_user_balance(client):
    """Test getting user balance."""
    # Create some invoices
    client.post('/invoice',
        json={
            'user_id': 1,
            'amount': 100.0
        }
    )
    
    response = client.get('/balance/1')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'balance' in data
    assert 'pending' in data
    assert 'paid' in data


def test_generate_report(client):
    """Test report generation."""
    response = client.get('/report?start_date=2024-01-01&end_date=2024-12-31')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'total_revenue' in data
    assert 'total_refunds' in data
    assert 'active_subscriptions' in data


def test_calculate_tax(client):
    """Test tax calculation."""
    response = client.post('/tax-calculate',
        json={'amount': 100.0}
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['tax'] == 10.0  # 10% of 100
    assert data['total'] == 110.0


def test_currency_conversion(client):
    """Test currency conversion."""
    response = client.post('/currency-convert',
        json={
            'from': 'USD',
            'to': 'EUR',
            'amount': 100.0
        }
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'converted' in data


def test_validate_card(client):
    """Test card validation."""
    # Valid card
    response = client.post('/validate-card',
        json={'number': '1234567812345678'}
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['valid'] is True
    
    # Invalid card
    response = client.post('/validate-card',
        json={'number': '123'}
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['valid'] is False