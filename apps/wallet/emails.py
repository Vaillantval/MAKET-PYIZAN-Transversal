"""Emails wallet — s'appuie sur apps.emails.utils (Resend)."""

from django.conf import settings

from apps.emails.utils import envoyer_email, envoyer_email_admin


# ── Recharges hors ligne ────────────────────────────────────────

def email_admin_recharge_preuve(recharge):
    """Alerte admin : preuve de recharge hors ligne reçue, à valider."""
    user = recharge.wallet.user
    return envoyer_email_admin(
        sujet=f"🧾 Recharge wallet à valider — #{recharge.pk} ({recharge.montant} HTG)",
        template="wallet_recharge_preuve_admin.html",
        contexte={
            "recharge": recharge,
            "user":     user,
            "admin_url": f"{settings.SITE_URL}/admin/wallet/walletrecharge/{recharge.pk}/change/",
            "site_url": settings.SITE_URL,
        },
    )


def email_recharge_validee(recharge):
    """Client : sa recharge hors ligne a été validée et créditée."""
    user = recharge.wallet.user
    if not user.email:
        return False
    return envoyer_email(
        destinataire=user.email,
        sujet="✅ Votre recharge a été créditée — Makèt Peyizan",
        template="wallet_recharge_validee.html",
        contexte={
            "recharge": recharge,
            "prenom":   user.first_name or user.username,
            "site_url": settings.SITE_URL,
        },
    )


def email_recharge_rejetee(recharge):
    """Client : sa recharge hors ligne a été rejetée."""
    user = recharge.wallet.user
    if not user.email:
        return False
    return envoyer_email(
        destinataire=user.email,
        sujet="Votre recharge n'a pas pu être validée — Makèt Peyizan",
        template="wallet_recharge_rejetee.html",
        contexte={
            "recharge": recharge,
            "prenom":   user.first_name or user.username,
            "site_url": settings.SITE_URL,
        },
    )


# ── Retraits ────────────────────────────────────────────────────

def email_admin_retrait_demande(retrait):
    """Alerte admin : demande de retrait à traiter (transfert manuel)."""
    user = retrait.wallet.user
    return envoyer_email_admin(
        sujet=f"💸 Demande de retrait — #{retrait.pk} ({retrait.montant} HTG, {retrait.get_canal_display()})",
        template="wallet_retrait_demande_admin.html",
        contexte={
            "retrait":  retrait,
            "user":     user,
            "admin_url": f"{settings.SITE_URL}/admin/wallet/walletretrait/{retrait.pk}/change/",
            "site_url": settings.SITE_URL,
        },
    )


def email_retrait_paye(retrait):
    """Client : son retrait a été payé (transfert effectué)."""
    user = retrait.wallet.user
    if not user.email:
        return False
    return envoyer_email(
        destinataire=user.email,
        sujet="✅ Votre retrait a été payé — Makèt Peyizan",
        template="wallet_retrait_paye.html",
        contexte={
            "retrait":  retrait,
            "prenom":   user.first_name or user.username,
            "site_url": settings.SITE_URL,
        },
    )


def email_retrait_rejete(retrait):
    """Client : son retrait a été rejeté, le solde est re-crédité."""
    user = retrait.wallet.user
    if not user.email:
        return False
    return envoyer_email(
        destinataire=user.email,
        sujet="Votre demande de retrait a été rejetée — Makèt Peyizan",
        template="wallet_retrait_rejete.html",
        contexte={
            "retrait":  retrait,
            "prenom":   user.first_name or user.username,
            "site_url": settings.SITE_URL,
        },
    )


# ── Ventes producteur ───────────────────────────────────────────

def email_vente_creditee(tx):
    """Producteur : le produit d'une vente livrée a été crédité."""
    user = tx.wallet.user
    if not user.email:
        return False
    return envoyer_email(
        destinataire=user.email,
        sujet="💰 Vente créditée sur votre portefeuille — Makèt Peyizan",
        template="wallet_vente_creditee.html",
        contexte={
            "tx":       tx,
            "commande": tx.commande,
            "prenom":   user.first_name or user.username,
            "site_url": settings.SITE_URL,
        },
    )


