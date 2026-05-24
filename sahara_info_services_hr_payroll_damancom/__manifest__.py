# -*- coding: utf-8 -*-
{
    'name': 'Sahara Info Services - Télédéclaration CNSS Damancom',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': "Génération du fichier BDS pour Damancom CNSS Maroc",
    'description': """
Module de Télédéclaration CNSS Damancom pour le Maroc
======================================================

Ce module permet de générer le fichier BDS au format officiel CNSS
(version 2 - Février 2006) pour la télédéclaration mensuelle des salaires
sur le portail Damancom (e-BDS).

Fonctionnalités:
----------------
* Configuration du numéro d'affiliation CNSS de l'entreprise (avec validation clé)
* Configuration du numéro d'immatriculation CNSS des employés (avec validation clé)
* Gestion des situations spéciales (SO, DE, IT, IL, AT, CS, MS, MP)
* Génération du fichier BDS principal (déclaration normale)
* Génération du fichier BDS complémentaire (entrants oubliés)
* Format conforme à 100% au cahier des charges CNSS Version 2
* Longueur fixe 260 caractères par enregistrement
* Calculs SBP/SBNP plafonné/déplafonné automatiques
* Contrôles horizontaux (S_Ctr) et verticaux
* Nommage automatique : DS_NNNNNNN_MMAAAA.txt

Le fichier généré peut être :
* Téléchargé et déposé manuellement sur damancom.ma (mode EDI)
* Utilisé pour vérification avant dépôt
    """,
    'author': 'Sahara Info Services',
    'website': 'https://www.sahara-info-services.ma',
    'depends': ['hr', 'hr_payroll', 'sahara_info_services_hr_payroll'],
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
