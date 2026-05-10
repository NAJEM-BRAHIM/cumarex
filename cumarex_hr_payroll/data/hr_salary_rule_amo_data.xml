<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">

        <!-- ================================================================
             ASSURANCE MALADIE OBLIGATOIRE (AMO)
             Déplafonnée - Calculée sur le salaire brut total
             ================================================================ -->

        <!-- AMO - Part Salariale : 2,26% (déplafonnée) -->
        <record id="ma_rule_amo_sal" model="hr.salary.rule">
            <field name="name">AMO - Part Salariale (2,26%)</field>
            <field name="code">AMO_SAL</field>
            <field name="sequence">210</field>
            <field name="category_id" ref="ma_rule_category_amo"/>
            <field name="condition_select">none</field>
            <field name="amount_select">code</field>
            <field name="amount_python_compute">
# AMO de base salariale : 2,26% sur salaire brut sans plafond
result = -(SBC * 0.0226)
            </field>
            <field name="struct_id" ref="hr_payroll_structure_ma_employee"/>
            <field name="appears_on_payslip">True</field>
        </record>

        <!-- AMO - Part Patronale : 4,11% (2,26% AMO + 1,85% solidarité) -->
        <record id="ma_rule_amo_pat" model="hr.salary.rule">
            <field name="name">AMO - Part Patronale (4,11%)</field>
            <field name="code">AMO_PAT</field>
            <field name="sequence">610</field>
            <field name="category_id" ref="ma_rule_category_patronal"/>
            <field name="condition_select">none</field>
            <field name="amount_select">code</field>
            <field name="amount_python_compute">
# AMO patronale : 2,26% AMO base + 1,85% solidarité = 4,11%
result = -(SBC * 0.0411)
            </field>
            <field name="struct_id" ref="hr_payroll_structure_ma_employee"/>
            <field name="appears_on_payslip">True</field>
        </record>

        <!-- ================================================================
             CIMR - Retraite Complémentaire (Optionnel)
             ================================================================ -->

        <record id="ma_rule_cimr_sal" model="hr.salary.rule">
            <field name="name">CIMR - Part Salariale</field>
            <field name="code">CIMR_SAL</field>
            <field name="sequence">220</field>
            <field name="category_id" ref="ma_rule_category_cnss"/>
            <field name="condition_select">python</field>
            <field name="condition_python">result = contract.l10n_ma_affilie_cimr and contract.l10n_ma_taux_cimr > 0</field>
            <field name="amount_select">code</field>
            <field name="amount_python_compute">
result = -(SBC * (contract.l10n_ma_taux_cimr / 100.0))
            </field>
            <field name="struct_id" ref="hr_payroll_structure_ma_employee"/>
            <field name="appears_on_payslip">True</field>
        </record>

        <record id="ma_rule_cimr_pat" model="hr.salary.rule">
            <field name="name">CIMR - Part Patronale</field>
            <field name="code">CIMR_PAT</field>
            <field name="sequence">620</field>
            <field name="category_id" ref="ma_rule_category_patronal"/>
            <field name="condition_select">python</field>
            <field name="condition_python">result = contract.l10n_ma_affilie_cimr and contract.l10n_ma_taux_cimr_patronal > 0</field>
            <field name="amount_select">code</field>
            <field name="amount_python_compute">
result = -(SBC * (contract.l10n_ma_taux_cimr_patronal / 100.0))
            </field>
            <field name="struct_id" ref="hr_payroll_structure_ma_employee"/>
            <field name="appears_on_payslip">True</field>
        </record>

        <!-- ================================================================
             MUTUELLE COMPLÉMENTAIRE (Optionnel)
             ================================================================ -->

        <record id="ma_rule_mutuelle_sal" model="hr.salary.rule">
            <field name="name">Mutuelle - Part Salariale</field>
            <field name="code">MUTUELLE_SAL</field>
            <field name="sequence">230</field>
            <field name="category_id" ref="ma_rule_category_amo"/>
            <field name="condition_select">python</field>
            <field name="condition_python">result = contract.l10n_ma_mutuelle > 0</field>
            <field name="amount_select">code</field>
            <field name="amount_python_compute">result = -contract.l10n_ma_mutuelle</field>
            <field name="struct_id" ref="hr_payroll_structure_ma_employee"/>
            <field name="appears_on_payslip">True</field>
        </record>

        <record id="ma_rule_mutuelle_pat" model="hr.salary.rule">
            <field name="name">Mutuelle - Part Patronale</field>
            <field name="code">MUTUELLE_PAT</field>
            <field name="sequence">630</field>
            <field name="category_id" ref="ma_rule_category_patronal"/>
            <field name="condition_select">python</field>
            <field name="condition_python">result = contract.l10n_ma_mutuelle_patronal > 0</field>
            <field name="amount_select">code</field>
            <field name="amount_python_compute">result = -contract.l10n_ma_mutuelle_patronal</field>
            <field name="struct_id" ref="hr_payroll_structure_ma_employee"/>
            <field name="appears_on_payslip">True</field>
        </record>

    </data>
</odoo>
