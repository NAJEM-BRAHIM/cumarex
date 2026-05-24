# -*- coding: utf-8 -*-
# Script de migration Cumarex -> Sahara Info Services
# Exécuter dans Odoo Shell ou via Menu Technique > Exécuter du code Python
# Usage: odoo-bin shell -d <nom_base> < migration_script.py
# 
# PRÉREQUIS:
# 1. Copier les nouveaux répertoires (sahara_info_services_*) dans les addons
# 2. Lancer ce script
# 3. Redémarrer Odoo

import logging
_logger = logging.getLogger(__name__)

OLD_NEW_MODULES = {
    'cumarex_hr_payroll': 'sahara_info_services_hr_payroll',
    'paie_maroc_cumarex': 'sahara_info_services_paie_maroc',
    'cumarex_hr_payroll_damancom': 'sahara_info_services_hr_payroll_damancom',
}


def migrate_module_names(env):
    print("\n=== MIGRATION Cumarex -> Sahara Info Services ===\n")
    
    # 1. ir.model.data (XML IDs)
    print("1. Mise à jour des XML IDs (ir.model.data)...")
    total = 0
    for old_name, new_name in OLD_NEW_MODULES.items():
        records = env['ir.model.data'].search([('module', '=', old_name)])
        count = len(records)
        if count:
            records.write({'module': new_name})
            print(f"   {old_name} -> {new_name}: {count} enregistrements")
            total += count
        else:
            print(f"   {old_name}: non trouvé (OK)")
    print(f"   Total: {total} XML IDs mis à jour\n")

    # 2. ir.module.module (noms techniques)
    print("2. Mise à jour des modules installés (ir.module.module)...")
    for old_name, new_name in OLD_NEW_MODULES.items():
        module = env['ir.module.module'].search([('name', '=', old_name)], limit=1)
        if module:
            module.write({'name': new_name})
            print(f"   {old_name} -> {new_name}: OK (état={module.state})")
        else:
            print(f"   {old_name}: non trouvé (OK)")
    print()

    # 3. Dépendances inter-modules
    print("3. Mise à jour des dépendances (ir.module.module.dependency)...")
    for old_name, new_name in OLD_NEW_MODULES.items():
        deps = env['ir.module.module.dependency'].search([('name', '=', old_name)])
        if deps:
            deps.write({'name': new_name})
            print(f"   Dépendance '{old_name}' -> '{new_name}': {len(deps)} enregistrements")
    print()

    env.cr.commit()
    print("=== MIGRATION TERMINÉE ===\n")
    print("Redémarrez Odoo avec l'option -u all ou mettez à jour les modules manuellement.")
    print("Modules à mettre à jour: sahara_info_services_hr_payroll, sahara_info_services_paie_maroc, sahara_info_services_hr_payroll_damancom")


# Point d'entrée
if 'env' in locals():
    migrate_module_names(env)
else:
    print("ERREUR: 'env' non trouvé. Exécutez ce script depuis un shell Odoo.")
