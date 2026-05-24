# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DamancomGenerateWizard(models.TransientModel):
    _name = 'damancom.generate.wizard'
    _description = 'Assistant de génération rapide de déclaration Damancom'

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )
    period_year = fields.Integer(
        string='Année',
        required=True,
        default=lambda self: fields.Date.today().year,
    )
    period_month = fields.Selection(
        selection=[
            ('1', 'Janvier'), ('2', 'Février'), ('3', 'Mars'),
            ('4', 'Avril'), ('5', 'Mai'), ('6', 'Juin'),
            ('7', 'Juillet'), ('8', 'Août'), ('9', 'Septembre'),
            ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre'),
        ],
        string='Mois',
        required=True,
        default=lambda self: str(fields.Date.today().month),
    )
    declaration_type = fields.Selection(
        selection=[
            ('principale', 'Déclaration Principale'),
            ('complementaire', 'Déclaration Complémentaire'),
        ],
        string='Type',
        required=True,
        default='principale',
    )
    sequence_number = fields.Integer(
        string='N° Séquence Complémentaire',
        default=1,
    )

    def action_create_declaration(self):
        self.ensure_one()
        
        # Vérifier qu'il n'existe pas déjà une déclaration pour cette période/type
        existing = self.env['damancom.declaration'].search([
            ('company_id', '=', self.company_id.id),
            ('period_year', '=', self.period_year),
            ('period_month', '=', int(self.period_month)),
            ('declaration_type', '=', self.declaration_type),
            ('state', '!=', 'rejected'),
        ])
        if existing and self.declaration_type == 'principale':
            raise UserError(_(
                "Une déclaration principale existe déjà pour la période %s/%s.\n"
                "Référence: %s\nÉtat: %s"
            ) % (self.period_month, self.period_year, existing[0].name, existing[0].state))

        declaration = self.env['damancom.declaration'].create({
            'company_id': self.company_id.id,
            'period_year': self.period_year,
            'period_month': int(self.period_month),
            'declaration_type': self.declaration_type,
            'sequence_number': self.sequence_number,
        })

        # Charger automatiquement les fiches de paie
        try:
            declaration.action_load_payslips()
        except UserError:
            # Pas de fiches de paie : on continue quand même, l'utilisateur 
            # remplira manuellement
            pass

        return {
            'type': 'ir.actions.act_window',
            'name': _('Déclaration Damancom'),
            'res_model': 'damancom.declaration',
            'res_id': declaration.id,
            'view_mode': 'form',
            'target': 'current',
        }
