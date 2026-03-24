import requests
import base64
from django.conf import settings


class MonCashService:
    BASE_URL = {
        'sandbox':    'https://sandbox.moncashbutton.digicelhaiti.com',
        'production': 'https://moncashbutton.digicelhaiti.com',
    }

    def __init__(self):
        self.env        = getattr(settings, 'MONCASH_ENVIRONMENT', 'sandbox')
        self.client_id  = settings.MONCASH_CLIENT_ID
        self.secret_key = settings.MONCASH_SECRET_KEY
        self.base_url   = self.BASE_URL[self.env]

    def _get_token(self):
        credentials = base64.b64encode(f"{self.client_id}:{self.secret_key}".encode()).decode()
        response = requests.post(
            f"{self.base_url}/Api/oauth/token",
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "scope": "read,write"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()['access_token']

    def initier_paiement(self, commande_id, montant_htg):
        token    = self._get_token()
        response = requests.post(
            f"{self.base_url}/Api/v1/CreatePayment",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"amount": float(montant_htg), "orderId": f"MKT-{commande_id}"},
            timeout=30,
        )
        response.raise_for_status()
        token_paiement = response.json()['payment_token']['token']
        return {'token': token_paiement, 'redirect_url': f"{self.base_url}/Pay/Confirm/{token_paiement}"}

    def verifier_paiement(self, id_transaction):
        token    = self._get_token()
        response = requests.post(
            f"{self.base_url}/Api/v1/RetrieveTransactionPayment",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"transactionId": id_transaction},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
