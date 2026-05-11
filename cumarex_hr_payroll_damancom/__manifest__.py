# -*- coding: utf-8 -*-
{
    'name': 'Cumarex - Teledeclaration CNSS Damancom',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': "Generation du fichier BDS pour Damancom CNSS Maroc",
    'description': """
Module de Teledeclaration CNSS Damancom pour le Maroc
======================================================

Ce module permet de generer le fichier BDS au format officiel CNSS
(version 2 - Fevrier 2006) pour la teledeclaration mensuelle des salaires
sur le portail Damancom (e-BDS).
    """,
    'author': 'Cumarex',
    'website': 'https://www.cumarex.ma',
    'depends': ['hr', 'hr_payroll', 'cumarex_hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'data/damancom_situation_data.xml',
        'views/res_company_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_payslip_views.xml',
        'wizards/damancom_generate_wizard_views.xml',
        'wizards/damancom_import_preetabli_wizard_views.xml',
        'views/damancom_declaration_views.xml',
        'views/damancom_menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
