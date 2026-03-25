import requests
import base64
from django.conf import settings


class MonCashService:
    """
    Client REST MonCash — API officielle Digicel.
    https://sandbox.moncashbutton.digicelgroup.com
    """

    _API_HOSTS = {
        'sandbox':    'https://sandbox.moncashbutton.digicelgroup.com/Api',
        'production': 'https://moncashbutton.digicelgroup.com/Api',
    }
    _GATEWAY_URLS = {
        'sandbox':    'https://sandbox.moncashbutton.digicelgroup.com/Moncash-middleware',
        'production': 'https://moncashbutton.digicelgroup.com/Moncash-middleware',
    }

    def __init__(self):
        self.env        = getattr(settings, 'MONCASH_ENVIRONMENT', 'sandbox')
        self.client_id  = getattr(settings, 'MONCASH_CLIENT_ID',  '')
        self.secret_key = getattr(settings, 'MONCASH_SECRET_KEY', '')
        self.api_host   = self._API_HOSTS.get(self.env,   self._API_HOSTS['sandbox'])
        self.gateway    = self._GATEWAY_URLS.get(self.env, self._GATEWAY_URLS['sandbox'])

    def is_configured(self) -> bool:
        return bool(self.client_id and self.secret_key)

    # ── Auth ─────────────────────────────────────────────────────────────────

    def _get_token(self) -> str:
        """POST /oauth/token — Basic client_credentials → access_token."""
        credentials = base64.b64encode(
            f"{self.client_id}:{self.secret_key}".encode()
        ).decode()
        response = requests.post(
            f"{self.api_host}/oauth/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Accept":        "application/json",
                "Content-Type":  "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": "read,write"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    # ── Paiement ─────────────────────────────────────────────────────────────

    def initier_paiement(self, commande_ref: str, montant_htg: float) -> dict:
        """
        POST /v1/CreatePayment
        Retourne {'token': str, 'redirect_url': str}
        orderId = "MKT-{commande_ref}"
        """
        token    = self._get_token()
        order_id = f"MKT-{commande_ref}"
        response = requests.post(
            f"{self.api_host}/v1/CreatePayment",
            headers={
                "Accept":        "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            json={"amount": float(montant_htg), "orderId": order_id},
            timeout=30,
        )
        response.raise_for_status()
        payment_token = response.json()["payment_token"]["token"]
        redirect_url  = f"{self.gateway}/Payment/Redirect?token={payment_token}"
        return {"token": payment_token, "redirect_url": redirect_url}

    # ── Vérification ─────────────────────────────────────────────────────────

    def verifier_paiement(self, transaction_id: str) -> dict:
        """
        POST /v1/RetrieveTransactionPayment
        Retourne le dict 'payment': reference, transaction_id, cost, message, payer.
        """
        token    = self._get_token()
        response = requests.post(
            f"{self.api_host}/v1/RetrieveTransactionPayment",
            headers={
                "Accept":        "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            json={"transactionId": transaction_id},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("payment", data)

    def verifier_par_ordre(self, order_id: str) -> dict:
        """
        POST /v1/RetrieveOrderPayment
        Retourne le dict 'payment'.
        """
        token    = self._get_token()
        response = requests.post(
            f"{self.api_host}/v1/RetrieveOrderPayment",
            headers={
                "Accept":        "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            json={"orderId": order_id},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("payment", data)
