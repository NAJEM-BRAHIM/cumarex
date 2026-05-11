# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrVersion(models.Model):
    """
    En Odoo 19, hr.contract a été remplacé par hr.version.
    Tous les champs de paie spécifiques au Maroc sont ajoutés ici.
    """
    _inherit = 'hr.version'

    # ============================================================
    # Champs spécifiques à la paie marocaine
    # ============================================================

    l10n_ma_anciennete_date = fields.Date(
        string="Date d'ancienneté",
        help="Date prise en compte pour le calcul de la prime d'ancienneté. "
             "Si vide, utilise contract_date_start."
    )

    l10n_ma_personnes_charge = fields.Integer(
        string="Personnes à charge",
        default=0,
        help="Nombre de personnes à charge (max 6). 50 DH/personne/mois en 2026."
    )

    l10n_ma_indemnite_transport = fields.Float(
        string="Indemnité de transport (DH/mois)",
        default=0.0,
        help="Indemnité de transport mensuelle. Exonérée d'IR jusqu'à 500 DH."
    )

    l10n_ma_indemnite_panier = fields.Float(
        string="Indemnité de panier (DH/mois)",
        default=0.0,
        help="Indemnité de panier / repas. Exonérée jusqu'à 30 DH/jour, max 20% du brut."
    )

    l10n_ma_indemnite_representation = fields.Float(
        string="Indemnité de représentation (DH/mois)",
        default=0.0,
        help="Indemnité de représentation pour cadres dirigeants."
    )

    l10n_ma_avantage_logement = fields.Float(
        string="Avantage logement (DH/mois)",
        default=0.0,
        help="Valeur de l'avantage en nature - logement de fonction."
    )

    l10n_ma_avantage_voiture = fields.Float(
        string="Avantage voiture (DH/mois)",
        default=0.0,
        help="Valeur de l'avantage en nature - voiture de fonction."
    )

    l10n_ma_taux_frais_pro = fields.Selection(
        [('25', '25%'),
         ('35', '35%')],
        string="Taux frais professionnels",
        default='35',
        help="35% pour salaires ≤ 78 000 DH/an, 25% au-delà (plafonné à 35 000 DH/an)."
    )

    l10n_ma_affilie_cimr = fields.Boolean(
        string="Affilié CIMR",
        default=False,
    )

    l10n_ma_taux_cimr = fields.Float(
        string="Taux CIMR salarial (%)",
        default=0.0,
    )

    l10n_ma_taux_cimr_patronal = fields.Float(
        string="Taux CIMR patronal (%)",
        default=0.0,
    )

    l10n_ma_mutuelle = fields.Float(
        string="Mutuelle salariale (DH/mois)",
        default=0.0,
    )

    l10n_ma_mutuelle_patronal = fields.Float(
        string="Mutuelle patronale (DH/mois)",
        default=0.0,
    )

    # ============================================================
    # Helper utilisé dans les règles salariales
    # ============================================================

    def get_anciennete_taux(self, payslip_date=None):
        """
        Calcule le taux de prime d'ancienneté selon le Code du Travail Marocain :
            - 5%  après 2 ans
            - 10% après 5 ans
            - 15% après 12 ans
            - 20% après 20 ans
            - 25% après 25 ans
        """
        self.ensure_one()
        ref_date = self.l10n_ma_anciennete_date or self.contract_date_start
        if not ref_date:
            return 0.0
        compare_date = payslip_date or fields.Date.today()
        years = (compare_date - ref_date).days / 365.25
        if years >= 25:
            return 0.25
        elif years >= 20:
            return 0.20
        elif years >= 12:
            return 0.15
        elif years >= 5:
            return 0.10
        elif years >= 2:
            return 0.05
        return 0.0
