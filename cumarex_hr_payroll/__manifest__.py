# -*- coding: utf-8 -*-
{
    'name': "Maroc - Paie Cumarex (Règles Personnalisées)",
    'summary': "Localisation Maroc - Règles salariales complètes (CNSS, AMO, IR, indemnités)",
    'description': """
Localisation marocaine pour la paie - Odoo 19
==============================================

Ce module ajoute toutes les règles salariales conformes à la législation marocaine 2025-2026 :

**Cotisations sociales (CNSS) :**
    * Prestations sociales court & long terme (plafonnées à 6 000 DH)
    * AMO de base (déplafonnée)
    * AMO solidarité (1,85% patronale)
    * Allocations familiales (6,40% patronale, déplafonnée)
    * Taxe de Formation Professionnelle (TFP - 1,60% patronale)
    * Indemnité Pour Perte d'Emploi (IPE - 0,57%)

**Fiscalité :**
    * Frais professionnels (35% / 25%, plafond 35 000 DH)
    * Barème IR mensuel progressif 2026 (0% à 37%, 6 tranches)
    * Charges de famille (50 DH/personne/mois - LF 2026)
    * Réduction pour personnes à charge

**Indemnités & Avantages :**
    * Prime d'ancienneté (légale : 5%, 10%, 15%, 20%, 25%)
    * Indemnité de transport (exonérée jusqu'à 500 DH)
    * Indemnité de panier / repas
    * Indemnité de représentation
    * Avantages en nature (logement, voiture)
    * Heures supplémentaires (25%, 50%, 100%)
    * Prime de rendement / bilan

**Retenues :**
    * Avances sur salaire
    * Acomptes
    * Prêts au personnel
    * Saisies-arrêts

**Conformité :**
    * Loi de Finances 2025 et 2026
    * Code Général des Impôts (Articles 56-60, 73)
    * Code du Travail Marocain
""",
    'author': "Localisation Maroc",
    'website': "https://www.odoo.com",
    'category': 'Human Resources/Payroll',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': [
        'hr_payroll',
        'hr_contract',
        'l10n_ma',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_salary_rule_cnss_data.xml',
        'data/hr_salary_rule_amo_data.xml',
        'data/hr_salary_rule_ir_data.xml',
        'data/hr_salary_rule_indemnites_data.xml',
        'data/hr_salary_rule_retenues_data.xml',
        'data/hr_salary_rule_net_data.xml',
        'data/hr_payroll_employer_cost_data.xml',
        'views/hr_contract_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
