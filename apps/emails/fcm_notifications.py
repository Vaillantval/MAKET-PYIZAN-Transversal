"""
Notifications push FCM centralisées — Makèt Peyizan
Chaque fonction inclut un dict `data` structuré pour le deep-linking Flutter.

Convention de routage Flutter (clé `screen`) :
  - admin_commande       → écran détail commande (admin)       data: commande_id, numero
  - producteur_collecte  → écran détail participation collecte data: participation_id, collecte_ref
  - admin_collecte       → écran détail collecte (admin)       data: participation_id, collecte_ref
  - admin_alerte_stock   → écran alerte stock (admin)          data: produit_id, niveau
  - producteur_stock     → écran stock producteur              data: produit_id, niveau
"""
import logging
from apps.emails.fcm_service import send_to_token, send_to_topic

logger = logging.getLogger(__name__)


# ── Nouvelle commande → admins ─────────────────────────────────────────────

def push_nouvelle_commande_admin(commande):
    """
    Notifie les admins (topic role_admin + role_superadmin) d'une nouvelle commande.
    """
    title = "Nouvelle commande reçue"
    body  = f"Commande {commande.numero_commande} — {commande.total:,.0f} HTG"
    data  = {
        "screen":          "admin_commande",
        "commande_id":     str(commande.pk),
        "numero":          commande.numero_commande,
        "acheteur":        commande.acheteur.user.get_full_name() or commande.acheteur.user.username,
        "total":           str(commande.total),
        "methode":         commande.methode_paiement,
    }
    send_to_topic('superadmin', title, body, data)


# ── Invitation collecte → producteur ──────────────────────────────────────

def push_invitation_collecte_producteur(participation):
    """
    Notifie le producteur (token individuel) d'une nouvelle invitation à une collecte.
    """
    fcm_token = getattr(participation.producteur.user, 'fcm_token', None)
    if not fcm_token:
        return

    collecte = participation.collecte
    title    = "Invitation à une collecte"
    body     = (
        f"Collecte {collecte.reference} prévue le "
        f"{collecte.date_planifiee.strftime('%d/%m/%Y')} — {collecte.zone.nom}"
    )
    data = {
        "screen":           "producteur_collecte",
        "participation_id": str(participation.pk),
        "collecte_ref":     collecte.reference,
        "collecte_id":      str(collecte.pk),
        "zone":             collecte.zone.nom,
        "date":             str(collecte.date_planifiee),
    }
    send_to_token(fcm_token, title, body, data)


# ── Collecte confirmée par producteur → admins ────────────────────────────

def push_collecte_confirmee_admin(participation):
    """
    Notifie les admins qu'un producteur a confirmé sa participation à une collecte.
    """
    producteur_nom = participation.producteur.user.get_full_name() or participation.producteur.user.username
    collecte       = participation.collecte

    title = "Producteur prêt pour la collecte"
    body  = f"{producteur_nom} a confirmé — {collecte.reference}"
    data  = {
        "screen":           "admin_collecte",
        "participation_id": str(participation.pk),
        "collecte_ref":     collecte.reference,
        "collecte_id":      str(collecte.pk),
        "producteur":       producteur_nom,
        "quantite_prevue":  str(participation.quantite_prevue),
    }
    send_to_topic('superadmin', title, body, data)


# ── Alerte stock → admins ─────────────────────────────────────────────────

def push_alerte_stock_admin(alerte):
    """
    Notifie les admins (topics) d'une alerte stock CRITIQUE ou ÉPUISÉ.
    """
    niveau_label = alerte.get_niveau_display()
    produit      = alerte.produit

    title = f"Alerte stock {niveau_label} — {produit.nom}"
    body  = (
        f"Stock : {alerte.quantite_actuelle} {produit.unite_vente} "
        f"(seuil : {alerte.seuil_alerte})"
    )
    data = {
        "screen":           "admin_alerte_stock",
        "alerte_id":        str(alerte.pk),
        "produit_id":       str(produit.pk),
        "produit_nom":      produit.nom,
        "niveau":           alerte.niveau,
        "quantite":         str(alerte.quantite_actuelle),
        "seuil":            str(alerte.seuil_alerte),
    }
    send_to_topic('superadmin', title, body, data)


# ── Alerte stock → producteur ─────────────────────────────────────────────

def push_alerte_stock_producteur(alerte):
    """
    Notifie le producteur concerné (token individuel) d'une alerte sur son stock.
    """
    fcm_token = getattr(alerte.produit.producteur.user, 'fcm_token', None)
    if not fcm_token:
        return

    niveau_label = alerte.get_niveau_display()
    produit      = alerte.produit

    title = f"Stock {niveau_label} — {produit.nom}"
    body  = (
        f"Il vous reste {alerte.quantite_actuelle} {produit.unite_vente}. "
        "Pensez à réapprovisionner."
    )
    data = {
        "screen":     "producteur_stock",
        "alerte_id":  str(alerte.pk),
        "produit_id": str(produit.pk),
        "produit_nom": produit.nom,
        "niveau":     alerte.niveau,
        "quantite":   str(alerte.quantite_actuelle),
        "seuil":      str(alerte.seuil_alerte),
    }
    send_to_token(fcm_token, title, body, data)
