# -*- coding: utf-8 -*-
"""
Migration post-upgrade 19.0.1.0.7 — ORM + SQL de secours.
Crée le type 'Salarié Maroc' et la structure 'Maroc - Salarié Standard'.
"""
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)
MODULE = 'sahara_info_paie_maroc'


def migrate(cr, version):
    _logger.info('[paie_maroc] ===== MIGRATION 19.0.1.0.7 START =====')
    env = api.Environment(cr, SUPERUSER_ID, {})

    # ── 1. Type de structure ────────────────────────────────────────────
    try:
        st = env['hr.payroll.structure.type'].search(
            [('name', '=', 'Salarié Maroc')], limit=1)
        if not st:
            st = env['hr.payroll.structure.type'].create({
                'name': 'Salarié Maroc',
                'wage_type': 'monthly',
            })
            _logger.info('[paie_maroc] Type créé id=%s', st.id)
        else:
            _logger.info('[paie_maroc] Type existant id=%s', st.id)
    except Exception as e:
        _logger.error('[paie_maroc] Erreur création type: %s', e, exc_info=True)
        raise

    # ── 2. XML ID du type ───────────────────────────────────────────────
    try:
        xid = env['ir.model.data'].search([
            ('module', '=', MODULE),
            ('name', '=', 'structure_type_employee_ma'),
        ], limit=1)
        if not xid:
            env['ir.model.data'].create({
                'name': 'structure_type_employee_ma',
                'module': MODULE,
                'model': 'hr.payroll.structure.type',
                'res_id': st.id,
                'noupdate': False,
            })
            _logger.info('[paie_maroc] XML ID type créé')
        else:
            xid.write({'res_id': st.id, 'noupdate': False})
            _logger.info('[paie_maroc] XML ID type mis à jour → %s', st.id)
    except Exception as e:
        _logger.error('[paie_maroc] Erreur XML ID type: %s', e, exc_info=True)
        raise

    # ── 3. Structure salariale ──────────────────────────────────────────
    try:
        struct = env['hr.payroll.structure'].search(
            [('type_id', '=', st.id)], limit=1)
        if not struct:
            vals = {'name': 'Maroc - Salarié Standard', 'type_id': st.id}
            if 'code' in env['hr.payroll.structure']._fields:
                vals['code'] = 'MA_STD'
            struct = env['hr.payroll.structure'].create(vals)
            _logger.info('[paie_maroc] Structure créée id=%s', struct.id)
        else:
            _logger.info('[paie_maroc] Structure existante id=%s', struct.id)
    except Exception as e:
        _logger.error('[paie_maroc] Erreur création structure: %s', e, exc_info=True)
        raise

    # ── 4. XML ID de la structure ───────────────────────────────────────
    try:
        xid2 = env['ir.model.data'].search([
            ('module', '=', MODULE),
            ('name', '=', 'hr_payroll_structure_ma_employee'),
        ], limit=1)
        if not xid2:
            env['ir.model.data'].create({
                'name': 'hr_payroll_structure_ma_employee',
                'module': MODULE,
                'model': 'hr.payroll.structure',
                'res_id': struct.id,
                'noupdate': False,
            })
            _logger.info('[paie_maroc] XML ID structure créé')
        else:
            xid2.write({'res_id': struct.id, 'noupdate': False})
            _logger.info('[paie_maroc] XML ID structure mis à jour → %s', struct.id)
    except Exception as e:
        _logger.error('[paie_maroc] Erreur XML ID structure: %s', e, exc_info=True)
        raise

    _logger.info('[paie_maroc] ===== MIGRATION 19.0.1.0.7 OK =====')
