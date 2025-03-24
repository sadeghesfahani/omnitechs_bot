import requests
from typing import Optional

DJANGO_API_BASE = "http://localhost:8000"


def create_invoice(client_id: int, items: list[dict], currency: str = "EUR") -> dict:
    """Send a POST request to create a new invoice with items"""
    url = f"{DJANGO_API_BASE}/invoices/"
    payload = {
        "client_id": client_id,
        "currency": currency,
        "items": items
    }
    response = requests.post(url, json=payload)
    return response.json()

def get_invoice(invoice_id: int) -> dict:
    """Retrieve a single invoice by ID"""
    url = f"{DJANGO_API_BASE}/invoices/{invoice_id}/"
    response = requests.get(url)
    return response.json()

def delete_invoice(invoice_id: int) -> dict:
    """Delete an invoice by ID"""
    url = f"{DJANGO_API_BASE}/invoices/{invoice_id}/"
    response = requests.delete(url)
    return response.json()

def list_invoices() -> list:
    """Retrieve a list of all invoices"""
    url = f"{DJANGO_API_BASE}/invoices/"
    response = requests.get(url)
    return response.json()

def get_client_id_from_telegram(telegram_id: int) -> Optional[int]:
    """Lookup and return the Tryton client_id (party ID) from a Telegram user ID via Django"""
    url = f"{DJANGO_API_BASE}/get_client_id/{telegram_id}/"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("client_id")
    return None