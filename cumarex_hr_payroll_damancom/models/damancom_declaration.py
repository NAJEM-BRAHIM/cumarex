# -*- coding: utf-8 -*-
import base64
import io
from datetime import date

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from .damancom_utils import (
    validate_num_affilie,
    validate_num_immatriculation,
    clean_text_for_bds,
    format_an,
    format_n,
    format_centimes,
    format_period,
    format_date,
    pad_record,
    SITUATION_RANGS,
    PLAFOND_CNSS_DEFAULT,
)


class DamancomDeclaration(models.Model):
    _name = 'damancom.declaration'
    _description = 'Declaration CNSS Damancom'
    _order = 'date_declaration desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    company_id = fields.Many2one('res.company', string='Societe', required=True, default=lambda self: self.env.company)
    period_year = fields.Integer(string='Annee', required=True, default=lambda self: fields.Date.today().year)
    period_month = fields.Integer(string='Mois', required=True, default=lambda self: fields.Date.today().month)
    period_str = fields.Char(string='Periode', compute='_compute_period_str', store=True)
    declaration_type = fields.Selection(
        selection=[('principale', 'Declaration Principale'), ('complementaire', 'Declaration Complementaire')],
        string='Type', required=True, default='principale')
    sequence_number = fields.Integer(string='N Sequence Complementaire', default=1)
    date_declaration = fields.Date(string='Date Declaration', default=fields.Date.context_today, required=True)
    date_exigibilite = fields.Date(string="Date Exigibilite")
    state = fields.Selection(
        selection=[('draft', 'Brouillon'), ('generated', 'Genere'), ('submitted', 'Soumis a Damancom'),
                   ('validated', 'Valide par CNSS'), ('rejected', 'Rejete')],
        string='Etat', default='draft', required=True, tracking=True)
    payslip_ids = fields.Many2many('hr.payslip', string='Fiches de paie',
        domain="[('state', 'in', ['done', 'paid']), ('company_id', '=', company_id)]")

    identif_transfert = fields.Char(string="Identifiant Transfert (CNSS)", size=14)
    preetabli_imported = fields.Boolean(string="Preetabli importe", default=False, readonly=True)
    preetabli_file = fields.Binary(string="Fichier Preetabli AFFEBDS", attachment=True)
    preetabli_filename = fields.Char(string="Nom Fichier Preetabli")
    line_ids = fields.One2many('damancom.declaration.line', 'declaration_id', string='Lignes de declaration')

    total_salaries = fields.Integer(string='Nombre Salaries', compute='_compute_totals', store=True)
    total_jours = fields.Integer(string='Total Jours', compute='_compute_totals', store=True)
    total_salaire_reel = fields.Float(string='Total Salaire Reel (DH)', compute='_compute_totals', store=True, digits=(15, 2))
    total_salaire_plaf = fields.Float(string='Total Salaire Plafonne (DH)', compute='_compute_totals', store=True, digits=(15, 2))

    bds_file = fields.Binary(string='Fichier BDS', attachment=True, readonly=True)
    bds_filename = fields.Char(string='Nom du fichier BDS', readonly=True)
    bds_generated_date = fields.Datetime(string='Date Generation', readonly=True)
    notes = fields.Text(string='Notes')

    @api.depends('period_year', 'period_month')
    def _compute_period_str(self):
        for rec in self:
            if rec.period_year and rec.period_month:
                rec.period_str = format_period(rec.period_year, rec.period_month)
            else:
                rec.period_str = ''

    @api.depends('period_str', 'company_id', 'declaration_type', 'sequence_number')
    def _compute_name(self):
        for rec in self:
            type_str = 'Principale' if rec.declaration_type == 'principale' else f'Complementaire #{rec.sequence_number}'
            company_str = rec.company_id.name or ''
            rec.name = f"BDS {rec.period_str} - {company_str} ({type_str})"

    @api.depends('line_ids', 'line_ids.jours_declares', 'line_ids.salaire_reel', 'line_ids.salaire_plafonne')
    def _compute_totals(self):
        for rec in self:
            rec.total_salaries = len(rec.line_ids)
            rec.total_jours = sum(rec.line_ids.mapped('jours_declares'))
            rec.total_salaire_reel = sum(rec.line_ids.mapped('salaire_reel'))
            rec.total_salaire_plaf = sum(rec.line_ids.mapped('salaire_plafonne'))

    @api.constrains('period_month')
    def _check_period_month(self):
        for rec in self:
            if rec.period_month < 1 or rec.period_month > 12:
                raise ValidationError(_("Le mois doit etre entre 1 et 12."))

    @api.constrains('sequence_number')
    def _check_sequence_number(self):
        for rec in self:
            if rec.declaration_type == 'complementaire' and (rec.sequence_number < 1 or rec.sequence_number > 9):
                raise ValidationError(_("Le numero de sequence doit etre entre 1 et 9."))

    def action_load_payslips(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Seules les declarations en brouillon peuvent charger les fiches de paie."))
        self.line_ids.unlink()
        start_date = date(self.period_year, self.period_month, 1)
        if self.period_month == 12:
            end_date = date(self.period_year + 1, 1, 1)
        else:
            end_date = date(self.period_year, self.period_month + 1, 1)
        payslips = self.env['hr.payslip'].search([
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', start_date),
            ('date_from', '<', end_date),
        ])
        if not payslips:
            raise UserError(_("Aucune fiche de paie validee trouvee pour la periode %s/%s.") % (self.period_month, self.period_year))
        self.payslip_ids = [(6, 0, payslips.ids)]
        lines_data = []
        plafond = PLAFOND_CNSS_DEFAULT
        for payslip in payslips:
            employee = payslip.employee_id
            if employee.l10n_ma_cnss_occasionnel:
                num_imma = '999999999'
            elif employee.l10n_ma_cnss_num_imma:
                num_imma = employee.l10n_ma_cnss_num_imma
            else:
                num_imma = '000000000'
            sbc_line = payslip.line_ids.filtered(lambda l: l.code == 'SBC')
            sbg_line = payslip.line_ids.filtered(lambda l: l.code == 'SBG')
            salaire_reel = sbc_line[:1].total if sbc_line else (sbg_line[:1].total if sbg_line else 0.0)
            salaire_plaf = min(salaire_reel, plafond)
            situation = payslip.l10n_ma_cnss_situation or ''
            jours = payslip.l10n_ma_cnss_jours or 26
            if situation in ('CS', 'MS'):
                jours = 0
                salaire_reel = 0.0
                salaire_plaf = 0.0
            af_line = payslip.line_ids.filtered(lambda l: l.code == 'ALLOC_FAM')
            af_a_payer = af_line[:1].total if af_line else 0.0
            af_a_deduire = 0.0
            af_net_a_payer = af_a_payer - af_a_deduire
            af_a_reverser = af_net_a_payer
            lines_data.append((0, 0, {
                'employee_id': employee.id, 'payslip_id': payslip.id,
                'num_immatriculation': num_imma, 'nom_prenom': employee.name,
                'num_cin': employee.identification_id or '',
                'jours_declares': jours, 'salaire_reel': salaire_reel,
                'salaire_plafonne': salaire_plaf, 'situation': situation,
                'nb_enfants': employee.children if hasattr(employee, 'children') else 0,
                'af_a_payer': af_a_payer, 'af_a_deduire': af_a_deduire,
                'af_net_a_payer': af_net_a_payer, 'af_a_reverser': af_a_reverser,
                'is_entrant': self._is_entrant(employee, payslip),
            }))
        self.line_ids = lines_data
        return True

    def _is_entrant(self, employee, payslip):
        prev_payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', employee.id), ('company_id', '=', self.company_id.id),
            ('state', 'in', ['done', 'paid']), ('date_from', '<', payslip.date_from),
        ], limit=1)
        return not prev_payslips

    def action_validate(self):
        self.ensure_one()
        errors = []
        if not self.company_id.l10n_ma_cnss_num_affilie:
            errors.append(_("N d'affiliation CNSS non configure pour la societe."))
        else:
            valid, msg = validate_num_affilie(self.company_id.l10n_ma_cnss_num_affilie)
            if not valid:
                errors.append(_("N d'affiliation CNSS invalide: %s") % msg)
        if not self.line_ids:
            errors.append(_("Aucune ligne dans la declaration. Chargez les fiches de paie d'abord."))
        for line in self.line_ids:
            if not line.is_entrant:
                if line.num_immatriculation in ('000000000', ''):
                    errors.append(_("Employe %s: N d'immatriculation CNSS manquant.") % line.employee_id.name)
                else:
                    valid, msg = validate_num_immatriculation(line.num_immatriculation)
                    if not valid:
                        errors.append(_("Employe %s: N immatriculation invalide (%s) - %s") % (line.employee_id.name, line.num_immatriculation, msg))
            if line.jours_declares > 26:
                errors.append(_("Employe %s: jours declares (%d) > 26") % (line.employee_id.name, line.jours_declares))
            if line.situation in ('CS', 'MS') and (line.jours_declares > 0 or line.salaire_reel > 0):
                errors.append(_("Employe %s: situation %s exige jours=0 et salaire=0") % (line.employee_id.name, line.situation))
            if line.num_immatriculation in ('000000000', '') and not line.num_cin:
                errors.append(_("Employe %s: N CIN obligatoire pour les entrants sans N d'immatriculation.") % line.employee_id.name)
            if line.salaire_plafonne > line.salaire_reel:
                errors.append(_("Employe %s: salaire plafonne (%s) > salaire reel (%s)") % (line.employee_id.name, line.salaire_plafonne, line.salaire_reel))
        if errors:
            raise ValidationError('\n'.join([_("Erreurs de validation:")] + errors))
        return True

    def action_generate_bds(self):
        self.ensure_one()
        self.action_validate()
        if self.declaration_type == 'principale':
            content = self._generate_bds_principale()
        else:
            content = self._generate_bds_complementaire()
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        period_mmaaaa = f"{self.period_month:02d}{self.period_year:04d}"
        if self.declaration_type == 'principale':
            filename = f"DS_{num_aff}_{period_mmaaaa}.txt"
        else:
            filename = f"DSC{self.sequence_number}_{num_aff}_{period_mmaaaa}.txt"
        self.write({
            'bds_file': base64.b64encode(content.encode('ascii', errors='replace')),
            'bds_filename': filename, 'bds_generated_date': fields.Datetime.now(), 'state': 'generated',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=damancom.declaration&id={self.id}&field=bds_file&filename_field=bds_filename&download=true',
            'target': 'self',
        }

    def _build_record_b00(self):
        if self.identif_transfert and self.identif_transfert.strip():
            identif_transfert = self.identif_transfert.strip().zfill(14)[:14]
        else:
            identif_transfert = format_n(0, 14)
        return pad_record('B00' + identif_transfert + 'B0' + ' ' * 241)

    def _build_record_b01(self):
        company = self.company_id
        return pad_record(
            'B01' +
            format_n(company.l10n_ma_cnss_num_affilie, 7) +
            self.period_str +
            format_an(company.name or '', 40) +
            format_an(company.l10n_ma_cnss_activite or '', 40) +
            format_an(company.street or '', 120) +
            format_an(company.city or '', 20) +
            format_an(company.l10n_ma_cnss_code_postal or company.zip or '', 6) +
            format_n(company.l10n_ma_cnss_code_agence or 0, 2) +
            format_date(self.date_declaration) +
            format_date(self.date_exigibilite or self.date_declaration))

    def _build_record_b02(self, line):
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        rang = SITUATION_RANGS.get(line.situation or '', 0)
        ctr = (int(line.num_immatriculation) + int(round(line.af_a_reverser * 100)) +
               line.jours_declares + int(round(line.salaire_reel * 100)) +
               int(round(line.salaire_plafonne * 100)) + rang)
        return pad_record(
            'B02' + format_n(num_aff, 7) + self.period_str +
            format_n(line.num_immatriculation, 9) +
            format_an(line.nom_prenom, 60) + format_n(line.nb_enfants, 2) +
            format_centimes(line.af_a_payer, 6) + format_centimes(line.af_a_deduire, 6) +
            format_centimes(line.af_net_a_payer, 6) + format_centimes(line.af_a_reverser, 6) +
            format_n(line.jours_declares, 2) + format_centimes(line.salaire_reel, 13) +
            format_centimes(line.salaire_plafonne, 9) + format_an(line.situation or '', 2) +
            format_n(ctr, 19) + ' ' * 104)

    def _build_record_b03(self, existants_lines):
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        nbr_salaries = len(existants_lines)
        t_enfants = sum(l.nb_enfants for l in existants_lines)
        t_af_a_payer = sum(l.af_a_payer for l in existants_lines)
        t_af_a_deduire = sum(l.af_a_deduire for l in existants_lines)
        t_af_net = sum(l.af_net_a_payer for l in existants_lines)
        t_af_reverser = sum(l.af_a_reverser for l in existants_lines)
        t_num_imma = sum(int(l.num_immatriculation) if l.num_immatriculation.strip().isdigit() else 0 for l in existants_lines)
        t_jours = sum(l.jours_declares for l in existants_lines)
        t_sal_reel = sum(l.salaire_reel for l in existants_lines)
        t_sal_plaf = sum(l.salaire_plafonne for l in existants_lines)
        t_ctr = sum(self._compute_line_ctr(l) for l in existants_lines)
        return pad_record(
            'B03' + format_n(num_aff, 7) + self.period_str +
            format_n(nbr_salaries, 6) + format_n(t_enfants, 6) +
            format_centimes(t_af_a_payer, 12) + format_centimes(t_af_a_deduire, 12) +
            format_centimes(t_af_net, 12) + format_n(t_num_imma, 15) +
            format_centimes(t_af_reverser, 12) + format_n(t_jours, 6) +
            format_centimes(t_sal_reel, 15) + format_centimes(t_sal_plaf, 13) +
            format_n(t_ctr, 19) + ' ' * 116)

    def _build_record_b04(self, line):
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        if line.num_immatriculation.strip().isdigit():
            num_for_ctr = int(line.num_immatriculation)
        else:
            num_for_ctr = 0
        ctr = (num_for_ctr + line.jours_declares +
               int(round(line.salaire_reel * 100)) + int(round(line.salaire_plafonne * 100)))
        return pad_record(
            'B04' + format_n(num_aff, 7) + self.period_str +
            format_n(line.num_immatriculation, 9) + format_an(line.nom_prenom, 60) +
            format_an(line.num_cin or '', 8) + format_n(line.jours_declares, 2) +
            format_centimes(line.salaire_reel, 13) + format_centimes(line.salaire_plafonne, 9) +
            format_n(ctr, 19) + ' ' * 124)

    def _build_record_b04_empty(self):
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        return pad_record(
            'B04' + format_n(num_aff, 7) + self.period_str +
            ' ' * 9 + ' ' * 60 + ' ' * 8 +
            format_n(0, 2) + format_centimes(0, 13) + format_centimes(0, 9) +
            format_n(0, 19) + ' ' * 124)

    def _build_record_b05(self, entrants_lines):
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        if not entrants_lines:
            nbr_salaries, t_num_imma, t_jours = 0, 0, 0
            t_sal_reel, t_sal_plaf, t_ctr = 0.0, 0.0, 0
        else:
            nbr_salaries = len(entrants_lines)
            t_num_imma = sum(int(l.num_immatriculation) if l.num_immatriculation.strip().isdigit() else 0 for l in entrants_lines)
            t_jours = sum(l.jours_declares for l in entrants_lines)
            t_sal_reel = sum(l.salaire_reel for l in entrants_lines)
            t_sal_plaf = sum(l.salaire_plafonne for l in entrants_lines)
            t_ctr = sum(self._compute_line_ctr(l, is_entrant=True) for l in entrants_lines)
        return pad_record(
            'B05' + format_n(num_aff, 7) + self.period_str +
            format_n(nbr_salaries, 6) + format_n(t_num_imma, 15) +
            format_n(t_jours, 6) + format_centimes(t_sal_reel, 15) +
            format_centimes(t_sal_plaf, 13) + format_n(t_ctr, 19) + ' ' * 170)

    def _build_record_b06(self, existants_lines, entrants_lines):
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        all_lines = list(existants_lines) + list(entrants_lines)
        nbr_salaries = len(all_lines)
        t_num_imma = sum(int(l.num_immatriculation) if l.num_immatriculation.strip().isdigit() else 0 for l in all_lines)
        t_jours = sum(l.jours_declares for l in all_lines)
        t_sal_reel = sum(l.salaire_reel for l in all_lines)
        t_sal_plaf = sum(l.salaire_plafonne for l in all_lines)
        t_ctr_exist = sum(self._compute_line_ctr(l) for l in existants_lines)
        t_ctr_entr = sum(self._compute_line_ctr(l, is_entrant=True) for l in entrants_lines)
        return pad_record(
            'B06' + format_n(num_aff, 7) + self.period_str +
            format_n(nbr_salaries, 6) + format_n(t_num_imma, 15) +
            format_n(t_jours, 6) + format_centimes(t_sal_reel, 15) +
            format_centimes(t_sal_plaf, 13) + format_n(t_ctr_exist + t_ctr_entr, 19) + ' ' * 170)

    def _compute_line_ctr(self, line, is_entrant=False):
        if is_entrant:
            num = int(line.num_immatriculation) if line.num_immatriculation.strip().isdigit() else 0
            return num + line.jours_declares + int(round(line.salaire_reel * 100)) + int(round(line.salaire_plafonne * 100))
        else:
            rang = SITUATION_RANGS.get(line.situation or '', 0)
            return (int(line.num_immatriculation) + int(round(line.af_a_reverser * 100)) +
                    line.jours_declares + int(round(line.salaire_reel * 100)) +
                    int(round(line.salaire_plafonne * 100)) + rang)

    def _generate_bds_principale(self):
        existants_lines = self.line_ids.filtered(lambda l: not l.is_entrant)
        entrants_lines = self.line_ids.filtered(lambda l: l.is_entrant)
        existants_lines = existants_lines.sorted(lambda l: l.num_immatriculation)
        entrants_lines = entrants_lines.sorted(lambda l: l.num_immatriculation)
        lines = []
        lines.append(self._build_record_b00())
        lines.append(self._build_record_b01())
        for line in existants_lines:
            lines.append(self._build_record_b02(line))
        lines.append(self._build_record_b03(existants_lines))
        if entrants_lines:
            for line in entrants_lines:
                lines.append(self._build_record_b04(line))
        else:
            lines.append(self._build_record_b04_empty())
        lines.append(self._build_record_b05(entrants_lines))
        lines.append(self._build_record_b06(existants_lines, entrants_lines))
        return '\n'.join(lines) + '\n'

    def _generate_bds_complementaire(self):
        entrants_lines = self.line_ids.filtered(lambda l: l.is_entrant)
        if not entrants_lines:
            raise UserError(_("Une declaration complementaire doit contenir au moins un entrant."))
        entrants_lines = entrants_lines.sorted(lambda l: l.num_immatriculation)
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        lines = []
        lines.append(pad_record('E00' + format_n(0, 14) + f'E{self.sequence_number}' + ' ' * 241))
        e01_content = self._build_record_b01().replace('B01', 'E01', 1)
        lines.append(e01_content)
        e02 = ('E02' + format_n(num_aff, 7) + self.period_str +
               ' ' * 9 + ' ' * 60 + format_n(0, 2) + format_n(0, 6) * 4 +
               format_n(0, 2) + format_n(0, 13) + format_n(0, 9) +
               ' ' * 2 + format_n(0, 19) + ' ' * 104)
        lines.append(pad_record(e02))
        e03 = ('E03' + format_n(num_aff, 7) + self.period_str +
               format_n(0, 6) * 3 + format_n(0, 12) * 3 + format_n(0, 15) +
               format_n(0, 12) + format_n(0, 6) + format_n(0, 15) +
               format_n(0, 13) + format_n(0, 19) + ' ' * 116)
        lines.append(pad_record(e03))
        for line in entrants_lines:
            lines.append(self._build_record_b04(line).replace('B04', 'E04', 1))
        lines.append(self._build_record_b05(entrants_lines).replace('B05', 'E05', 1))
        lines.append(self._build_record_b06(self.env['damancom.declaration.line'], entrants_lines).replace('B06', 'E06', 1))
        return '\n'.join(lines) + '\n'

    def action_download_bds(self):
        self.ensure_one()
        if not self.bds_file:
            raise UserError(_("Le fichier BDS n'a pas encore ete genere."))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=damancom.declaration&id={self.id}&field=bds_file&filename_field=bds_filename&download=true',
            'target': 'self',
        }

    def action_mark_submitted(self):
        self.write({'state': 'submitted'})

    def action_mark_validated(self):
        self.write({'state': 'validated'})

    def action_mark_rejected(self):
        self.write({'state': 'rejected'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'bds_file': False, 'bds_filename': False, 'bds_generated_date': False})