# ── Cashback et parrainage ──────────────────────────────────────

def email_cashback_credite(tx):
    """Acheteur : cashback fidélité crédité sur une commande payée."""
    user = tx.wallet.user
    if not user.email:
        return False
    return envoyer_email(
        destinataire=user.email,
        sujet="🎉 Vous avez gagné du cashback — Makèt Peyizan",
        template="wallet_cashback_credite.html",
        contexte={
            "tx":       tx,
            "commande": tx.commande,
            "prenom":   user.first_name or user.username,
            "site_url": settings.SITE_URL,
        },
    )


def email_bonus_parrainage(tx, est_filleul):
    """Parrain ou filleul : bonus de parrainage crédité (1ère commande du filleul)."""
    user = tx.wallet.user
    if not user.email:
        return False
    sujet = (
        "🎁 Votre bonus de bienvenue est arrivé — Makèt Peyizan"
        if est_filleul else
        "🤝 Votre filleul a commandé — bonus crédité ! — Makèt Peyizan"
    )
    return envoyer_email(
        destinataire=user.email,
        sujet=sujet,
        template="wallet_bonus_parrainage.html",
        contexte={
            "tx":          tx,
            "est_filleul": est_filleul,
            "prenom":      user.first_name or user.username,
            "site_url":    settings.SITE_URL,
        },
    )


# ── Emails lifecycle (Celery Beat) ──────────────────────────────

def email_bon_expire_bientot(bon):
    """Rappel : le bon cadeau expire dans ~30 jours (destinataire ou acheteur)."""
    destinataire = bon.email_destinataire or (
        bon.achete_par.email if bon.achete_par else None
    )
    if not destinataire:
        return False
    return envoyer_email(
        destinataire=destinataire,
        sujet="⏳ Votre bon cadeau expire bientôt — Makèt Peyizan",
        template="wallet_bon_expire_bientot.html",
        contexte={
            "bon":      bon,
            "site_url": settings.SITE_URL,
        },
    )


def email_solde_dormant(wallet):
    """Rappel mensuel : solde inutilisé depuis plus de 30 jours."""
    user = wallet.user
    if not user.email:
        return False
    return envoyer_email(
        destinataire=user.email,
        sujet="💰 Votre solde vous attend — Makèt Peyizan",
        template="wallet_solde_dormant.html",
        contexte={
            "wallet":   wallet,
            "prenom":   user.first_name or user.username,
            "site_url": settings.SITE_URL,
        },
    )


def email_relance_parrainage(user, taux_bonus):
    """Relance : le code de parrainage n'a encore parrainé personne."""
    if not user.email:
        return False
    return envoyer_email(
        destinataire=user.email,
        sujet="🤝 Votre code de parrainage n'attend que vous — Makèt Peyizan",
        template="wallet_relance_parrainage.html",
        contexte={
            "code":       user.code_parrainage,
            "taux_bonus": taux_bonus,
            "lien":       f"{settings.SITE_URL}/inscription/?parrain={user.code_parrainage}",
            "prenom":     user.first_name or user.username,
            "site_url":   settings.SITE_URL,
        },
    )


# ── Bons cadeaux ────────────────────────────────────────────────

def email_bon_cadeau(bon):
    """Envoie le code du bon au destinataire, ou à l'acheteur à défaut."""
    destinataire = bon.email_destinataire or (
        bon.achete_par.email if bon.achete_par else None
    )
    if not destinataire:
        return False
    return envoyer_email(
        destinataire=destinataire,
        sujet="🎁 Vous avez reçu un bon cadeau Makèt Peyizan !",
        template="wallet_bon_cadeau.html",
        contexte={
            "bon":      bon,
            "site_url": settings.SITE_URL,
        },
    )
