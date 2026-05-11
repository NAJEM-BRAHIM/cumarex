# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .damancom_utils import validate_num_immatriculation


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_ma_cnss_num_imma = fields.Char(
        string="N° Immatriculation CNSS",
        size=9,
        help="Numéro d'immatriculation CNSS du salarié (9 chiffres). "
             "Le premier chiffre doit être 1 (sauf cas spéciaux). "
             "La clé de contrôle est validée selon l'algorithme officiel CNSS.\n\n"
             "Cas spéciaux acceptés:\n"
             "- 000000000 : salarié en attente de N° immatriculation (CIN obligatoire)\n"
             "- 999999999 : main d'œuvre occasionnelle",
    )

    l10n_ma_cnss_occasionnel = fields.Boolean(
        string="Main d'œuvre occasionnelle",
        default=False,
        help="Si coché, le salarié sera déclaré comme occasionnel (N° 999999999).",
    )

    l10n_ma_cnss_situation_default = fields.Selection(
        selection=[
            ('', 'Travail normal'),
            ('SO', 'SO - Sortant'),
            ('DE', 'DE - Décédé'),
            ('IT', 'IT - Maternité'),
            ('IL', 'IL - Maladie'),
            ('AT', 'AT - Accident de Travail'),
            ('CS', 'CS - Congé Sans salaire'),
            ('MS', 'MS - Maintenu Sans Salaire'),
            ('MP', 'MP - Maladie Professionnelle'),
        ],
        string="Situation CNSS par défaut",
        default='',
        help="Situation CNSS par défaut du salarié (sera appliquée aux fiches de paie).",
    )

    @api.constrains('l10n_ma_cnss_num_imma')
    def _check_num_imma(self):
        for employee in self:
            if employee.l10n_ma_cnss_num_imma:
                valid, msg = validate_num_immatriculation(employee.l10n_ma_cnss_num_imma)
                if not valid:
                    raise ValidationError(
                        _("N° immatriculation CNSS invalide pour %s: %s") % (
                            employee.name, msg
                        )
                    )
