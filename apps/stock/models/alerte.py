from django.db import models
from django.conf import settings


class AlerteStock(models.Model):
    class Niveau(models.TextChoices):
        INFO     = 'info',     'Information'
        WARNING  = 'warning',  'Avertissement'
        CRITIQUE = 'critique', 'Critique — Stock tres faible'
        EPUISE   = 'epuise',   'Epuise'

    class Statut(models.TextChoices):
        NOUVELLE = 'nouvelle', 'Nouvelle'
        VUE      = 'vue',      'Vue'
        EN_COURS = 'en_cours', 'En cours de traitement'
        RESOLUE  = 'resolue',  'Resolue'
        IGNOREE  = 'ignoree',  'Ignoree'

    produit         = models.ForeignKey('catalog.Produit', on_delete=models.CASCADE, related_name='alertes_stock')
    lot             = models.ForeignKey('stock.Lot', on_delete=models.CASCADE, null=True, blank=True, related_name='alertes')
    niveau          = models.CharField(max_length=20, choices=Niveau.choices, default=Niveau.WARNING)
    statut          = models.CharField(max_length=20, choices=Statut.choices, default=Statut.NOUVELLE)
    stock_actuel    = models.PositiveIntegerField()
    seuil           = models.PositiveIntegerField()
    message         = models.TextField()
    traitee_par     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='alertes_traitees')
    note_traitement = models.TextField(blank=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Alerte stock'
        verbose_name_plural = 'Alertes stock'
        ordering            = ['-created_at']

    def __str__(self):
        return f"[{self.get_niveau_display()}] {self.produit.nom} — Stock: {self.stock_actuel} / Seuil: {self.seuil}"

    @classmethod
    def verifier_et_creer(cls, produit):
        stock = produit.stock_disponible
        seuil = produit.seuil_alerte
        if stock == 0:
            niveau  = cls.Niveau.EPUISE
            message = f"Le produit '{produit.nom}' de {produit.producteur.user.get_full_name()} est completement epuise."
        elif stock <= seuil * 0.5:
            niveau  = cls.Niveau.CRITIQUE
            message = f"Stock critique pour '{produit.nom}' : {stock} unites restantes (seuil : {seuil})."
        elif stock <= seuil:
            niveau  = cls.Niveau.WARNING
            message = f"Stock faible pour '{produit.nom}' : {stock} unites restantes (seuil : {seuil})."
        else:
            cls.objects.filter(produit=produit, statut__in=[cls.Statut.NOUVELLE, cls.Statut.VUE]).update(statut=cls.Statut.RESOLUE)
            return None
        existe = cls.objects.filter(produit=produit, niveau=niveau, statut__in=[cls.Statut.NOUVELLE, cls.Statut.VUE]).exists()
        if not existe:
            return cls.objects.create(produit=produit, niveau=niveau, statut=cls.Statut.NOUVELLE, stock_actuel=stock, seuil=seuil, message=message)
        return None
