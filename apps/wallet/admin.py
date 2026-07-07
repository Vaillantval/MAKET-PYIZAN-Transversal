from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html

from apps.wallet.models import (
    BonCadeau,
    Wallet,
    WalletRecharge,
    WalletRetrait,
    WalletTransaction,
)
from apps.wallet.services import WalletError, WalletService


class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    can_delete = False
    readonly_fields = ('type', 'montant', 'solde_apres', 'commande',
                       'description', 'reference', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'role_user', 'solde', 'is_active', 'updated_at')
    list_display_links = ('user',)
    list_filter = ('is_active', 'user__role')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('solde', 'created_at', 'updated_at')
    inlines = [WalletTransactionInline]

    @admin.display(description='Rôle')
    def role_user(self, obj):
        return obj.user.get_role_display()

    def has_delete_permission(self, request, obj=None):
        # Un wallet avec historique ne se supprime pas — désactivez-le.
        return False


class WalletAjustementForm(forms.ModelForm):
    """Ajustement manuel : montant signé + description, le reste est calculé."""

    class Meta:
        model = WalletTransaction
        fields = ('wallet', 'montant', 'description')

    def clean_montant(self):
        montant = self.cleaned_data['montant']
        if montant == 0:
            raise forms.ValidationError("Le montant ne peut pas être nul.")
        return montant


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'type', 'montant', 'solde_apres',
                    'commande', 'description', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('wallet__user__username', 'wallet__user__email',
                     'description', 'reference')
    date_hierarchy = 'created_at'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # ledger immuable
            return [f.name for f in self.model._meta.fields]
        return []

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs['form'] = WalletAjustementForm
        return super().get_form(request, obj, **kwargs)

    def has_change_permission(self, request, obj=None):
        return obj is None

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # L'ajout passe par le service pour verrouiller le solde et
        # calculer solde_apres — jamais par un save() direct.
        if change:
            return
        try:
            if obj.montant > 0:
                WalletService.crediter(
                    obj.wallet, obj.montant,
                    type_tx=WalletTransaction.Type.AJUSTEMENT,
                    description=obj.description or 'Ajustement manuel (admin)',
                )
            else:
                WalletService._appliquer(
                    obj.wallet, obj.montant, WalletTransaction.Type.AJUSTEMENT,
                    description=obj.description or 'Ajustement manuel (admin)',
                    autoriser_negatif=True,
                )
            messages.success(request, "Ajustement appliqué au wallet.")
        except WalletError as e:
            messages.error(request, f"Ajustement refusé : {e}")

    def response_add(self, request, obj, post_url_continue=None):
        # L'objet affiché n'a pas été sauvegardé directement (save_model
        # délègue au service) — on renvoie simplement vers la liste.
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(reverse('admin:wallet_wallettransaction_changelist'))


@admin.register(WalletRecharge)
class WalletRechargeAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'montant', 'methode', 'statut',
                    'affiche_preuve', 'created_at')
    list_filter = ('methode', 'statut', 'created_at')
    search_fields = ('wallet__user__username', 'wallet__user__email', 'reference_plopplop')
    readonly_fields = ('wallet', 'montant', 'methode', 'reference_plopplop',
                       'preuve_image', 'transaction', 'created_at', 'updated_at')
    actions = ['valider_et_crediter', 'rejeter_recharge']

    @admin.display(description='Preuve')
    def affiche_preuve(self, obj):
        if obj.preuve_image:
            return format_html(
                '<a href="{}" target="_blank" style="color:#2e7d32;font-weight:600;">'
                '<i class="fas fa-image"></i> Voir preuve</a>',
                obj.preuve_image.url,
            )
        return '—'

    @admin.action(description='Valider la preuve et créditer le wallet')
    def valider_et_crediter(self, request, queryset):
        creditees, ignorees = 0, 0
        for recharge in queryset:
            est_hors_ligne = recharge.methode == WalletRecharge.Methode.HORS_LIGNE
            statut_ok = recharge.statut in (
                WalletRecharge.Statut.PREUVE_SOUMISE, WalletRecharge.Statut.EN_ATTENTE,
            )
            if not est_hors_ligne or not statut_ok:
                ignorees += 1
                continue
            try:
                tx = WalletService.completer_recharge(
                    recharge, reference=f"hors-ligne-{recharge.pk}",
                )
                if tx:
                    creditees += 1
                    try:
                        from apps.wallet.tasks import task_notifier_recharge_validee
                        task_notifier_recharge_validee.delay(recharge.pk)
                    except Exception:
                        pass
                else:
                    ignorees += 1  # déjà créditée
            except WalletError as e:
                self.message_user(request, f"Recharge #{recharge.pk} : {e}", level=messages.ERROR)
        if creditees:
            self.message_user(request, f"{creditees} recharge(s) créditée(s).", level=messages.SUCCESS)
        if ignorees:
            self.message_user(
                request,
                f"{ignorees} recharge(s) ignorée(s) (déjà traitée(s) ou non hors ligne).",
                level=messages.WARNING,
            )

    @admin.action(description='Rejeter la recharge (preuve invalide)')
    def rejeter_recharge(self, request, queryset):
        rejetees = 0
        for recharge in queryset:
            if recharge.statut not in (
                WalletRecharge.Statut.PREUVE_SOUMISE, WalletRecharge.Statut.EN_ATTENTE,
            ):
                continue
            recharge.statut = WalletRecharge.Statut.REJETEE
            recharge.save(update_fields=['statut', 'updated_at'])
            rejetees += 1
            try:
                from apps.wallet.tasks import task_notifier_recharge_rejetee
                task_notifier_recharge_rejetee.delay(recharge.pk)
            except Exception:
                pass
        if rejetees:
            self.message_user(request, f"{rejetees} recharge(s) rejetée(s).", level=messages.SUCCESS)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class WalletRetraitForm(forms.ModelForm):
    """Seuls la preuve de transfert et la note restent éditables par l'admin."""

    class Meta:
        model = WalletRetrait
        fields = ('preuve_transfert', 'note_admin')


