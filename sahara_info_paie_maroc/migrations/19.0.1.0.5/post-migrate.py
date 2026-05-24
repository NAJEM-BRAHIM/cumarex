# -*- coding: utf-8 -*-
"""
Script de migration post-upgrade vers 19.0.1.0.5.
Garantit la création du type de structure 'Salarié Maroc' et
de la structure salariale 'Maroc - Salarié Standard'.
S'exécute après chaque upgrade vers cette version, indépendamment du XML.
"""
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    StructureType = env['hr.payroll.structure.type']
    Structure = env['hr.payroll.structure']
    IrModelData = env['ir.model.data']

    # ── 1. Type de structure ────────────────────────────────────────────
    st = env.ref('sahara_info_paie_maroc.structure_type_employee_ma',
                 raise_if_not_found=False)
    if not st:
        st = StructureType.search([('name', '=', 'Salarié Maroc')], limit=1)
    if not st:
        _logger.info('[paie_maroc] Migration: création du type Salarié Maroc')
        st = StructureType.create({
            'name': 'Salarié Maroc',
            'wage_type': 'monthly',
        })
    xid = IrModelData.search([
        ('module', '=', 'sahara_info_paie_maroc'),
        ('name', '=', 'structure_type_employee_ma'),
    ], limit=1)
    if not xid:
        IrModelData.create({
            'name': 'structure_type_employee_ma',
            'module': 'sahara_info_paie_maroc',
            'model': 'hr.payroll.structure.type',
            'res_id': st.id,
            'noupdate': False,
        })
    else:
        xid.write({'res_id': st.id})
    _logger.info('[paie_maroc] Type structure OK: %s id=%s', st.name, st.id)

    # ── 2. Structure salariale ──────────────────────────────────────────
    struct = env.ref('sahara_info_paie_maroc.hr_payroll_structure_ma_employee',
                     raise_if_not_found=False)
    if not struct:
        struct = Structure.search([('type_id', '=', st.id)], limit=1)
    if not struct:
        _logger.info('[paie_maroc] Migration: création de la structure MA_STD')
        vals = {'name': 'Maroc - Salarié Standard', 'type_id': st.id}
        if 'code' in Structure._fields:
            vals['code'] = 'MA_STD'
        struct = Structure.create(vals)
    xid2 = IrModelData.search([
        ('module', '=', 'sahara_info_paie_maroc'),
        ('name', '=', 'hr_payroll_structure_ma_employee'),
    ], limit=1)
    if not xid2:
        IrModelData.create({
            'name': 'hr_payroll_structure_ma_employee',
            'module': 'sahara_info_paie_maroc',
            'model': 'hr.payroll.structure',
            'res_id': struct.id,
            'noupdate': False,
        })
    else:
        xid2.write({'res_id': struct.id})
    _logger.info('[paie_maroc] Structure OK: %s id=%s', struct.name, struct.id)
