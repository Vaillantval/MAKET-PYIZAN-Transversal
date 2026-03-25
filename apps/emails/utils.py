import resend
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY


def envoyer_email(destinataire, sujet, template, contexte):
    """
    Fonction centrale d'envoi d'email via Resend.
    Retourne True si succès, False sinon.
    """
    try:
        html_content = render_to_string(f'emails/{template}', contexte)
        text_content = strip_tags(html_content)

        resend.Emails.send({
            "from":    settings.DEFAULT_FROM_EMAIL,
            "to":      [destinataire] if isinstance(destinataire, str) else destinataire,
            "subject": sujet,
            "html":    html_content,
            "text":    text_content,
        })

        logger.info(f"✅ Email envoyé à {destinataire} — {sujet}")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur envoi email à {destinataire} — {sujet} : {e}")
        return False


def envoyer_email_admin(sujet, template, contexte):
    """Envoie un email à tous les admins configurés dans ADMINS_NOTIFY."""
    raw = settings.ADMINS_NOTIFY
    if not raw:
        return False
    destinataires = [e.strip() for e in raw.split(',') if e.strip()]
    if not destinataires:
        return False
    return envoyer_email(destinataires, sujet, template, contexte)


# ── Emails Producteurs ──────────────────────────────────────────

def email_admin_nouveau_producteur(producteur):
    return envoyer_email_admin(
        sujet=f"🌱 Nouvelle inscription producteur — {producteur.user.get_full_name()}",
        template="admin_nouveau_producteur.html",
        contexte={
            "producteur": producteur,
            "site_url":   settings.SITE_URL,
        }
    )


def email_producteur_bienvenue(producteur):
    return envoyer_email(
        destinataire=producteur.user.email,
        sujet="🌾 Bienvenue sur Makèt Peyizan !",
        template="producteur_bienvenue.html",
        contexte={
            "producteur":      producteur,
            "prenom":          producteur.user.first_name,
            "code_producteur": producteur.code_producteur,
            "site_url":        settings.SITE_URL,
        }
    )


def email_producteur_valide(producteur):
    return envoyer_email(
        destinataire=producteur.user.email,
        sujet="✅ Votre compte producteur est validé !",
        template="producteur_valide.html",
        contexte={
            "producteur": producteur,
            "prenom":     producteur.user.first_name,
            "site_url":   settings.SITE_URL,
        }
    )


def email_producteur_suspendu(producteur, motif=''):
    return envoyer_email(
        destinataire=producteur.user.email,
        sujet="⚠️ Votre compte producteur a été suspendu",
        template="producteur_suspendu.html",
        contexte={
            "producteur": producteur,
            "prenom":     producteur.user.first_name,
            "motif":      motif or producteur.note_admin,
            "site_url":   settings.SITE_URL,
        }
    )


def email_producteur_rejete(producteur, motif=''):
    return envoyer_email(
        destinataire=producteur.user.email,
        sujet="❌ Votre demande d'inscription n'a pas été acceptée",
        template="producteur_rejete.html",
        contexte={
            "producteur": producteur,
            "prenom":     producteur.user.first_name,
            "motif":      motif or producteur.note_admin,
            "site_url":   settings.SITE_URL,
        }
    )


# ── Emails Commandes ────────────────────────────────────────────

def email_nouvelle_commande_acheteur(commande):
    return envoyer_email(
        destinataire=commande.acheteur.user.email,
        sujet=f"📦 Commande {commande.numero_commande} reçue",
        template="commande_nouvelle_acheteur.html",
        contexte={
            "commande": commande,
            "prenom":   commande.acheteur.user.first_name,
            "details":  commande.details.select_related('produit').all(),
            "site_url": settings.SITE_URL,
        }
    )


def email_nouvelle_commande_producteur(commande):
    return envoyer_email(
        destinataire=commande.producteur.user.email,
        sujet=f"🛒 Nouvelle commande reçue — {commande.numero_commande}",
        template="commande_nouvelle_producteur.html",
        contexte={
            "commande": commande,
            "prenom":   commande.producteur.user.first_name,
            "details":  commande.details.select_related('produit').all(),
            "site_url": settings.SITE_URL,
        }
    )


def email_statut_commande_change(commande, statut_avant):
    return envoyer_email(
        destinataire=commande.acheteur.user.email,
        sujet=f"🔄 Mise à jour de votre commande {commande.numero_commande}",
        template="commande_statut_change.html",
        contexte={
            "commande":     commande,
            "prenom":       commande.acheteur.user.first_name,
            "statut_avant": statut_avant,
            "statut_apres": commande.get_statut_display(),
            "site_url":     settings.SITE_URL,
        }
    )


# ── Emails Paiements ────────────────────────────────────────────

def email_paiement_confirme(paiement):
    return envoyer_email(
        destinataire=paiement.commande.acheteur.user.email,
        sujet=f"✅ Paiement confirmé — {paiement.reference}",
        template="paiement_confirme.html",
        contexte={
            "paiement": paiement,
            "commande": paiement.commande,
            "prenom":   paiement.commande.acheteur.user.first_name,
            "site_url": settings.SITE_URL,
        }
    )


def email_preuve_paiement_admin(paiement):
    return envoyer_email_admin(
        sujet=f"💳 Preuve de paiement à vérifier — {paiement.reference}",
        template="admin_preuve_paiement.html",
        contexte={
            "paiement": paiement,
            "commande": paiement.commande,
            "acheteur": paiement.commande.acheteur,
            "site_url": settings.SITE_URL,
        }
    )


# ── Emails Stock ────────────────────────────────────────────────

def email_alerte_stock(alerte):
    return envoyer_email(
        destinataire=alerte.produit.producteur.user.email,
        sujet=f"⚠️ Alerte stock — {alerte.produit.nom}",
        template="alerte_stock.html",
        contexte={
            "alerte":     alerte,
            "produit":    alerte.produit,
            "producteur": alerte.produit.producteur,
            "prenom":     alerte.produit.producteur.user.first_name,
            "site_url":   settings.SITE_URL,
        }
    )


# ── Emails Collectes ────────────────────────────────────────────

def email_invitation_collecte(participation):
    return envoyer_email(
        destinataire=participation.producteur.user.email,
        sujet=f"🚛 Invitation collecte — {participation.collecte.reference}",
        template="collecte_invitation.html",
        contexte={
            "participation": participation,
            "collecte":      participation.collecte,
            "producteur":    participation.producteur,
            "prenom":        participation.producteur.user.first_name,
            "site_url":      settings.SITE_URL,
        }
    )
