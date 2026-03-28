"""
Service FCM — Firebase Cloud Messaging
Utilise le SDK firebase-admin pour :
  - Envoyer une notification à un token individuel
  - Envoyer une notification à un topic (rôle)
  - Abonner / désabonner un token d'un topic
"""
import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Initialisation unique de l'app Firebase ───────────────────────────────────

def _get_firebase_app():
    """Retourne l'app Firebase, l'initialise si nécessaire."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        cred_dict = getattr(settings, 'FIREBASE_CREDENTIALS_DICT', None)
        if not cred_dict:
            logger.warning("FCM : FIREBASE_SERVICE_ACCOUNT_JSON non configuré ou vide.")
            return None
        cred = credentials.Certificate(cred_dict)
        return firebase_admin.initialize_app(cred)


# ── Topics par rôle ───────────────────────────────────────────────────────────

ROLE_TOPICS = {
    'acheteur':    'role_acheteur',
    'producteur':  'role_producteur',
    'superadmin':  'role_superadmin',
    'collecteur':  'role_collecteur',
}

ALL_ROLES = list(ROLE_TOPICS.values())


# ── Abonnement aux topics ─────────────────────────────────────────────────────

def subscribe_to_role_topic(fcm_token: str, role: str) -> bool:
    """
    Abonne un token FCM au topic correspondant à son rôle.
    Désabonne des autres topics pour éviter les doublons.
    """
    app = _get_firebase_app()
    if not app or not fcm_token:
        return False

    topic = ROLE_TOPICS.get(role)
    if not topic:
        return False

    try:
        # Désabonner des autres topics
        for other_topic in ALL_ROLES:
            if other_topic != topic:
                try:
                    messaging.unsubscribe_from_topic([fcm_token], other_topic, app=app)
                except Exception:
                    pass  # Ignorer si pas abonné

        # Abonner au bon topic
        response = messaging.subscribe_to_topic([fcm_token], topic, app=app)
        if response.failure_count > 0:
            logger.warning(f"FCM subscribe échec pour token {fcm_token[:20]}... : {response.errors}")
            return False
        return True
    except Exception as e:
        logger.error(f"FCM subscribe_to_role_topic erreur : {e}")
        return False


def unsubscribe_from_all_topics(fcm_token: str) -> None:
    """Désabonne un token de tous les topics (lors de la déconnexion)."""
    app = _get_firebase_app()
    if not app or not fcm_token:
        return
    for topic in ALL_ROLES:
        try:
            messaging.unsubscribe_from_topic([fcm_token], topic, app=app)
        except Exception:
            pass


# ── Envoi de notifications ────────────────────────────────────────────────────

def send_to_token(fcm_token: str, title: str, body: str, data: dict = None) -> bool:
    """Envoie une notification push à un token FCM individuel."""
    app = _get_firebase_app()
    if not app or not fcm_token:
        return False

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data={str(k): str(v) for k, v in (data or {}).items()},
        token=fcm_token,
        android=messaging.AndroidConfig(priority='high'),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound='default')
            )
        ),
    )
    try:
        messaging.send(message, app=app)
        return True
    except Exception as e:
        logger.error(f"FCM send_to_token erreur : {e}")
        return False


def send_to_topic(topic_key: str, title: str, body: str, data: dict = None) -> bool:
    """
    Envoie une notification push à tous les abonnés d'un topic.
    topic_key : clé de rôle ('acheteur', 'producteur', etc.)
               ou nom de topic direct si préfixé par 'topic:'
    """
    app = _get_firebase_app()
    if not app:
        return False

    if topic_key.startswith('topic:'):
        topic = topic_key[6:]
    else:
        topic = ROLE_TOPICS.get(topic_key, topic_key)

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data={str(k): str(v) for k, v in (data or {}).items()},
        topic=topic,
        android=messaging.AndroidConfig(priority='high'),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound='default')
            )
        ),
    )
    try:
        messaging.send(message, app=app)
        return True
    except Exception as e:
        logger.error(f"FCM send_to_topic({topic}) erreur : {e}")
        return False


def send_to_multiple_tokens(tokens: list, title: str, body: str, data: dict = None) -> dict:
    """Envoie une notification à plusieurs tokens. Retourne {success: int, failure: int}."""
    app = _get_firebase_app()
    if not app or not tokens:
        return {'success': 0, 'failure': 0}

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={str(k): str(v) for k, v in (data or {}).items()},
        tokens=tokens[:500],  # FCM limite à 500 tokens par batch
        android=messaging.AndroidConfig(priority='high'),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound='default')
            )
        ),
    )
    try:
        response = messaging.send_each_for_multicast(message, app=app)
        return {'success': response.success_count, 'failure': response.failure_count}
    except Exception as e:
        logger.error(f"FCM send_to_multiple_tokens erreur : {e}")
        return {'success': 0, 'failure': len(tokens)}
