"""
Report generators for PDF and CSV exports
"""
import json
from datetime import datetime, timedelta
from io import BytesIO, StringIO
import csv

from django.db.models import Sum, Count, Q
from django.utils import timezone


class ReportDataGenerator:
    """Generate report data for a given date range"""

    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date

    def get_kpis(self):
        """Get KPIs for the date range"""
        from apps.accounts.models import CustomUser, Producteur, Acheteur
        from apps.catalog.models import Produit
        from apps.orders.models import Commande
        from apps.payments.models import Paiement
        from apps.stock.models import AlerteStock

        total_commandes = Commande.objects.filter(
            created_at__date__gte=self.start_date,
            created_at__date__lte=self.end_date
        ).count()

        ca_total = Commande.objects.filter(
            created_at__date__gte=self.start_date,
            created_at__date__lte=self.end_date,
            statut_paiement='paye'
        ).aggregate(total=Sum('total'))['total'] or 0

        return {
            'periode_debut': self.start_date.strftime('%d/%m/%Y'),
            'periode_fin': self.end_date.strftime('%d/%m/%Y'),
            'total_utilisateurs': CustomUser.objects.filter(is_active=True).count(),
            'total_producteurs': Producteur.objects.filter(statut='actif').count(),
            'total_produits': Produit.objects.filter(is_active=True).count(),
            'total_commandes': total_commandes,
            'ca_total': float(ca_total),
            'alertes_stock': AlerteStock.objects.filter(statut__in=['nouvelle', 'vue']).count(),
            'paiements_en_attente': Paiement.objects.filter(
                statut__in=['initie', 'en_attente', 'soumis']
            ).count(),
        }

    def get_daily_sales(self):
        """Get daily sales data"""
        from apps.orders.models import Commande

        data = []
        current_date = self.start_date
        while current_date <= self.end_date:
            ca = Commande.objects.filter(
                created_at__date=current_date,
                statut_paiement='paye'
            ).aggregate(total=Sum('total'))['total'] or 0
            data.append({
                'date': current_date.strftime('%d/%m/%Y'),
                'ca': float(ca)
            })
            current_date += timedelta(days=1)
        return data

    def get_monthly_sales(self):
        """Get monthly sales data for 12 months before start_date"""
        from apps.orders.models import Commande

        data = []
        for i in range(11, -1, -1):
            month_start = (self.start_date.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            ca = Commande.objects.filter(
                created_at__year=month_start.year,
                created_at__month=month_start.month,
                statut_paiement='paye'
            ).aggregate(total=Sum('total'))['total'] or 0
            data.append({
                'mois': month_start.strftime('%b %Y'),
                'ca': float(ca)
            })
        return data

    def get_orders_by_status(self):
        """Get orders grouped by status"""
        from apps.orders.models import Commande

        statuts = Commande.objects.filter(
            created_at__date__gte=self.start_date,
            created_at__date__lte=self.end_date
        ).values('statut').annotate(count=Count('id')).order_by('-count')
        
        return [{'statut': s['statut'], 'count': s['count']} for s in statuts]

    def get_payments_by_type(self):
        """Get payments grouped by type"""
        from apps.payments.models import Paiement

        types = Paiement.objects.filter(
            created_at__date__gte=self.start_date,
            created_at__date__lte=self.end_date,
            statut='confirme'
        ).values('type_paiement').annotate(
            count=Count('id'),
            total=Sum('montant')
        ).order_by('-total')
        
        return list(types)

    def get_top_products(self, limit=10):
        """Get top products by revenue"""
        from apps.orders.models import CommandeDetail, Commande

        return CommandeDetail.objects.filter(
            commande__created_at__date__gte=self.start_date,
            commande__created_at__date__lte=self.end_date,
            commande__statut_paiement='paye'
        ).values('produit__nom', 'produit__slug').annotate(
            total_vendu=Sum('quantite'),
            ca=Sum('sous_total')
        ).order_by('-ca')[:limit]

    def get_top_producers(self, limit=10):
        """Get top producers by revenue"""
        from apps.accounts.models import Producteur

        producers = Producteur.objects.annotate(
            nb_cmd=Count('commandes_recues', filter=Q(
                commandes_recues__created_at__date__gte=self.start_date,
                commandes_recues__created_at__date__lte=self.end_date
            )),
            ca=Sum('commandes_recues__total', filter=Q(
                commandes_recues__statut_paiement='paye',
                commandes_recues__created_at__date__gte=self.start_date,
                commandes_recues__created_at__date__lte=self.end_date
            ))
        ).filter(ca__isnull=False).order_by('-ca')[:limit]
        
        return [{
            'name': p.user.get_full_name() if p.user else str(p),
            'nb_cmd': p.nb_cmd or 0,
            'ca': p.ca or 0,
        } for p in producers]

    def get_top_buyers(self, limit=10):
        """Get top buyers by spending"""
        from apps.accounts.models import Acheteur

        buyers = Acheteur.objects.annotate(
            nb_cmd=Count('commandes', filter=Q(
                commandes__created_at__date__gte=self.start_date,
                commandes__created_at__date__lte=self.end_date
            )),
            depense=Sum('commandes__total', filter=Q(
                commandes__statut_paiement='paye',
                commandes__created_at__date__gte=self.start_date,
                commandes__created_at__date__lte=self.end_date
            ))
        ).filter(depense__isnull=False).order_by('-depense')[:limit]
        
        return [{
            'name': b.user.get_full_name() if b.user else str(b),
            'nb_cmd': b.nb_cmd or 0,
            'depense': b.depense or 0,
        } for b in buyers]

    def get_sales_by_category(self):
        """Get sales grouped by category"""
        from apps.orders.models import CommandeDetail, Commande

        return CommandeDetail.objects.filter(
            commande__created_at__date__gte=self.start_date,
            commande__created_at__date__lte=self.end_date,
            commande__statut_paiement='paye'
        ).values('produit__categorie__nom').annotate(
            ca=Sum('sous_total'),
            nb=Count('id')
        ).order_by('-ca')[:8]


class PDFReportGenerator:
    """Generate PDF reports using reportlab"""

    # Palette de couleurs
    C_GREEN      = '#1a6b2f'
    C_GREEN_LIGHT = '#27ae60'
    C_GREEN_BG   = '#f0faf3'
    C_ORANGE     = '#e67e22'
    C_ORANGE_BG  = '#fef9f0'
    C_BLUE       = '#2980b9'
    C_BLUE_BG    = '#eaf4fb'
    C_RED        = '#e74c3c'
    C_RED_BG     = '#fdf0f0'
    C_PURPLE     = '#8e44ad'
    C_GRAY       = '#7f8c8d'
    C_LIGHT_GRAY = '#ecf0f1'
    C_DARK       = '#2c3e50'
    C_ROW_ALT    = '#f8fafb'

    CHART_COLORS = [
        '#27ae60', '#3498db', '#e67e22', '#9b59b6',
        '#e74c3c', '#1abc9c', '#f39c12', '#2980b9',
        '#d35400', '#16a085',
    ]

    def __init__(self, report_data):
        self.report_data = report_data

    # ------------------------------------------------------------------ #
    #  Entrée principale                                                   #
    # ------------------------------------------------------------------ #
    def generate(self):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm, inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        except ImportError:
            raise ImportError("reportlab est requis : pip install reportlab")

        self._import_rl()

        buffer = BytesIO()
        doc = self._make_doc(buffer)

        elements = []
        elements += self._cover_page()
        elements.append(self._rl['PageBreak']())
        elements += self._section_kpis()
        elements += self._section_ventes_mensuelles()
        elements += self._section_ventes_journalieres()
        elements.append(self._rl['PageBreak']())
        elements += self._section_commandes_statut()
        elements += self._section_paiements()
        elements += self._section_categories()
        elements.append(self._rl['PageBreak']())
        elements += self._section_top_produits()
        elements += self._section_top_producteurs()
        elements += self._section_top_acheteurs()

        doc.build(
            elements,
            onFirstPage=self._draw_page_frame,
            onLaterPages=self._draw_page_frame,
        )
        buffer.seek(0)
        return buffer

    # ------------------------------------------------------------------ #
    #  Imports reportlab centralisés                                       #
    # ------------------------------------------------------------------ #
    def _import_rl(self):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm, inch
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph,
            Spacer, PageBreak, HRFlowable, KeepTogether,
        )
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
        from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics.charts.legends import Legend

        self._rl = {
            'A4': A4, 'cm': cm, 'inch': inch,
            'getSampleStyleSheet': getSampleStyleSheet,
            'ParagraphStyle': ParagraphStyle,
            'Table': Table, 'TableStyle': TableStyle,
            'Paragraph': Paragraph, 'Spacer': Spacer,
            'PageBreak': PageBreak, 'HRFlowable': HRFlowable,
            'KeepTogether': KeepTogether,
            'colors': colors,
            'TA_CENTER': TA_CENTER, 'TA_LEFT': TA_LEFT, 'TA_RIGHT': TA_RIGHT,
            'Drawing': Drawing, 'Rect': Rect, 'String': String,
            'Line': Line, 'Circle': Circle,
            'VerticalBarChart': VerticalBarChart,
            'HorizontalBarChart': HorizontalBarChart,
            'Pie': Pie, 'Legend': Legend,
        }

        styles = getSampleStyleSheet()
        C = self._rl['colors']

        self._styles = {
            'normal': ParagraphStyle('RpNormal', parent=styles['Normal'],
                                     fontSize=9, leading=13, textColor=C.HexColor(self.C_DARK)),
            'small':  ParagraphStyle('RpSmall', parent=styles['Normal'],
                                     fontSize=8, leading=11, textColor=C.HexColor(self.C_GRAY)),
            'h1': ParagraphStyle('RpH1', parent=styles['Heading1'],
                                 fontSize=22, textColor=C.HexColor(self.C_GREEN),
                                 alignment=TA_CENTER, spaceAfter=4),
            'h2': ParagraphStyle('RpH2', parent=styles['Heading2'],
                                 fontSize=13, textColor=C.HexColor(self.C_GREEN),
                                 spaceBefore=14, spaceAfter=6,
                                 borderPad=4),
            'h3': ParagraphStyle('RpH3', parent=styles['Heading3'],
                                 fontSize=10, textColor=C.HexColor(self.C_DARK),
                                 spaceBefore=6, spaceAfter=4, fontName='Helvetica-Bold'),
            'center': ParagraphStyle('RpCenter', parent=styles['Normal'],
                                     fontSize=9, leading=13, alignment=TA_CENTER,
                                     textColor=C.HexColor(self.C_DARK)),
            'kpi_val': ParagraphStyle('RpKpiVal', parent=styles['Normal'],
                                      fontSize=22, fontName='Helvetica-Bold',
                                      alignment=TA_CENTER, textColor=C.HexColor(self.C_GREEN),
                                      leading=26),
            'kpi_lbl': ParagraphStyle('RpKpiLbl', parent=styles['Normal'],
                                      fontSize=8, alignment=TA_CENTER,
                                      textColor=C.HexColor(self.C_GRAY),
                                      fontName='Helvetica-Bold'),
            'cover_sub': ParagraphStyle('RpCoverSub', parent=styles['Normal'],
                                        fontSize=11, alignment=TA_CENTER,
                                        textColor=C.HexColor(self.C_GRAY)),
            'cover_title': ParagraphStyle('RpCoverTitle', parent=styles['Heading1'],
                                          fontSize=32, textColor=C.HexColor(self.C_GREEN),
                                          alignment=TA_CENTER, spaceAfter=8,
                                          fontName='Helvetica-Bold'),
            'table_header': ParagraphStyle('RpTblHdr', parent=styles['Normal'],
                                           fontSize=9, fontName='Helvetica-Bold',
                                           textColor=C.white, alignment=TA_CENTER),
            'badge_green':  ParagraphStyle('RpBgGr', parent=styles['Normal'],
                                           fontSize=8, textColor=C.HexColor(self.C_GREEN),
                                           fontName='Helvetica-Bold', alignment=TA_CENTER),
            'badge_orange': ParagraphStyle('RpBgOr', parent=styles['Normal'],
                                           fontSize=8, textColor=C.HexColor(self.C_ORANGE),
                                           fontName='Helvetica-Bold', alignment=TA_CENTER),
            'badge_red':    ParagraphStyle('RpBgRd', parent=styles['Normal'],
                                           fontSize=8, textColor=C.HexColor(self.C_RED),
                                           fontName='Helvetica-Bold', alignment=TA_CENTER),
        }

    def _make_doc(self, buffer):
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate
        from reportlab.lib.units import cm
        return SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.8*cm,
            leftMargin=1.8*cm,
            topMargin=2.2*cm,
            bottomMargin=2*cm,
        )

    # ------------------------------------------------------------------ #
    #  Header / Footer de chaque page                                      #
    # ------------------------------------------------------------------ #
    def _draw_page_frame(self, canvas, doc):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib import colors

        W, H = A4
        canvas.saveState()

        # Bande verte en haut
        canvas.setFillColor(colors.HexColor(self.C_GREEN))
        canvas.rect(0, H - 1.2*cm, W, 1.2*cm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawString(1.8*cm, H - 0.85*cm, 'MAKÈT PEYIZAN')
        canvas.setFont('Helvetica', 8)
        kpis = self.report_data['kpis']
        canvas.drawRightString(
            W - 1.8*cm, H - 0.85*cm,
            f"Rapport du {kpis['periode_debut']} au {kpis['periode_fin']}"
        )

        # Ligne et pagination en bas
        canvas.setStrokeColor(colors.HexColor(self.C_LIGHT_GRAY))
        canvas.setLineWidth(0.5)
        canvas.line(1.8*cm, 1.5*cm, W - 1.8*cm, 1.5*cm)
        canvas.setFillColor(colors.HexColor(self.C_GRAY))
        canvas.setFont('Helvetica', 7.5)
        from datetime import date
        canvas.drawString(1.8*cm, 0.8*cm, f"Généré le {date.today().strftime('%d/%m/%Y')}")
        canvas.drawRightString(W - 1.8*cm, 0.8*cm, f"Page {doc.page}")

        canvas.restoreState()

    # ------------------------------------------------------------------ #
    #  Helpers visuels                                                     #
    # ------------------------------------------------------------------ #
    def _section_title(self, text, color=None):
        """Retourne un titre de section avec barre latérale colorée."""
        color = color or self.C_GREEN
        rl = self._rl
        C = rl['colors']
        W_page = 17.4 * rl['cm']  # largeur utile A4 - marges

        drawing = rl['Drawing'](W_page, 22)
        drawing.add(rl['Rect'](0, 6, 4, 14, fillColor=C.HexColor(color), strokeColor=None))
        drawing.add(rl['String'](10, 7, text,
                                  fontName='Helvetica-Bold', fontSize=13,
                                  fillColor=C.HexColor(self.C_DARK)))
        return drawing

    def _styled_table(self, data, col_widths, header_color=None, number_cols=None):
        """Table avec header coloré et lignes alternées."""
        rl = self._rl
        C  = rl['colors']
        hc = C.HexColor(header_color or self.C_GREEN)
        number_cols = number_cols or []

        style = [
            ('BACKGROUND', (0, 0), (-1, 0), hc),
            ('TEXTCOLOR',  (0, 0), (-1, 0), C.white),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0, 0), (-1, 0), 9),
            ('ALIGN',      (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',  (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('FONTSIZE',   (0, 1), (-1, -1), 8.5),
            ('FONTNAME',   (0, 1), (-1, -1), 'Helvetica'),
            ('TEXTCOLOR',  (0, 1), (-1, -1), C.HexColor(self.C_DARK)),
            ('GRID',       (0, 0), (-1, -1), 0.3, C.HexColor(self.C_LIGHT_GRAY)),
            ('LINEBELOW',  (0, 0), (-1, 0), 0, C.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C.white, C.HexColor(self.C_ROW_ALT)]),
            ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ]
        for col in number_cols:
            style.append(('ALIGN', (col, 1), (col, -1), 'RIGHT'))

        return rl['Table'](data, colWidths=col_widths, style=rl['TableStyle'](style))

    @staticmethod
    def _safe(values):
        """Convertit une liste en floats sans None — indispensable pour les graphiques."""
        return [float(v) if v is not None else 0.0 for v in values]

    @staticmethod
    def _safe_f(v):
        """Float safe depuis Decimal / None."""
        try:
            return float(v) if v is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _chart_max(values, fallback=1.0):
        """max sécurisé sur une liste qui peut contenir None."""
        clean = [v for v in values if v is not None]
        return max(clean) if clean else fallback

    @staticmethod
    def _step(max_v, divisions=5):
        """Calcule un valueStep toujours > 0."""
        s = max_v / divisions if max_v > 0 else 1.0
        return max(s, 0.1)

    def _kpi_card(self, label, value, color, width):
        """Mini carte KPI dans une cellule de tableau."""
        rl = self._rl
        C  = rl['colors']
        bg = C.HexColor({
            self.C_GREEN:  self.C_GREEN_BG,
            self.C_ORANGE: self.C_ORANGE_BG,
            self.C_BLUE:   self.C_BLUE_BG,
            self.C_RED:    self.C_RED_BG,
            self.C_PURPLE: '#f5eefa',
        }.get(color, self.C_GREEN_BG))
        border = C.HexColor(color)

        inner = rl['Table'](
            [[rl['Paragraph'](str(value), self._styles['kpi_val'])],
             [rl['Paragraph'](label,      self._styles['kpi_lbl'])]],
            colWidths=[width - 0.4*rl['cm']],
            style=rl['TableStyle']([
                ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
                ('TOPPADDING',    (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND',    (0, 0), (-1, -1), bg),
                ('LINEAFTER',     (0, 0), (0, -1), 3, border),
                ('LINEBEFORE',    (0, 0), (0, -1), 3, border),
            ]),
        )
        return inner

    # ------------------------------------------------------------------ #
    #  Page de couverture                                                  #
    # ------------------------------------------------------------------ #
    def _cover_page(self):
        rl = self._rl
        C  = rl['colors']
        cm = rl['cm']
        W  = 17.4 * cm
        els = []

        els.append(rl['Spacer'](1, 3.5*cm))

        # Logo / icône stylisé
        d = rl['Drawing'](W, 80)
        d.add(rl['Rect'](W/2 - 35, 10, 70, 60,
                          fillColor=C.HexColor(self.C_GREEN), strokeColor=None, rx=12))
        d.add(rl['String'](W/2 - 12, 32, 'MP',
                            fontName='Helvetica-Bold', fontSize=28,
                            fillColor=C.white))
        els.append(d)
        els.append(rl['Spacer'](1, 0.5*cm))

        els.append(rl['Paragraph']('MAKÈT PEYIZAN', self._styles['cover_title']))
        els.append(rl['Paragraph']('Rapport d\'Analyse et de Performance', self._styles['cover_sub']))
        els.append(rl['Spacer'](1, 0.5*cm))

        # Ligne décorative
        d2 = rl['Drawing'](W, 8)
        d2.add(rl['Rect'](W/2 - 60, 3, 120, 3,
                           fillColor=C.HexColor(self.C_GREEN_LIGHT), strokeColor=None))
        els.append(d2)
        els.append(rl['Spacer'](1, 0.5*cm))

        kpis = self.report_data['kpis']
        els.append(rl['Paragraph'](
            f"Période : <b>{kpis['periode_debut']}</b> — <b>{kpis['periode_fin']}</b>",
            self._styles['cover_sub']
        ))
        els.append(rl['Spacer'](1, 3*cm))

        # Bloc résumé rapide
        from datetime import date
        summary = [
            ['', ''],
            [rl['Paragraph']('<b>Commandes sur la période</b>', self._styles['normal']),
             rl['Paragraph'](f"<b>{kpis['total_commandes']}</b>", self._styles['normal'])],
            [rl['Paragraph']('<b>Chiffre d\'affaires (HTG)</b>', self._styles['normal']),
             rl['Paragraph'](f"<b>{kpis['ca_total']:,.0f}</b>", self._styles['normal'])],
            [rl['Paragraph']('<b>Producteurs actifs</b>', self._styles['normal']),
             rl['Paragraph'](f"<b>{kpis['total_producteurs']}</b>", self._styles['normal'])],
            [rl['Paragraph']('<b>Alertes stock actives</b>', self._styles['normal']),
             rl['Paragraph'](f"<b>{kpis['alertes_stock']}</b>", self._styles['normal'])],
            ['', ''],
        ]
        t = rl['Table'](summary, colWidths=[8*cm, 4*cm],
                        style=rl['TableStyle']([
                            ('ALIGN',         (1, 0), (1, -1), 'RIGHT'),
                            ('BACKGROUND',    (0, 0), (-1, 0), C.HexColor(self.C_GREEN)),
                            ('BACKGROUND',    (0, -1), (-1, -1), C.HexColor(self.C_GREEN)),
                            ('LINEBELOW',     (0, 1), (-1, -2), 0.5, C.HexColor(self.C_LIGHT_GRAY)),
                            ('TOPPADDING',    (0, 0), (-1, -1), 7),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                            ('LEFTPADDING',   (0, 0), (-1, -1), 14),
                            ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
                        ]))

        # Centrer le tableau
        wrapper = rl['Table']([[t]], colWidths=[W],
                               style=rl['TableStyle']([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        els.append(wrapper)

        els.append(rl['Spacer'](1, 2*cm))
        els.append(rl['Paragraph'](
            f"Document généré automatiquement le {date.today().strftime('%d/%m/%Y')}",
            self._styles['small']
        ))
        return els

    # ------------------------------------------------------------------ #
    #  Section KPIs                                                        #
    # ------------------------------------------------------------------ #
    def _section_kpis(self):
        rl = self._rl
        cm = rl['cm']
        W  = 17.4 * cm
        kpis = self.report_data['kpis']
        els  = []

        els.append(self._section_title('Indicateurs Clés de Performance'))
        els.append(rl['Spacer'](1, 0.3*cm))

        cw = (W - 3*0.3*cm) / 4
        row1 = [
            self._kpi_card('Utilisateurs actifs',   str(kpis['total_utilisateurs']), self.C_BLUE,   cw),
            self._kpi_card('Producteurs actifs',    str(kpis['total_producteurs']),  self.C_GREEN,  cw),
            self._kpi_card('Produits disponibles',  str(kpis['total_produits']),     self.C_GREEN,  cw),
            self._kpi_card('Commandes (période)',   str(kpis['total_commandes']),    self.C_ORANGE, cw),
        ]
        row2 = [
            self._kpi_card('CA total (HTG)',        f"{kpis['ca_total']:,.0f}",      self.C_GREEN,  cw),
            self._kpi_card('Alertes stock',         str(kpis['alertes_stock']),      self.C_RED,    cw),
            self._kpi_card('Paiements en attente',  str(kpis['paiements_en_attente']), self.C_ORANGE, cw),
            self._kpi_card('Produits / Producteur',
                           f"{round(kpis['total_produits'] / max(kpis['total_producteurs'], 1), 1)}",
                           self.C_PURPLE, cw),
        ]
        grid = rl['Table'](
            [row1, [rl['Spacer'](1, 0.25*cm)] * 4, row2],
            colWidths=[cw] * 4,
            style=rl['TableStyle']([
                ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN',     (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('LEFTPADDING',  (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ])
        )
        els.append(grid)
        els.append(rl['Spacer'](1, 0.5*cm))
        return els

    # ------------------------------------------------------------------ #
    #  Graphique : CA mensuel (12 mois)                                    #
    # ------------------------------------------------------------------ #
    def _section_ventes_mensuelles(self):
        rl  = self._rl
        C   = rl['colors']
        cm  = rl['cm']
        W   = 17.4 * cm
        els = []

        monthly = self.report_data['monthly_sales']
        if not monthly:
            return els

        els.append(self._section_title('Chiffre d\'Affaires — 12 Derniers Mois'))
        els.append(rl['Spacer'](1, 0.3*cm))

        labels = [m['mois'] for m in monthly]
        values = self._safe([m['ca'] for m in monthly])
        max_v  = self._chart_max(values)

        recap_w = 5.5 * cm
        spacer_w = 0.3 * cm
        chart_w  = W - recap_w - spacer_w          # = 11.6 cm — total = W exactement
        chart_h  = 5.5 * cm
        d = rl['Drawing'](chart_w, chart_h + 1.2*cm)

        bc = rl['VerticalBarChart']()
        bc.x, bc.y = 1.2*cm, 1.2*cm
        bc.width  = chart_w - 2*cm
        bc.height = chart_h - 0.8*cm
        bc.data   = [values]
        bc.categoryAxis.categoryNames = labels
        bc.categoryAxis.labels.angle  = 45
        bc.categoryAxis.labels.dy     = -10
        bc.categoryAxis.labels.fontSize = 6.5
        bc.categoryAxis.labels.textAnchor = 'end'
        bc.valueAxis.valueMin  = 0
        bc.valueAxis.valueMax  = max_v * 1.15
        bc.valueAxis.valueStep = self._step(max_v, 5)
        bc.valueAxis.labels.fontSize = 7
        bc.barSpacing = 1
        bc.bars[0].fillColor   = C.HexColor(self.C_GREEN_LIGHT)
        bc.bars[0].strokeColor = None
        d.add(bc)

        # Tableau récap à droite : top 3 mois (colWidths <= recap_w)
        sorted_m = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)[:3]
        recap = [['Mois', 'CA (HTG)']]
        for lbl, val in sorted_m:
            recap.append([lbl, f"{val:,.0f}"])
        t = self._styled_table(recap, [2.7*cm, 2.5*cm], header_color=self.C_GREEN_LIGHT, number_cols=[1])

        row = rl['Table']([[d, rl['Spacer'](spacer_w, 1), t]],
                          colWidths=[chart_w, spacer_w, recap_w],
                          style=rl['TableStyle']([
                              ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                              ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                              ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
                              ('TOPPADDING',    (0, 0), (-1, -1), 0),
                              ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                          ]))
        els.append(row)
        els.append(rl['Spacer'](1, 0.4*cm))
        return els

    # ------------------------------------------------------------------ #
    #  Graphique : CA journalier                                           #
    # ------------------------------------------------------------------ #
    def _section_ventes_journalieres(self):
        rl  = self._rl
        C   = rl['colors']
        cm  = rl['cm']
        W   = 17.4 * cm
        els = []

        daily = self.report_data['daily_sales']
        if not daily:
            return els

        # N'afficher qu'un label sur N pour éviter surcharge
        step   = max(1, len(daily) // 10)
        labels = [item['date'] if i % step == 0 else '' for i, item in enumerate(daily)]
        values = self._safe([item['ca'] for item in daily])
        max_v  = self._chart_max(values)

        els.append(self._section_title('Ventes Journalières — Période Sélectionnée'))
        els.append(rl['Spacer'](1, 0.3*cm))

        chart_w, chart_h = W, 4.5 * cm
        d = rl['Drawing'](chart_w, chart_h + 1.2*cm)

        bc = rl['VerticalBarChart']()
        bc.x, bc.y = 1.2*cm, 1.2*cm
        bc.width  = chart_w - 1.8*cm
        bc.height = chart_h - 0.5*cm
        bc.data   = [values]
        bc.categoryAxis.categoryNames = labels
        bc.categoryAxis.labels.angle  = 0
        bc.categoryAxis.labels.fontSize = 6
        bc.valueAxis.valueMin  = 0
        bc.valueAxis.valueMax  = max_v * 1.15
        bc.valueAxis.valueStep = self._step(max_v, 4)
        bc.valueAxis.labels.fontSize = 7
        bc.barSpacing = 0.5
        bc.bars[0].fillColor   = C.HexColor(self.C_BLUE)
        bc.bars[0].strokeColor = None
        d.add(bc)
        els.append(d)
        els.append(rl['Spacer'](1, 0.4*cm))
        return els

    # ------------------------------------------------------------------ #
    #  Graphique : Commandes par statut (camembert)                        #
    # ------------------------------------------------------------------ #
    def _section_commandes_statut(self):
        rl  = self._rl
        C   = rl['colors']
        cm  = rl['cm']
        W   = 17.4 * cm
        els = []

        statuts_data = self.report_data['orders_by_status']
        if not statuts_data:
            return els

        LABELS = {
            'en_attente': 'En attente', 'confirmee': 'Confirmée',
            'en_preparation': 'En préparation', 'prete': 'Prête',
            'en_collecte': 'En collecte', 'livree': 'Livrée',
            'annulee': 'Annulée', 'litige': 'Litige',
        }
        COLORS_STATUT = {
            'livree': self.C_GREEN_LIGHT, 'confirmee': self.C_BLUE,
            'en_preparation': '#1abc9c', 'prete': '#f39c12',
            'en_collecte': self.C_ORANGE, 'en_attente': self.C_GRAY,
            'annulee': self.C_RED, 'litige': self.C_PURPLE,
        }

        raw = [(s, LABELS.get(s['statut'], s['statut']), int(s['count'] or 0)) for s in statuts_data]
        raw = [(s, lbl, cnt) for s, lbl, cnt in raw if cnt > 0]  # exclure les zéros (pie ne les accepte pas)
        if not raw:
            return els

        labels      = [lbl for _, lbl, _ in raw]
        values      = [cnt for _, _, cnt in raw]
        colors_list = [C.HexColor(COLORS_STATUT.get(s['statut'], self.C_GRAY)) for s, _, _ in raw]
        total       = sum(values) or 1

        # Tableau complet (y compris les statuts à 0)
        all_rows = [(LABELS.get(s['statut'], s['statut']), int(s['count'] or 0)) for s in statuts_data]

        els.append(self._section_title('Analyse des Commandes par Statut'))
        els.append(rl['Spacer'](1, 0.3*cm))

        pie_size = 4.5 * cm
        d = rl['Drawing'](pie_size + 0.5*cm, pie_size + 0.5*cm)
        pie = rl['Pie']()
        pie.x, pie.y = 0.25*cm, 0.25*cm
        pie.width = pie.height = pie_size
        pie.data   = values
        pie.labels = ['' for _ in labels]
        for i, col in enumerate(colors_list):
            pie.slices[i].fillColor   = col
            pie.slices[i].strokeColor = C.white
            pie.slices[i].strokeWidth = 0.5
        d.add(pie)

        # Tableau — tous les statuts (y compris ceux à 0)
        leg_data = [['Statut', 'Nb', '%']]
        for lbl, cnt in all_rows:
            leg_data.append([lbl, str(cnt), f"{cnt/total*100:.1f}%"])
        t = self._styled_table(leg_data, [3.2*cm, 1.2*cm, 1.4*cm],
                               header_color=self.C_DARK, number_cols=[1, 2])

        row = rl['Table']([[d, rl['Spacer'](0.5*cm, 1), t]],
                          colWidths=[pie_size + 0.75*cm, 0.5*cm, W - pie_size - 1.5*cm],
                          style=rl['TableStyle']([
                              ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                              ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                              ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
                              ('TOPPADDING',    (0, 0), (-1, -1), 0),
                              ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                          ]))
        els.append(row)
        els.append(rl['Spacer'](1, 0.5*cm))
        return els

    # ------------------------------------------------------------------ #
    #  Graphique : Paiements par méthode                                   #
    # ------------------------------------------------------------------ #
    def _section_paiements(self):
        rl  = self._rl
        C   = rl['colors']
        cm  = rl['cm']
        W   = 17.4 * cm
        els = []

        pay_data = self.report_data['payments_by_type']
        if not pay_data:
            return els

        PAY_LABELS = {
            'moncash': 'MonCash', 'natcash': 'NatCash',
            'virement': 'Virement', 'cash': 'Espèces',
            'voucher': 'Voucher', 'hors_ligne': 'Hors ligne',
        }
        # Filtrer uniquement les méthodes avec au moins 1 paiement
        pay_rows = [
            (PAY_LABELS.get(p['type_paiement'], p['type_paiement']),
             int(p['count'] or 0),
             self._safe_f(p.get('total')))
            for p in pay_data
        ]
        pay_rows = [(lbl, cnt, tot) for lbl, cnt, tot in pay_rows if cnt > 0]
        if not pay_rows:
            return els

        labels      = [r[0] for r in pay_rows]
        counts      = [r[1] for r in pay_rows]
        totals      = [r[2] for r in pay_rows]
        colors_list = [C.HexColor(self.CHART_COLORS[i % len(self.CHART_COLORS)]) for i in range(len(labels))]

        els.append(self._section_title('Analyse des Paiements par Méthode'))
        els.append(rl['Spacer'](1, 0.3*cm))

        # Camembert
        pie_size = 4 * cm
        d = rl['Drawing'](pie_size + 0.5*cm, pie_size + 0.5*cm)
        pie = rl['Pie']()
        pie.x, pie.y = 0.25*cm, 0.25*cm
        pie.width = pie.height = pie_size
        pie.data   = counts
        pie.labels = ['' for _ in labels]
        for i, col in enumerate(colors_list):
            pie.slices[i].fillColor   = col
            pie.slices[i].strokeColor = C.white
            pie.slices[i].strokeWidth = 0.5
        d.add(pie)

        leg_data = [['Méthode', 'Nb', 'Total HTG']]
        for lbl, cnt, tot in zip(labels, counts, totals):
            leg_data.append([lbl, str(cnt), f"{tot:,.0f}"])
        t = self._styled_table(leg_data, [3*cm, 1.2*cm, 2.5*cm],
                               header_color=self.C_BLUE, number_cols=[1, 2])

        row = rl['Table']([[d, rl['Spacer'](0.5*cm, 1), t]],
                          colWidths=[pie_size + 0.75*cm, 0.5*cm, W - pie_size - 1.5*cm],
                          style=rl['TableStyle']([
                              ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                              ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                              ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
                              ('TOPPADDING',    (0, 0), (-1, -1), 0),
                              ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                          ]))
        els.append(row)
        els.append(rl['Spacer'](1, 0.5*cm))
        return els

    # ------------------------------------------------------------------ #
    #  Graphique : Ventes par catégorie (barres horizontales)              #
    # ------------------------------------------------------------------ #
    def _section_categories(self):
        rl  = self._rl
        C   = rl['colors']
        cm  = rl['cm']
        W   = 17.4 * cm
        els = []

        cat_data = self.report_data['sales_by_category']
        if not cat_data:
            return els

        labels = [str(c.get('produit__categorie__nom') or 'Sans catégorie')[:20] for c in cat_data]
        values = self._safe([c.get('ca') for c in cat_data])
        max_v  = self._chart_max(values)

        els.append(self._section_title('Ventes par Catégorie'))
        els.append(rl['Spacer'](1, 0.3*cm))

        spacer_w = 0.3 * cm
        cat_col_w = [2.8*cm, 2.2*cm, 0.9*cm]           # = 5.9 cm
        cat_tbl_w = sum(cat_col_w)
        chart_w   = W - cat_tbl_w - spacer_w            # = 11.2 cm
        chart_h   = max(3*cm, len(labels) * 0.7*cm + 1*cm)
        d = rl['Drawing'](chart_w, chart_h)

        bc = rl['HorizontalBarChart']()
        bc.x, bc.y = 3.5*cm, 0.5*cm
        bc.width   = chart_w - 4.5*cm
        bc.height  = chart_h - 1*cm
        bc.data    = [values]
        bc.categoryAxis.categoryNames = labels
        bc.categoryAxis.labels.fontSize = 7.5
        bc.categoryAxis.labels.dx = -4
        bc.valueAxis.valueMin  = 0
        bc.valueAxis.valueMax  = max_v * 1.1
        bc.valueAxis.valueStep = self._step(max_v, 4)
        bc.valueAxis.labels.fontSize = 7
        bc.bars[0].fillColor   = C.HexColor(self.C_ORANGE)
        bc.bars[0].strokeColor = None
        d.add(bc)

        # Tableau de données (colWidths = cat_col_w, somme <= cat_tbl_w)
        cat_tbl = [['Catégorie', 'CA (HTG)', 'Ventes']]
        for (lbl, val), c in zip(zip(labels, values), cat_data):
            cat_tbl.append([lbl, f"{val:,.0f}", str(c.get('nb', 0))])
        t = self._styled_table(cat_tbl, cat_col_w,
                               header_color=self.C_ORANGE, number_cols=[1, 2])

        row = rl['Table']([[d, rl['Spacer'](spacer_w, 1), t]],
                          colWidths=[chart_w, spacer_w, cat_tbl_w],
                          style=rl['TableStyle']([
                              ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                              ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                              ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
                              ('TOPPADDING',    (0, 0), (-1, -1), 0),
                              ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                          ]))
        els.append(row)
        els.append(rl['Spacer'](1, 0.5*cm))
        return els

    # ------------------------------------------------------------------ #
    #  Top Produits                                                        #
    # ------------------------------------------------------------------ #
    def _section_top_produits(self):
        rl  = self._rl
        cm  = rl['cm']
        W   = 17.4 * cm
        els = []
        products = self.report_data['top_products']

        els.append(self._section_title('Top 10 Produits'))
        els.append(rl['Spacer'](1, 0.3*cm))

        if not products:
            els.append(rl['Paragraph']('Aucune donnée.', self._styles['small']))
            return els

        data = [['#', 'Produit', 'Qté vendue', 'CA (HTG)']]
        for i, p in enumerate(products, 1):
            data.append([
                str(i),
                str(p['produit__nom'] or '')[:35],
                str(p['total_vendu'] or 0),
                f"{self._safe_f(p['ca']):,.0f}",
            ])
        t = self._styled_table(data, [0.6*cm, 9.4*cm, 2.8*cm, 3.6*cm],
                               header_color=self.C_GREEN, number_cols=[2, 3])
        els.append(t)
        els.append(rl['Spacer'](1, 0.5*cm))
        return els

    # ------------------------------------------------------------------ #
    #  Top Producteurs                                                     #
    # ------------------------------------------------------------------ #
    def _section_top_producteurs(self):
        rl  = self._rl
        cm  = rl['cm']
        W   = 17.4 * cm
        els = []
        producers = self.report_data['top_producers']

        els.append(self._section_title('Top 10 Producteurs'))
        els.append(rl['Spacer'](1, 0.3*cm))

        if not producers:
            els.append(rl['Paragraph']('Aucune donnée.', self._styles['small']))
            return els

        data = [['#', 'Producteur', 'Commandes', 'CA (HTG)']]
        for i, p in enumerate(producers, 1):
            data.append([
                str(i),
                str(p['name'] or '')[:35],
                str(p['nb_cmd'] or 0),
                f"{self._safe_f(p['ca']):,.0f}",
            ])
        t = self._styled_table(data, [0.6*cm, 9.4*cm, 2.8*cm, 3.6*cm],
                               header_color=self.C_GREEN_LIGHT, number_cols=[2, 3])
        els.append(t)
        els.append(rl['Spacer'](1, 0.5*cm))
        return els

    # ------------------------------------------------------------------ #
    #  Top Acheteurs                                                       #
    # ------------------------------------------------------------------ #
    def _section_top_acheteurs(self):
        rl  = self._rl
        cm  = rl['cm']
        W   = 17.4 * cm
        els = []
        buyers = self.report_data['top_buyers']

        els.append(self._section_title('Top 10 Acheteurs'))
        els.append(rl['Spacer'](1, 0.3*cm))

        if not buyers:
            els.append(rl['Paragraph']('Aucune donnée.', self._styles['small']))
            return els

        data = [['#', 'Acheteur', 'Commandes', 'Dépense (HTG)']]
        for i, b in enumerate(buyers, 1):
            data.append([
                str(i),
                str(b['name'] or '')[:35],
                str(b['nb_cmd'] or 0),
                f"{self._safe_f(b['depense']):,.0f}",
            ])
        t = self._styled_table(data, [0.6*cm, 9.4*cm, 2.8*cm, 3.6*cm],
                               header_color=self.C_BLUE, number_cols=[2, 3])
        els.append(t)
        els.append(rl['Spacer'](1, 0.3*cm))
        return els


class CSVReportGenerator:
    """Generate CSV reports"""

    def __init__(self, report_data):
        self.report_data = report_data

    def generate(self):
        """Generate CSV report"""
        output = StringIO()
        writer = csv.writer(output)

        kpis = self.report_data['kpis']
        
        # Header
        writer.writerow(['RAPPORT MAKÈT PEYIZAN'])
        writer.writerow([f"Période: {kpis['periode_debut']} au {kpis['periode_fin']}"])
        writer.writerow([])

        # KPIs
        writer.writerow(['INDICATEURS CLÉS'])
        writer.writerow(['Métrique', 'Valeur'])
        writer.writerow(['Total Commandes', kpis['total_commandes']])
        writer.writerow(['Chiffre d\'affaires (HTG)', f"{kpis['ca_total']:,.0f}"])
        writer.writerow(['Producteurs Actifs', kpis['total_producteurs']])
        writer.writerow(['Alertes Stock', kpis['alertes_stock']])
        writer.writerow(['Paiements en Attente', kpis['paiements_en_attente']])
        writer.writerow([])

        # Daily Sales
        writer.writerow(['VENTES JOURNALIÈRES'])
        writer.writerow(['Date', 'CA (HTG)'])
        for day in self.report_data['daily_sales']:
            writer.writerow([day['date'], f"{day['ca']:,.0f}"])
        writer.writerow([])

        # Top Products
        writer.writerow(['TOP 10 PRODUITS'])
        writer.writerow(['Produit', 'Quantité', 'CA (HTG)'])
        for p in self.report_data['top_products']:
            writer.writerow([
                p['produit__nom'],
                p['total_vendu'],
                f"{p['ca']:,.0f}"
            ])
        writer.writerow([])

        # Orders by Status
        writer.writerow(['COMMANDES PAR STATUT'])
        writer.writerow(['Statut', 'Nombre'])
        for s in self.report_data['orders_by_status']:
            writer.writerow([s['statut'], s['count']])

        output.seek(0)
        return output


# ======================================================================= #
#  Rapport PRODUCTEUR                                                       #
# ======================================================================= #

class ProducteurReportDataGenerator:
    """Génère les données de rapport filtrées pour un producteur spécifique."""

    def __init__(self, producteur, start_date, end_date):
        self.producteur  = producteur
        self.start_date  = start_date
        self.end_date    = end_date

    def _qs_base(self):
        from apps.orders.models import Commande
        return Commande.objects.filter(
            producteur=self.producteur,
            created_at__date__gte=self.start_date,
            created_at__date__lte=self.end_date,
        )

    def get_kpis(self):
        from apps.catalog.models import Produit
        from apps.stock.models import AlerteStock

        qs = self._qs_base()
        ca = qs.filter(statut_paiement='paye').aggregate(total=Sum('total'))['total'] or 0

        return {
            'nom_producteur':      self.producteur.user.get_full_name() or self.producteur.user.username,
            'code_producteur':     self.producteur.code_producteur,
            'periode_debut':       self.start_date.strftime('%d/%m/%Y'),
            'periode_fin':         self.end_date.strftime('%d/%m/%Y'),
            'total_commandes':     qs.count(),
            'ca_total':            float(ca),
            'commandes_en_attente': qs.filter(statut='en_attente').count(),
            'commandes_en_cours':   qs.filter(statut__in=['confirmee', 'en_preparation', 'prete', 'en_collecte']).count(),
            'commandes_livrees':    qs.filter(statut='livree').count(),
            'commandes_annulees':   qs.filter(statut='annulee').count(),
            'produits_actifs':      Produit.objects.filter(producteur=self.producteur, is_active=True).count(),
            'alertes_stock':        AlerteStock.objects.filter(
                                        produit__producteur=self.producteur,
                                        statut__in=['nouvelle', 'vue']
                                    ).count(),
        }

    def get_revenue_by_month(self):
        from apps.orders.models import Commande
        data = []
        for i in range(11, -1, -1):
            mois = (self.start_date.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            ca = Commande.objects.filter(
                producteur=self.producteur,
                created_at__year=mois.year,
                created_at__month=mois.month,
                statut_paiement='paye',
            ).aggregate(total=Sum('total'))['total'] or 0
            data.append({'mois': mois.strftime('%b %Y'), 'ca': float(ca)})
        return data

    def get_orders_by_status(self):
        return [
            {'statut': s['statut'], 'count': s['count']}
            for s in self._qs_base().values('statut').annotate(count=Count('id')).order_by('-count')
        ]

    def get_top_products(self, limit=10):
        from apps.orders.models import CommandeDetail
        return list(CommandeDetail.objects.filter(
            commande__producteur=self.producteur,
            commande__created_at__date__gte=self.start_date,
            commande__created_at__date__lte=self.end_date,
        ).values('produit__nom').annotate(
            total_vendu=Sum('quantite'),
            ca=Sum('sous_total'),
        ).order_by('-ca')[:limit])

    def get_stock_actuel(self):
        from apps.catalog.models import Produit
        return list(Produit.objects.filter(
            producteur=self.producteur, is_active=True
        ).values('nom', 'stock_disponible', 'seuil_alerte', 'unite_vente').order_by('stock_disponible')[:15])

    def get_recent_orders(self, limit=15):
        return list(self._qs_base().select_related('acheteur__user').order_by('-created_at').values(
            'numero_commande', 'statut', 'total', 'created_at',
            'acheteur__user__first_name', 'acheteur__user__last_name',
        )[:limit])


class ProducteurPDFReportGenerator(PDFReportGenerator):
    """Rapport PDF spécifique à un producteur. Hérite des helpers de PDFReportGenerator."""

    def __init__(self, report_data):
        self.report_data = report_data

    def generate(self):
        self._import_rl()
        buffer = BytesIO()
        doc    = self._make_doc(buffer)

        elements  = self._cover_producteur()
        elements.append(self._rl['PageBreak']())
        elements += self._section_kpis_producteur()
        elements += self._section_ca_mensuel()
        elements += self._section_statuts()
        elements.append(self._rl['PageBreak']())
        elements += self._section_top_produits_prod()
        elements += self._section_stock()
        elements += self._section_recent_orders()

        doc.build(elements,
                  onFirstPage=self._draw_page_frame_prod,
                  onLaterPages=self._draw_page_frame_prod)
        buffer.seek(0)
        return buffer

    def _draw_page_frame_prod(self, canvas, doc):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from datetime import date
        W, H = A4
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(self.C_GREEN))
        canvas.rect(0, H - 1.2*cm, W, 1.2*cm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawString(1.8*cm, H - 0.85*cm, 'MAKÈT PEYIZAN — Espace Producteur')
        canvas.setFont('Helvetica', 8)
        kpis = self.report_data['kpis']
        canvas.drawRightString(W - 1.8*cm, H - 0.85*cm,
                               f"{kpis['nom_producteur']} · {kpis['periode_debut']} – {kpis['periode_fin']}")
        canvas.setStrokeColor(colors.HexColor(self.C_LIGHT_GRAY))
        canvas.setLineWidth(0.5)
        canvas.line(1.8*cm, 1.5*cm, W - 1.8*cm, 1.5*cm)
        canvas.setFillColor(colors.HexColor(self.C_GRAY))
        canvas.setFont('Helvetica', 7.5)
        canvas.drawString(1.8*cm, 0.8*cm, f"Généré le {date.today().strftime('%d/%m/%Y')}")
        canvas.drawRightString(W - 1.8*cm, 0.8*cm, f"Page {doc.page}")
        canvas.restoreState()

    def _cover_producteur(self):
        rl  = self._rl
        C   = rl['colors']
        cm  = rl['cm']
        W   = 17.4 * cm
        kpis = self.report_data['kpis']
        els  = []

        els.append(rl['Spacer'](1, 3*cm))

        d = rl['Drawing'](W, 80)
        d.add(rl['Rect'](W/2 - 35, 10, 70, 60, fillColor=C.HexColor(self.C_GREEN),
                          strokeColor=None, rx=12))
        d.add(rl['String'](W/2 - 12, 32, 'MP', fontName='Helvetica-Bold', fontSize=28,
                            fillColor=C.white))
        els.append(d)
        els.append(rl['Spacer'](1, 0.4*cm))

        els.append(rl['Paragraph']('MAKÈT PEYIZAN', self._styles['cover_title']))
        els.append(rl['Paragraph']('Rapport Producteur', self._styles['cover_sub']))
        els.append(rl['Spacer'](1, 0.3*cm))

        d2 = rl['Drawing'](W, 8)
        d2.add(rl['Rect'](W/2 - 60, 3, 120, 3, fillColor=C.HexColor(self.C_GREEN_LIGHT),
                           strokeColor=None))
        els.append(d2)
        els.append(rl['Spacer'](1, 0.4*cm))

        els.append(rl['Paragraph'](
            f"<b>{kpis['nom_producteur']}</b> · {kpis['code_producteur']}",
            self._styles['cover_sub']
        ))
        els.append(rl['Paragraph'](
            f"Période : <b>{kpis['periode_debut']}</b> — <b>{kpis['periode_fin']}</b>",
            self._styles['cover_sub']
        ))
        els.append(rl['Spacer'](1, 2.5*cm))

        from datetime import date
        summary = [
            ['', ''],
            [rl['Paragraph']('<b>Commandes sur la période</b>', self._styles['normal']),
             rl['Paragraph'](f"<b>{kpis['total_commandes']}</b>",    self._styles['normal'])],
            [rl['Paragraph']('<b>Chiffre d\'affaires (HTG)</b>',     self._styles['normal']),
             rl['Paragraph'](f"<b>{kpis['ca_total']:,.0f}</b>",       self._styles['normal'])],
            [rl['Paragraph']('<b>Commandes livrées</b>',             self._styles['normal']),
             rl['Paragraph'](f"<b>{kpis['commandes_livrees']}</b>",   self._styles['normal'])],
            [rl['Paragraph']('<b>Produits actifs</b>',               self._styles['normal']),
             rl['Paragraph'](f"<b>{kpis['produits_actifs']}</b>",     self._styles['normal'])],
            [rl['Paragraph']('<b>Alertes stock actives</b>',         self._styles['normal']),
             rl['Paragraph'](f"<b>{kpis['alertes_stock']}</b>",       self._styles['normal'])],
            ['', ''],
        ]
        t = rl['Table'](summary, colWidths=[8*cm, 4*cm], style=rl['TableStyle']([
            ('ALIGN',         (1, 0), (1, -1), 'RIGHT'),
            ('BACKGROUND',    (0, 0), (-1, 0), C.HexColor(self.C_GREEN)),
            ('BACKGROUND',    (0, -1), (-1, -1), C.HexColor(self.C_GREEN)),
            ('LINEBELOW',     (0, 1), (-1, -2), 0.5, C.HexColor(self.C_LIGHT_GRAY)),
            ('TOPPADDING',    (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING',   (0, 0), (-1, -1), 14),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ]))
        wrapper = rl['Table']([[t]], colWidths=[W],
                               style=rl['TableStyle']([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        els.append(wrapper)
        els.append(rl['Spacer'](1, 1.5*cm))
        els.append(rl['Paragraph'](
            f"Document généré automatiquement le {date.today().strftime('%d/%m/%Y')}",
            self._styles['small']
        ))
        return els

    def _section_kpis_producteur(self):
        rl   = self._rl
        cm   = rl['cm']
        W    = 17.4 * cm
        kpis = self.report_data['kpis']
        els  = []

        els.append(self._section_title('Indicateurs Clés'))
        els.append(rl['Spacer'](1, 0.3*cm))

        cw   = (W - 3*0.3*cm) / 4
        row1 = [
            self._kpi_card('Commandes totales',  str(kpis['total_commandes']),       self.C_ORANGE, cw),
            self._kpi_card('CA total (HTG)',      f"{kpis['ca_total']:,.0f}",         self.C_GREEN,  cw),
            self._kpi_card('Livrées',             str(kpis['commandes_livrees']),     self.C_GREEN,  cw),
            self._kpi_card('En attente',          str(kpis['commandes_en_attente']), self.C_ORANGE, cw),
        ]
        row2 = [
            self._kpi_card('En cours',            str(kpis['commandes_en_cours']),   self.C_BLUE,   cw),
            self._kpi_card('Annulées',            str(kpis['commandes_annulees']),   self.C_RED,    cw),
            self._kpi_card('Produits actifs',     str(kpis['produits_actifs']),      self.C_GREEN,  cw),
            self._kpi_card('Alertes stock',       str(kpis['alertes_stock']),        self.C_RED,    cw),
        ]
        grid = rl['Table'](
            [row1, [rl['Spacer'](1, 0.25*cm)] * 4, row2],
            colWidths=[cw] * 4,
            style=rl['TableStyle']([
                ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING',    (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('LEFTPADDING',   (0, 0), (-1, -1), 3),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
            ])
        )
        els.append(grid)
        els.append(rl['Spacer'](1, 0.5*cm))
        return els

    def _section_ca_mensuel(self):
        rl   = self._rl
        C    = rl['colors']
        cm   = rl['cm']
        W    = 17.4 * cm
        els  = []
        monthly = self.report_data.get('revenue_by_month', [])
        if not monthly:
            return els

        els.append(self._section_title('Chiffre d\'Affaires Mensuel'))
        els.append(rl['Spacer'](1, 0.3*cm))

        labels   = [m['mois'] for m in monthly]
        values   = self._safe([m['ca'] for m in monthly])
        max_v    = self._chart_max(values)
        recap_w  = 5.5 * cm
        spacer_w = 0.3 * cm
        chart_w  = W - recap_w - spacer_w
        chart_h  = 5.0 * cm

        d = rl['Drawing'](chart_w, chart_h + 1.2*cm)
        bc = rl['VerticalBarChart']()
        bc.x, bc.y = 1.2*cm, 1.2*cm
        bc.width  = chart_w - 2*cm
        bc.height = chart_h - 0.8*cm
        bc.data   = [values]
        bc.categoryAxis.categoryNames  = labels
        bc.categoryAxis.labels.angle   = 45
        bc.categoryAxis.labels.dy      = -10
        bc.categoryAxis.labels.fontSize = 6.5
        bc.categoryAxis.labels.textAnchor = 'end'
        bc.valueAxis.valueMin  = 0
        bc.valueAxis.valueMax  = max_v * 1.15
        bc.valueAxis.valueStep = self._step(max_v, 5)
        bc.valueAxis.labels.fontSize = 7
        bc.barSpacing = 1
        bc.bars[0].fillColor   = C.HexColor(self.C_GREEN_LIGHT)
        bc.bars[0].strokeColor = None
        d.add(bc)

        sorted_m = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)[:3]
        recap = [['Mois', 'CA (HTG)']]
        for lbl, val in sorted_m:
            recap.append([lbl, f"{val:,.0f}"])
        t = self._styled_table(recap, [2.7*cm, 2.5*cm],
                               header_color=self.C_GREEN_LIGHT, number_cols=[1])

        row = rl['Table']([[d, rl['Spacer'](spacer_w, 1), t]],
                          colWidths=[chart_w, spacer_w, recap_w],
                          style=rl['TableStyle']([
                              ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
                              ('LEFTPADDING',   (0,0), (-1,-1), 0),
                              ('RIGHTPADDING',  (0,0), (-1,-1), 0),
                              ('TOPPADDING',    (0,0), (-1,-1), 0),
                              ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                          ]))
        els.append(row)
        els.append(rl['Spacer'](1, 0.4*cm))
        return els

    def _section_statuts(self):
        rl  = self._rl
        C   = rl['colors']
        cm  = rl['cm']
        W   = 17.4 * cm
        els = []
        statuts_data = self.report_data.get('orders_by_status', [])
        if not statuts_data:
            return els

        LABELS = {
            'en_attente': 'En attente', 'confirmee': 'Confirmée',
            'en_preparation': 'En préparation', 'prete': 'Prête',
            'en_collecte': 'En collecte', 'livree': 'Livrée',
            'annulee': 'Annulée', 'litige': 'Litige',
        }
        COLORS_S = {
            'livree': self.C_GREEN_LIGHT, 'confirmee': self.C_BLUE,
            'en_preparation': '#1abc9c', 'prete': '#f39c12',
            'en_collecte': self.C_ORANGE, 'en_attente': self.C_GRAY,
            'annulee': self.C_RED, 'litige': self.C_PURPLE,
        }

        all_rows = [(LABELS.get(s['statut'], s['statut']), int(s['count'] or 0))
                    for s in statuts_data]
        pie_rows = [(lbl, cnt) for lbl, cnt in all_rows if cnt > 0]
        if not pie_rows:
            return els

        total = sum(c for _, c in pie_rows) or 1

        els.append(self._section_title('Commandes par Statut'))
        els.append(rl['Spacer'](1, 0.3*cm))

        pie_size = 4.5 * cm
        d = rl['Drawing'](pie_size + 0.5*cm, pie_size + 0.5*cm)
        pie = rl['Pie']()
        pie.x, pie.y = 0.25*cm, 0.25*cm
        pie.width = pie.height = pie_size
        pie.data   = [c for _, c in pie_rows]
        pie.labels = ['' for _ in pie_rows]
        for i, (lbl, _) in enumerate(pie_rows):
            s_key = next((k for k, v in LABELS.items() if v == lbl), '')
            pie.slices[i].fillColor   = C.HexColor(COLORS_S.get(s_key, self.C_GRAY))
            pie.slices[i].strokeColor = C.white
            pie.slices[i].strokeWidth = 0.5
        d.add(pie)

        leg_data = [['Statut', 'Nb', '%']]
        for lbl, cnt in all_rows:
            leg_data.append([lbl, str(cnt), f"{cnt/total*100:.1f}%"])
        t = self._styled_table(leg_data, [3.2*cm, 1.2*cm, 1.4*cm],
                               header_color=self.C_DARK, number_cols=[1, 2])

        row = rl['Table']([[d, rl['Spacer'](0.5*cm, 1), t]],
                          colWidths=[pie_size + 0.75*cm, 0.5*cm, W - pie_size - 1.5*cm],
                          style=rl['TableStyle']([
                              ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
                              ('LEFTPADDING',   (0,0), (-1,-1), 0),
                              ('RIGHTPADDING',  (0,0), (-1,-1), 0),
                              ('TOPPADDING',    (0,0), (-1,-1), 0),
                              ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                          ]))
        els.append(row)
        els.append(rl['Spacer'](1, 0.5*cm))
        return els

    def _section_top_produits_prod(self):
        rl  = self._rl
        cm  = rl['cm']
        W   = 17.4 * cm
        els = []
        products = self.report_data.get('top_products', [])

        els.append(self._section_title('Top Produits Vendus'))
        els.append(rl['Spacer'](1, 0.3*cm))

        if not products:
            els.append(rl['Paragraph']('Aucune vente sur la période.', self._styles['small']))
            return els

        data = [['#', 'Produit', 'Qté vendue', 'CA (HTG)']]
        for i, p in enumerate(products, 1):
            data.append([
                str(i),
                str(p.get('produit__nom') or '')[:35],
                str(p.get('total_vendu') or 0),
                f"{self._safe_f(p.get('ca')):,.0f}",
            ])
        els.append(self._styled_table(data, [0.6*cm, 9.4*cm, 2.8*cm, 3.6*cm],
                                      header_color=self.C_GREEN, number_cols=[2, 3]))
        els.append(rl['Spacer'](1, 0.5*cm))
        return els

    def _section_stock(self):
        rl   = self._rl
        C    = rl['colors']
        cm   = rl['cm']
        W    = 17.4 * cm
        els  = []
        stock_data = self.report_data.get('stock_actuel', [])

        els.append(self._section_title('État du Stock Actuel', color=self.C_ORANGE))
        els.append(rl['Spacer'](1, 0.3*cm))

        if not stock_data:
            els.append(rl['Paragraph']('Aucun produit actif.', self._styles['small']))
            return els

        data = [['Produit', 'Stock dispo', 'Seuil alerte', 'Unité', 'État']]
        for p in stock_data:
            dispo  = p.get('stock_disponible') or 0
            seuil  = p.get('seuil_alerte') or 0
            etat   = 'OK' if dispo > seuil else ('Critique' if dispo == 0 else 'Bas')
            data.append([
                str(p.get('nom') or '')[:30],
                str(dispo),
                str(seuil),
                str(p.get('unite_vente') or ''),
                etat,
            ])
        els.append(self._styled_table(data, [5.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.4*cm],
                                      header_color=self.C_ORANGE, number_cols=[1, 2]))
        els.append(rl['Spacer'](1, 0.5*cm))
        return els

    def _section_recent_orders(self):
        rl   = self._rl
        cm   = rl['cm']
        W    = 17.4 * cm
        els  = []
        orders = self.report_data.get('recent_orders', [])

        els.append(self._section_title('Commandes Récentes'))
        els.append(rl['Spacer'](1, 0.3*cm))

        if not orders:
            els.append(rl['Paragraph']('Aucune commande sur la période.', self._styles['small']))
            return els

        STATUT_LABELS = {
            'en_attente': 'En attente', 'confirmee': 'Confirmée',
            'en_preparation': 'En prép.', 'prete': 'Prête',
            'en_collecte': 'En collecte', 'livree': 'Livrée',
            'annulee': 'Annulée', 'litige': 'Litige',
        }

        data = [['N°', 'Acheteur', 'Total (HTG)', 'Statut', 'Date']]
        for o in orders:
            nom = f"{o.get('acheteur__user__first_name','') or ''} {o.get('acheteur__user__last_name','') or ''}".strip() or '—'
            data.append([
                str(o.get('numero_commande') or '')[:18],
                nom[:22],
                f"{self._safe_f(o.get('total')):,.0f}",
                STATUT_LABELS.get(o.get('statut'), str(o.get('statut') or '')),
                str(o.get('created_at'))[:10] if o.get('created_at') else '—',
            ])
        els.append(self._styled_table(
            data, [3.8*cm, 4.5*cm, 3.0*cm, 3.0*cm, 2.1*cm],
            header_color=self.C_BLUE, number_cols=[2]
        ))
        els.append(rl['Spacer'](1, 0.3*cm))
        return els
