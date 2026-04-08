import requests
from django.conf import settings


class PlopplopService:
    """
    Passerelle de paiement plopplop.solutionip.app
    Supporte : moncash, natcash
    Doc : https://plopplop.solutionip.app/paiement-doc
    """

    BASE_URL = 'https://plopplop.solutionip.app'

    def __init__(self):
        self.client_id = getattr(settings, 'PLOPPLOP_CLIENT_ID', '')

    def is_configured(self) -> bool:
        return bool(self.client_id)

    def initier_paiement(self, commande_ref: str, montant: float, payment_method: str) -> dict:
        """
        POST /api/paiement-marchand
        Retourne {'redirect_url': str, 'transaction_id': str}
        """
        response = requests.post(
            f"{self.BASE_URL}/api/paiement-marchand",
            headers={"Content-Type": "application/json"},
            json={
                "client_id":      self.client_id,
                "refference_id":  f"MKT-{commande_ref}",
                "montant":        float(montant),
                "payment_method": payment_method,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("status"):
            raise ValueError(data.get("message", "Erreur de la passerelle de paiement."))
        return {
            "redirect_url":   data["url"],
            "transaction_id": data.get("transaction_id", ""),
        }

    def verifier_paiement(self, commande_ref: str) -> dict:
        """
        POST /api/paiement-verify
        Retourne le dict de la transaction (trans_status: 'no'|'ok')
        """
        response = requests.post(
            f"{self.BASE_URL}/api/paiement-verify",
            headers={"Content-Type": "application/json"},
            json={
                "client_id":     self.client_id,
                "refference_id": f"MKT-{commande_ref}",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