class DamancomDeclarationLine(models.Model):
    _name = 'damancom.declaration.line'
    _description = 'Ligne de Declaration Damancom'
    _order = 'is_entrant, num_immatriculation'

    declaration_id = fields.Many2one('damancom.declaration', string='Declaration', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employe', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Fiche de paie')
    num_immatriculation = fields.Char(string='N Immatriculation', size=9, required=True)
    nom_prenom = fields.Char(string='Nom et Prenom', required=True)
    num_cin = fields.Char(string='N CIN', size=8)
    nb_enfants = fields.Integer(string='Nb Enfants AF', default=0)
    jours_declares = fields.Integer(string='Jours Declares', default=26)
    salaire_reel = fields.Float(string='Salaire Reel (DH)', digits=(15, 2))
    salaire_plafonne = fields.Float(string='Salaire Plafonne (DH)', digits=(15, 2))
    situation = fields.Selection(
        selection=[('', 'Travail normal'), ('SO', 'SO - Sortant'), ('DE', 'DE - Decede'),
                   ('IT', 'IT - Maternite'), ('IL', 'IL - Maladie'), ('AT', 'AT - Accident de Travail'),
                   ('CS', 'CS - Conge Sans salaire'), ('MS', 'MS - Maintenu Sans Salaire'),
                   ('MP', 'MP - Maladie Professionnelle')],
        string='Situation', default='')
    af_a_payer = fields.Float(string='AF a Payer (DH)', default=0.0, digits=(15, 2))
    af_a_deduire = fields.Float(string='AF a Deduire (DH)', default=0.0, digits=(15, 2))
    af_net_a_payer = fields.Float(string='AF Net a Payer (DH)', default=0.0, digits=(15, 2))
    af_a_reverser = fields.Float(string='AF a Reverser (DH)', default=0.0, digits=(15, 2))
    is_entrant = fields.Boolean(string='Entrant', default=False)
