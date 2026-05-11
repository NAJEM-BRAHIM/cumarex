# -*- coding: utf-8 -*-
import base64
import logging
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DamancomImportPreetabliWizard(models.TransientModel):
    _name = 'damancom.import.preetabli.wizard'
    _description = "Importer un fichier preetabli AFFEBDS"

    preetabli_file = fields.Binary(
        string="Fichier preetabli (AFFEBDS_NNNNNNN_MMAAAA.txt)",
        required=True)
    preetabli_filename = fields.Char(string="Nom du fichier")
    declaration_id = fields.Many2one('damancom.declaration', string="Declaration cible")
    create_new_declaration = fields.Boolean(string="Creer une nouvelle declaration", default=True)
    auto_match_employees = fields.Boolean(string="Associer automatiquement les employes", default=True)
    auto_load_payslips = fields.Boolean(string="Charger les fiches de paie apres import", default=True)

    preview_num_affilie = fields.Char(string="N Affilie", readonly=True)
    preview_periode = fields.Char(string="Periode", readonly=True)
    preview_raison_sociale = fields.Char(string="Raison Sociale", readonly=True)
    preview_identif_transfert = fields.Char(string="Identif. Transfert", readonly=True)
    preview_nbr_assures = fields.Integer(string="Nb Assures", readonly=True)
    preview_total_af = fields.Float(string="Total AF Net a Payer (DH)", readonly=True)
    preview_date_emission = fields.Date(string="Date Emission", readonly=True)
    preview_date_exigibilite = fields.Date(string="Date Exigibilite", readonly=True)
    parsed_data = fields.Text(string="Donnees analysees", readonly=True)

    @api.onchange('preetabli_file')
    def _onchange_preview(self):
        if not self.preetabli_file:
            self.preview_num_affilie = False
            self.preview_periode = False
            self.preview_raison_sociale = False
            self.preview_identif_transfert = False
            self.preview_nbr_assures = 0
            self.preview_total_af = 0
            return
        try:
            data = self._parse_preetabli()
            self.preview_num_affilie = data['header']['num_affilie']
            self.preview_periode = data['header']['periode']
            self.preview_raison_sociale = data['header']['raison_sociale']
            self.preview_identif_transfert = data['identif_transfert']
            self.preview_nbr_assures = len(data['lines'])
            self.preview_total_af = sum(l['af_net_a_payer'] for l in data['lines'])
            if data['header'].get('date_emission'):
                self.preview_date_emission = data['header']['date_emission']
            if data['header'].get('date_exigibilite'):
                self.preview_date_exigibilite = data['header']['date_exigibilite']
        except Exception as e:
            _logger.warning("Erreur parsing preetabli: %s", e)
            self.parsed_data = f"Erreur de lecture: {str(e)}"

    def _parse_preetabli(self):
        if not self.preetabli_file:
            raise UserError(_("Aucun fichier selectionne."))
        try:
            content_bytes = base64.b64decode(self.preetabli_file)
        except Exception as e:
            raise UserError(_("Impossible de decoder le fichier: %s") % e)
        try:
            content = content_bytes.decode('ascii')
        except UnicodeDecodeError:
            content = content_bytes.decode('latin-1')
        lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        lines = [l for l in lines if l.strip()]
        if not lines:
            raise UserError(_("Le fichier est vide."))
        result = {'identif_transfert': '', 'header': {}, 'lines': [], 'footer': {}}
        for raw_line in lines:
            if len(raw_line) < 3:
                continue
            rec_type = raw_line[:3]
            try:
                if rec_type == 'A00':
                    result['identif_transfert'] = raw_line[3:17].strip()
                elif rec_type == 'A01':
                    pos = 3
                    num_affilie = raw_line[pos:pos+7].strip()
                    pos += 7
                    periode = raw_line[pos:pos+6].strip()
                    pos += 6
                    raison_sociale = raw_line[pos:pos+40].strip()
                    pos += 40
                    activite = raw_line[pos:pos+40].strip()
                    pos += 40
                    adresse = raw_line[pos:pos+120].strip()
                    pos += 120
                    ville = raw_line[pos:pos+20].strip()
                    pos += 20
                    code_postal = raw_line[pos:pos+6].strip()
                    pos += 6
                    code_agence = raw_line[pos:pos+2].strip()
                    pos += 2
                    date_emission_str = raw_line[pos:pos+8].strip()
                    pos += 8
                    date_exig_str = raw_line[pos:pos+8].strip()
                    result['header'] = {
                        'num_affilie': num_affilie, 'periode': periode,
                        'raison_sociale': raison_sociale, 'activite': activite,
                        'adresse': adresse, 'ville': ville,
                        'code_postal': code_postal, 'code_agence': code_agence,
                        'date_emission': self._parse_date(date_emission_str),
                        'date_exigibilite': self._parse_date(date_exig_str),
                    }
                elif rec_type == 'A02':
                    pos = 3
                    pos += 13
                    num_assure = raw_line[pos:pos+9].strip()
                    pos += 9
                    nom_prenom = raw_line[pos:pos+60].strip()
                    pos += 60
                    nb_enfants = self._to_int(raw_line[pos:pos+2])
                    pos += 2
                    af_a_payer = self._centimes_to_dh(raw_line[pos:pos+6])
                    pos += 6
                    af_a_deduire = self._centimes_to_dh(raw_line[pos:pos+6])
                    pos += 6
                    af_net_a_payer = self._centimes_to_dh(raw_line[pos:pos+6])
                    result['lines'].append({
                        'num_immatriculation': num_assure, 'nom_prenom': nom_prenom,
                        'nb_enfants': nb_enfants, 'af_a_payer': af_a_payer,
                        'af_a_deduire': af_a_deduire, 'af_net_a_payer': af_net_a_payer,
                    })
                elif rec_type == 'A03':
                    pos = 3
                    pos += 13
                    nbr_salaries = self._to_int(raw_line[pos:pos+6])
                    pos += 6
                    t_enfants = self._to_int(raw_line[pos:pos+6])
                    pos += 6
                    t_af_a_payer = self._centimes_to_dh(raw_line[pos:pos+12])
                    pos += 12
                    t_af_a_deduire = self._centimes_to_dh(raw_line[pos:pos+12])
                    pos += 12
                    t_af_net_a_payer = self._centimes_to_dh(raw_line[pos:pos+12])
                    result['footer'] = {
                        'nbr_salaries': nbr_salaries, 't_enfants': t_enfants,
                        't_af_a_payer': t_af_a_payer, 't_af_a_deduire': t_af_a_deduire,
                        't_af_net_a_payer': t_af_net_a_payer,
                    }
            except Exception as e:
                _logger.warning("Erreur parsing ligne type %s: %s", rec_type, e)
                continue
        if not result['header']:
            raise UserError(_("Fichier preetabli invalide: enregistrement A01 non trouve."))
        if not result['lines'] and not result['footer']:
            raise UserError(_("Fichier preetabli invalide: aucun assure trouve."))
        return result

    @staticmethod
    def _to_int(s):
        s = s.strip()
        if not s:
            return 0
        try:
            return int(s)
        except ValueError:
            return 0

    @staticmethod
    def _centimes_to_dh(s):
        centimes = DamancomImportPreetabliWizard._to_int(s)
        return centimes / 100.0

    @staticmethod
    def _parse_date(s):
        s = s.strip()
        if not s or s == '00000000' or len(s) != 8:
            return False
        try:
            return datetime.strptime(s, '%Y%m%d').date()
        except ValueError:
            return False

    def action_import(self):
        self.ensure_one()
        data = self._parse_preetabli()
        periode = data['header']['periode']
        if len(periode) != 6:
            raise UserError(_("Periode invalide dans le fichier: %s") % periode)
        year = int(periode[:4])
        month = int(periode[4:])
        num_affilie_file = data['header']['num_affilie']
        company = self.env.company
        if company.l10n_ma_cnss_num_affilie and company.l10n_ma_cnss_num_affilie != num_affilie_file:
            raise UserError(_("Le N d'affiliation du fichier (%s) ne correspond pas a celui configure.") % num_affilie_file)
        if self.create_new_declaration or not self.declaration_id:
            declaration_vals = {
                'company_id': company.id, 'period_year': year, 'period_month': month,
                'declaration_type': 'principale',
                'date_declaration': fields.Date.context_today(self),
                'date_exigibilite': data['header'].get('date_exigibilite'),
                'identif_transfert': data['identif_transfert'],
                'preetabli_imported': True,
            }
            declaration = self.env['damancom.declaration'].create(declaration_vals)
        else:
            declaration = self.declaration_id
            declaration.write({
                'identif_transfert': data['identif_transfert'],
                'preetabli_imported': True,
                'date_exigibilite': data['header'].get('date_exigibilite'),
            })
            declaration.line_ids.unlink()
        lines_data = []
        unmatched_employees = []
        for line_data in data['lines']:
            num_imma = line_data['num_immatriculation']
            employee = self.env['hr.employee'].search([
                ('l10n_ma_cnss_num_imma', '=', num_imma),
                ('company_id', '=', company.id),
            ], limit=1)
            if not employee and self.auto_match_employees:
                clean_name = line_data['nom_prenom'].strip()
                if clean_name:
                    employee = self.env['hr.employee'].search([
                        ('name', 'ilike', clean_name),
                        ('company_id', '=', company.id),
                    ], limit=1)
            line_vals = {
                'num_immatriculation': num_imma,
                'nom_prenom': line_data['nom_prenom'],
                'nb_enfants': line_data['nb_enfants'],
                'af_a_payer': line_data['af_a_payer'],
                'af_a_deduire': line_data['af_a_deduire'],
                'af_net_a_payer': line_data['af_net_a_payer'],
                'af_a_reverser': line_data['af_net_a_payer'],
                'jours_declares': 26,
                'salaire_reel': 0.0,
                'salaire_plafonne': 0.0,
                'situation': '',
                'is_entrant': False,
            }
            if employee:
                line_vals['employee_id'] = employee.id
                if not employee.l10n_ma_cnss_num_imma:
                    employee.l10n_ma_cnss_num_imma = num_imma
            else:
                unmatched_employees.append(line_data['nom_prenom'])
            lines_data.append((0, 0, line_vals))
        declaration.line_ids = lines_data
        if unmatched_employees:
            note = _("Employes non trouves dans Odoo (a creer ou a associer manuellement):\n")
            note += '\n'.join(f"- {name}" for name in unmatched_employees[:20])
            if len(unmatched_employees) > 20:
                note += f"\n... et {len(unmatched_employees) - 20} autres"
            declaration.notes = (declaration.notes or '') + '\n\n' + note
        if self.auto_load_payslips:
            try:
                self._merge_payslip_data(declaration)
            except Exception as e:
                _logger.warning("Impossible de charger les fiches de paie: %s", e)
                declaration.notes = (declaration.notes or '') + f'\n\nErreur chargement fiches de paie: {e}'
        return {
            'type': 'ir.actions.act_window', 'name': _('Declaration Damancom (Preetabli importe)'),
            'res_model': 'damancom.declaration', 'res_id': declaration.id,
            'view_mode': 'form', 'target': 'current',
        }

    def _merge_payslip_data(self, declaration):
        from datetime import date
        start_date = date(declaration.period_year, declaration.period_month, 1)
        if declaration.period_month == 12:
            end_date = date(declaration.period_year + 1, 1, 1)
        else:
            end_date = date(declaration.period_year, declaration.period_month + 1, 1)
        plafond = 6000.0
        for line in declaration.line_ids:
            if not line.employee_id:
                continue
            payslip = self.env['hr.payslip'].search([
                ('employee_id', '=', line.employee_id.id),
                ('company_id', '=', declaration.company_id.id),
                ('state', 'in', ['done', 'paid']),
                ('date_from', '>=', start_date),
                ('date_from', '<', end_date),
            ], limit=1)
            if not payslip:
                continue
            sbc_line = payslip.line_ids.filtered(lambda l: l.code == 'SBC')
            sbg_line = payslip.line_ids.filtered(lambda l: l.code == 'SBG')
            salaire_reel = sbc_line[:1].total if sbc_line else (
                sbg_line[:1].total if sbg_line else 0.0)
            salaire_plaf = min(salaire_reel, plafond)
            af_line = payslip.line_ids.filtered(lambda l: l.code == 'ALLOC_FAM')
            af_a_payer = af_line[:1].total if af_line else 0.0
            af_a_deduire = 0.0
            af_net_a_payer = af_a_payer - af_a_deduire
            af_a_reverser = af_net_a_payer
            situation = payslip.l10n_ma_cnss_situation or ''
            jours = payslip.l10n_ma_cnss_jours or 26
            if situation in ('CS', 'MS'):
                jours = 0
                salaire_reel = 0.0
                salaire_plaf = 0.0
                af_a_payer = 0.0
                af_net_a_payer = 0.0
                af_a_reverser = 0.0
            line.write({
                'payslip_id': payslip.id, 'jours_declares': jours,
                'salaire_reel': salaire_reel, 'salaire_plafonne': salaire_plaf,
                'situation': situation,
                'af_a_payer': af_a_payer, 'af_a_deduire': af_a_deduire,
                'af_net_a_payer': af_net_a_payer, 'af_a_reverser': af_a_reverser,
            })
