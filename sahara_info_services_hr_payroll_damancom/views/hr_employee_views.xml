<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="view_employee_form_inherit_cnss" model="ir.ui.view">
        <field name="name">hr.employee.form.inherit.cnss</field>
        <field name="model">hr.employee</field>
        <field name="inherit_id" ref="hr.view_employee_form"/>
        <field name="arch" type="xml">
            <xpath expr="//notebook" position="inside">
                <page string="CNSS Damancom" name="cnss_damancom">
                    <group>
                        <group string="Identification CNSS">
                            <field name="l10n_ma_cnss_num_imma" 
                                   placeholder="ex: 168764721 (9 chiffres)"/>
                            <field name="l10n_ma_cnss_occasionnel"/>
                            <field name="l10n_ma_cnss_situation_default"/>
                        </group>
                        <group string="Information">
                            <div class="text-muted" colspan="2">
                                <p>
                                    Le <b>numéro d'immatriculation CNSS</b> doit comporter 
                                    <b>9 chiffres</b> et est validé selon l'algorithme officiel CNSS.
                                </p>
                                <p>
                                    Cas spéciaux:<br/>
                                    • <b>000000000</b> : salarié en attente (CIN obligatoire)<br/>
                                    • <b>999999999</b> : main d'œuvre occasionnelle
                                </p>
                            </div>
                        </group>
                    </group>
                </page>
            </xpath>
        </field>
    </record>

</odoo>
