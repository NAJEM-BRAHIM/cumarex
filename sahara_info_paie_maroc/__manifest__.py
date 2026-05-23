# -*- coding: utf-8 -*-
{
    'name': "Sahara Info - Paie Maroc (Règles Personnalisées)",
    'summary': "Localisation Maroc - Règles salariales personnalisées Odoo 19",
    'description': """
Module personnalisé de paie Maroc pour Odoo 19
===============================================

Ce module ajoute des règles salariales adaptées au Maroc 2025-2026 :
- Cotisations CNSS, AMO, allocations familiales, TFP
- Barème IR mensuel 2026
- Indemnités (transport, panier, représentation)
- Avantages en nature
- Prime d'ancienneté légale
- Heures supplémentaires
- Retenues diverses
""",
    'author': 'Sahara Info',
    'category': 'Human Resources/Payroll',
    'version': '19.0.1.0.2',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'hr_payroll',
    ],
    'data': [
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_salary_rule_indemnites_data.xml',
        'data/hr_salary_rule_cnss_data.xml',
        'data/hr_salary_rule_amo_data.xml',
        'data/hr_salary_rule_ir_data.xml',
        'data/hr_salary_rule_retenues_data.xml',
        'data/hr_salary_rule_net_data.xml',
        'data/hr_payroll_employer_cost_data.xml',
        'data/hr_salary_rule_account_data.xml',
        # 'views/hr_version_views.xml',  # TODO: trouver l'XML ID correct de la vue hr.version dans cette instance
        # 'report/report_payslip_templates.xml',  # TODO: vérifier que hr_payroll.report_payslip existe dans cette instance
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
