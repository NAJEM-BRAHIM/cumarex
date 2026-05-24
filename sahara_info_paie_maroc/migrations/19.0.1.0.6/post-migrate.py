# -*- coding: utf-8 -*-
"""
Migration post-upgrade 19.0.1.0.6 — SQL pur, sans ORM.
Crée le type de structure 'Salarié Maroc' et la structure
'Maroc - Salarié Standard' directement en base.
"""
import logging

_logger = logging.getLogger(__name__)

MODULE = 'sahara_info_paie_maroc'


def migrate(cr, version):
    _logger.info('[paie_maroc] ========== DÉBUT MIGRATION 19.0.1.0.6 ==========')

    # ── 1. Vérifier que la table existe ────────────────────────────────
    cr.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN ('hr_payroll_structure_type', 'hr_payroll_structure', 'ir_model_data')
    """)
    tables = {r[0] for r in cr.fetchall()}
    _logger.info('[paie_maroc] Tables trouvées: %s', tables)

    if 'hr_payroll_structure_type' not in tables:
        _logger.error('[paie_maroc] Table hr_payroll_structure_type introuvable — abandon')
        return

    # ── 2. Colonnes disponibles sur hr_payroll_structure_type ──────────
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'hr_payroll_structure_type'
    """)
    type_cols = {r[0] for r in cr.fetchall()}
    _logger.info('[paie_maroc] Colonnes hr_payroll_structure_type: %s', sorted(type_cols))

    # ── 3. Créer ou récupérer le type de structure ──────────────────────
    cr.execute(
        "SELECT id FROM hr_payroll_structure_type WHERE name = %s LIMIT 1",
        ('Salarié Maroc',)
    )
    row = cr.fetchone()

    if row:
        st_id = row[0]
        _logger.info('[paie_maroc] Type existant id=%s', st_id)
    else:
        # Construire l'INSERT selon les colonnes disponibles
        cols = ['name']
        vals = ['Salarié Maroc']
        placeholders = ['%s']

        if 'wage_type' in type_cols:
            cols.append('wage_type')
            vals.append('monthly')
            placeholders.append('%s')
        if 'active' in type_cols:
            cols.append('active')
            vals.append(True)
            placeholders.append('%s')

        sql = "INSERT INTO hr_payroll_structure_type ({}) VALUES ({}) RETURNING id".format(
            ', '.join(cols), ', '.join(placeholders)
        )
        _logger.info('[paie_maroc] SQL type: %s | vals: %s', sql, vals)
        cr.execute(sql, vals)
        st_id = cr.fetchone()[0]
        _logger.info('[paie_maroc] Type créé id=%s', st_id)

    # ── 4. Enregistrer l'XML ID du type ────────────────────────────────
    _upsert_xml_id(cr, MODULE, 'structure_type_employee_ma',
                   'hr.payroll.structure.type', st_id)

    # ── 5. Colonnes disponibles sur hr_payroll_structure ───────────────
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'hr_payroll_structure'
    """)
    struct_cols = {r[0] for r in cr.fetchall()}
    _logger.info('[paie_maroc] Colonnes hr_payroll_structure: %s', sorted(struct_cols))

    # ── 6. Créer ou récupérer la structure ─────────────────────────────
    cr.execute(
        "SELECT id FROM hr_payroll_structure WHERE type_id = %s LIMIT 1",
        (st_id,)
    )
    row2 = cr.fetchone()

    if row2:
        struct_id = row2[0]
        _logger.info('[paie_maroc] Structure existante id=%s', struct_id)
    else:
        cols2 = ['name', 'type_id']
        vals2 = ['Maroc - Salarié Standard', st_id]
        ph2 = ['%s', '%s']

        if 'code' in struct_cols:
            cols2.append('code')
            vals2.append('MA_STD')
            ph2.append('%s')
        if 'active' in struct_cols:
            cols2.append('active')
            vals2.append(True)
            ph2.append('%s')

        sql2 = "INSERT INTO hr_payroll_structure ({}) VALUES ({}) RETURNING id".format(
            ', '.join(cols2), ', '.join(ph2)
        )
        _logger.info('[paie_maroc] SQL structure: %s | vals: %s', sql2, vals2)
        cr.execute(sql2, vals2)
        struct_id = cr.fetchone()[0]
        _logger.info('[paie_maroc] Structure créée id=%s', struct_id)

    # ── 7. Enregistrer l'XML ID de la structure ────────────────────────
    _upsert_xml_id(cr, MODULE, 'hr_payroll_structure_ma_employee',
                   'hr.payroll.structure', struct_id)

    _logger.info('[paie_maroc] ========== MIGRATION TERMINÉE ==========')


def _upsert_xml_id(cr, module, name, model, res_id):
    # Odoo 19 : date_update / date_init supprimés de ir_model_data
    cr.execute("""
        SELECT id FROM ir_model_data
        WHERE module = %s AND name = %s LIMIT 1
    """, (module, name))
    row = cr.fetchone()
    if row:
        cr.execute("""
            UPDATE ir_model_data SET res_id = %s, noupdate = false
            WHERE module = %s AND name = %s
        """, (res_id, module, name))
        _logger.info('[paie_maroc] XML ID mis à jour: %s.%s → %s', module, name, res_id)
    else:
        cr.execute("""
            INSERT INTO ir_model_data (name, module, model, res_id, noupdate)
            VALUES (%s, %s, %s, %s, false)
        """, (name, module, model, res_id))
        _logger.info('[paie_maroc] XML ID créé: %s.%s → %s', module, name, res_id)
