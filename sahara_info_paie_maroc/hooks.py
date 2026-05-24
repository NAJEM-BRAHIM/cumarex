# -*- coding: utf-8 -*-
"""
Hooks d'installation et de migration pour sahara_info_paie_maroc.
Garantit la création du type de structure et de la structure salariale
indépendamment du chargement XML.
"""
import logging

_logger = logging.getLogger(__name__)


def _ensure_ma_structure(env):
    """
    Crée (ou récupère) le type de structure 'Salarié Maroc' et
    la structure 'Maroc - Salarié Standard' en Odoo 19.
    """
    StructureType = env['hr.payroll.structure.type']
    Structure = env['hr.payroll.structure']
    IrModelData = env['ir.model.data']

    # ── 1. Type de structure ────────────────────────────────────────────
    st = env.ref('sahara_info_paie_maroc.structure_type_employee_ma',
                 raise_if_not_found=False)

    if not st:
        # Chercher par nom au cas où le record existe sans XML ID
        st = StructureType.search([('name', '=', 'Salarié Maroc')], limit=1)

    if not st:
        _logger.info('[paie_maroc] Création du type de structure Salarié Maroc')
        st = StructureType.create({
            'name': 'Salarié Maroc',
            'wage_type': 'monthly',
        })

    # S'assurer que l'XML ID est enregistré
    existing_xid = IrModelData.search([
        ('module', '=', 'sahara_info_paie_maroc'),
        ('name', '=', 'structure_type_employee_ma'),
    ], limit=1)
    if not existing_xid:
        IrModelData.create({
            'name': 'structure_type_employee_ma',
            'module': 'sahara_info_paie_maroc',
            'model': 'hr.payroll.structure.type',
            'res_id': st.id,
            'noupdate': False,
        })
    else:
        existing_xid.write({'res_id': st.id})

    _logger.info('[paie_maroc] Type de structure OK: %s (id=%s)', st.name, st.id)

    # ── 2. Structure salariale ──────────────────────────────────────────
    struct = env.ref('sahara_info_paie_maroc.hr_payroll_structure_ma_employee',
                     raise_if_not_found=False)

    if not struct:
        struct = Structure.search([('type_id', '=', st.id)], limit=1)

    if not struct:
        _logger.info('[paie_maroc] Création de la structure Maroc - Salarié Standard')
        vals = {
            'name': 'Maroc - Salarié Standard',
            'type_id': st.id,
        }
        # Le champ 'code' n'existe peut-être plus en Odoo 19 — on vérifie
        if 'code' in Structure._fields:
            vals['code'] = 'MA_STD'
        struct = Structure.create(vals)

    # S'assurer que l'XML ID est enregistré
    existing_xid2 = IrModelData.search([
        ('module', '=', 'sahara_info_paie_maroc'),
        ('name', '=', 'hr_payroll_structure_ma_employee'),
    ], limit=1)
    if not existing_xid2:
        IrModelData.create({
            'name': 'hr_payroll_structure_ma_employee',
            'module': 'sahara_info_paie_maroc',
            'model': 'hr.payroll.structure',
            'res_id': struct.id,
            'noupdate': False,
        })
    else:
        existing_xid2.write({'res_id': struct.id})

    _logger.info('[paie_maroc] Structure OK: %s (id=%s)', struct.name, struct.id)


def post_init_hook(env):
    """Appelé après une installation fraîche du module."""
    _ensure_ma_structure(env)


def post_migrate_hook(env, version):
    """Appelé après chaque mise à jour du module."""
    _ensure_ma_structure(env)
