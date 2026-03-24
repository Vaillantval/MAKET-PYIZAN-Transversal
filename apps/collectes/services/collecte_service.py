from django.db import transaction
from django.utils import timezone
from apps.collectes.models import Collecte, ParticipationCollecte


class CollecteService:
    @staticmethod
    @transaction.atomic
    def planifier_collecte(zone, point_collecte, date_planifiee, collecteur=None, heure_debut=None, heure_fin=None, notes=''):
        collecte = Collecte.objects.create(
            zone=zone,
            point_collecte=point_collecte,
            date_planifiee=date_planifiee,
            collecteur=collecteur,
            heure_debut=heure_debut,
            heure_fin=heure_fin,
            notes=notes,
        )
        return collecte

    @staticmethod
    @transaction.atomic
    def inscrire_producteur(collecte, producteur, quantite_prevue=0, notes=''):
        if collecte.statut not in [Collecte.Statut.PLANIFIEE, Collecte.Statut.EN_COURS]:
            raise ValueError("Impossible de s'inscrire a une collecte qui n'est pas planifiee ou en cours.")
        participation, created = ParticipationCollecte.objects.get_or_create(
            collecte=collecte,
            producteur=producteur,
            defaults={'quantite_prevue': quantite_prevue, 'notes': notes},
        )
        if not created:
            participation.quantite_prevue = quantite_prevue
            participation.notes = notes
            participation.save()
        return participation

    @staticmethod
    @transaction.atomic
    def demarrer_collecte(collecte, effectue_par=None):
        if collecte.statut != Collecte.Statut.PLANIFIEE:
            raise ValueError("Seules les collectes planifiees peuvent etre demarrees.")
        collecte.statut         = Collecte.Statut.EN_COURS
        collecte.date_debut_reel = timezone.now()
        collecte.save()
        return collecte

    @staticmethod
    @transaction.atomic
    def terminer_collecte(collecte, rapport=''):
        if collecte.statut != Collecte.Statut.EN_COURS:
            raise ValueError("Seules les collectes en cours peuvent etre terminees.")
        collecte.statut       = Collecte.Statut.TERMINEE
        collecte.date_fin_reel = timezone.now()
        collecte.rapport      = rapport
        collecte.save()
        return collecte

    @staticmethod
    @transaction.atomic
    def enregistrer_collecte_producteur(participation, quantite_collectee, statut=ParticipationCollecte.Statut.PRESENT):
        participation.quantite_collectee = quantite_collectee
        participation.statut             = statut
        participation.save()
        return participation

    @staticmethod
    def get_collectes_a_venir(days=7):
        from datetime import timedelta
        today = timezone.now().date()
        limit = today + timedelta(days=days)
        return Collecte.objects.filter(
            statut=Collecte.Statut.PLANIFIEE,
            date_planifiee__range=[today, limit]
        ).select_related('zone', 'point_collecte', 'collecteur')

    @staticmethod
    def get_collectes_en_retard():
        today = timezone.now().date()
        return Collecte.objects.filter(
            statut__in=[Collecte.Statut.PLANIFIEE, Collecte.Statut.EN_COURS],
            date_planifiee__lt=today
        ).select_related('zone', 'collecteur')