@admin.register(WalletRetrait)
class WalletRetraitAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'montant', 'canal', 'numero_telephone',
                    'statut', 'affiche_preuve', 'traite_par', 'created_at')
    list_filter = ('canal', 'statut', 'created_at')
    search_fields = ('wallet__user__username', 'wallet__user__email', 'numero_telephone')
    readonly_fields = ('wallet', 'montant', 'canal', 'numero_telephone', 'statut',
                       'traite_par', 'date_traitement', 'transaction',
                       'transaction_reprise', 'created_at', 'updated_at')
    form = WalletRetraitForm
    actions = ['marquer_paye', 'rejeter_retrait']

    def get_fields(self, request, obj=None):
        return ('wallet', 'montant', 'canal', 'numero_telephone', 'statut',
                'preuve_transfert', 'note_admin', 'traite_par', 'date_traitement',
                'transaction', 'transaction_reprise', 'created_at', 'updated_at')

    @admin.display(description='Preuve transfert')
    def affiche_preuve(self, obj):
        if obj.preuve_transfert:
            return format_html(
                '<a href="{}" target="_blank" style="color:#2e7d32;font-weight:600;">'
                '<i class="fas fa-image"></i> Voir preuve</a>',
                obj.preuve_transfert.url,
            )
        return '—'

    @admin.action(description='Marquer payé (transfert effectué)')
    def marquer_paye(self, request, queryset):
        payes, ignores = 0, 0
        for retrait in queryset:
            if WalletService.payer_retrait(retrait, traite_par=request.user):
                payes += 1
                try:
                    from apps.wallet.tasks import task_notifier_retrait_paye
                    task_notifier_retrait_paye.delay(retrait.pk)
                except Exception:
                    pass
            else:
                ignores += 1
        if payes:
            self.message_user(request, f"{payes} retrait(s) marqué(s) payé(s).", level=messages.SUCCESS)
        if ignores:
            self.message_user(request, f"{ignores} retrait(s) déjà traité(s).", level=messages.WARNING)

    @admin.action(description='Rejeter et re-créditer le wallet')
    def rejeter_retrait(self, request, queryset):
        rejetes, ignores = 0, 0
        for retrait in queryset:
            try:
                if WalletService.rejeter_retrait(retrait, traite_par=request.user):
                    rejetes += 1
                    try:
                        from apps.wallet.tasks import task_notifier_retrait_rejete
                        task_notifier_retrait_rejete.delay(retrait.pk)
                    except Exception:
                        pass
                else:
                    ignores += 1
            except WalletError as e:
                self.message_user(request, f"Retrait #{retrait.pk} : {e}", level=messages.ERROR)
        if rejetes:
            self.message_user(request, f"{rejetes} retrait(s) rejeté(s) et re-crédité(s).", level=messages.SUCCESS)
        if ignores:
            self.message_user(request, f"{ignores} retrait(s) déjà traité(s).", level=messages.WARNING)

    def has_add_permission(self, request):
        # Les retraits se créent via la demande du producteur (le débit doit
        # passer par le service), jamais à la main.
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BonCadeau)
class BonCadeauAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'montant', 'statut', 'achete_par',
                    'email_destinataire', 'encaisse_par', 'date_expiration', 'created_at')
    list_filter = ('statut', 'created_at')
    search_fields = ('code', 'achete_par__username', 'achete_par__email',
                     'email_destinataire', 'encaisse_par__username')
    readonly_fields = ('code', 'montant', 'achete_par', 'encaisse_par',
                       'date_encaissement', 'reference_plopplop',
                       'created_at', 'updated_at')
    actions = ['annuler_bons', 'renvoyer_email_code']

    @admin.action(description='Annuler les bons sélectionnés (non utilisés)')
    def annuler_bons(self, request, queryset):
        annules = queryset.filter(
            statut__in=(BonCadeau.Statut.ATTENTE_PAIEMENT, BonCadeau.Statut.ACTIF),
        ).update(statut=BonCadeau.Statut.ANNULE)
        self.message_user(request, f"{annules} bon(s) annulé(s).", level=messages.SUCCESS)

    @admin.action(description="Renvoyer l'email du code (bons actifs)")
    def renvoyer_email_code(self, request, queryset):
        envoyes = 0
        for bon in queryset.filter(statut=BonCadeau.Statut.ACTIF):
            try:
                from apps.wallet.tasks import task_envoyer_bon_cadeau
                task_envoyer_bon_cadeau.delay(bon.pk)
                envoyes += 1
            except Exception as e:
                self.message_user(request, f"Bon {bon.code} : {e}", level=messages.ERROR)
        if envoyes:
            self.message_user(request, f"{envoyes} email(s) planifié(s).", level=messages.SUCCESS)

    def has_add_permission(self, request):
        # Les bons se créent via l'achat (paiement vérifié), pas à la main.
        return False

    def has_delete_permission(self, request, obj=None):
        return False
