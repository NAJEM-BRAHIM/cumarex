# -*- coding: utf-8 -*-
"""
Modèle principal de la Déclaration Damancom CNSS.

Génère le fichier BDS conforme au Cahier des Charges CNSS Version 2 / Février 2006.
"""
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
    _description = 'Déclaration CNSS Damancom'
    _order = 'date_declaration desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Référence',
        compute='_compute_name',
        store=True,
    )
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
    period_month = fields.Integer(
        string='Mois',
        required=True,
        default=lambda self: fields.Date.today().month,
    )
    period_str = fields.Char(
        string='Période',
        compute='_compute_period_str',
        store=True,
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
        help="Numéro de séquence pour les TD complémentaires (1 à 9).",
    )
    date_declaration = fields.Date(
        string='Date Déclaration',
        default=fields.Date.context_today,
        required=True,
    )
    date_exigibilite = fields.Date(
        string="Date Exigibilité",
        help="Date limite de retour des BDS et de paiement des cotisations.",
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('generated', 'Généré'),
            ('submitted', 'Soumis à Damancom'),
            ('validated', 'Validé par CNSS'),
            ('rejected', 'Rejeté'),
        ],
        string='État',
        default='draft',
        required=True,
        tracking=True,
    )
    payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Fiches de paie',
        domain="[('state', 'in', ['done', 'paid']), "
               "('company_id', '=', company_id)]",
    )
    line_ids = fields.One2many(
        'damancom.declaration.line',
        'declaration_id',
        string='Lignes de déclaration',
    )

    # Totaux calculés
    total_salaries = fields.Integer(
        string='Nombre Salariés',
        compute='_compute_totals',
        store=True,
    )
    total_jours = fields.Integer(
        string='Total Jours',
        compute='_compute_totals',
        store=True,
    )
    total_salaire_reel = fields.Float(
        string='Total Salaire Réel (DH)',
        compute='_compute_totals',
        store=True,
        digits=(15, 2),
    )
    total_salaire_plaf = fields.Float(
        string='Total Salaire Plafonné (DH)',
        compute='_compute_totals',
        store=True,
        digits=(15, 2),
    )

    # Fichier généré
    bds_file = fields.Binary(
        string='Fichier BDS',
        attachment=True,
        readonly=True,
    )
    bds_filename = fields.Char(
        string='Nom du fichier BDS',
        readonly=True,
    )
    bds_generated_date = fields.Datetime(
        string='Date Génération',
        readonly=True,
    )

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
            type_str = 'Principale' if rec.declaration_type == 'principale' else f'Complémentaire #{rec.sequence_number}'
            company_str = rec.company_id.name or ''
            rec.name = f"BDS {rec.period_str} - {company_str} ({type_str})"

    @api.depends('line_ids', 'line_ids.jours_declares',
                 'line_ids.salaire_reel', 'line_ids.salaire_plafonne')
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
                raise ValidationError(_("Le mois doit être entre 1 et 12."))

    @api.constrains('sequence_number')
    def _check_sequence_number(self):
        for rec in self:
            if rec.declaration_type == 'complementaire' and (
                    rec.sequence_number < 1 or rec.sequence_number > 9):
                raise ValidationError(_("Le numéro de séquence doit être entre 1 et 9."))

    def action_load_payslips(self):
        """
        Charge automatiquement les fiches de paie du mois sélectionné
        et crée les lignes de déclaration correspondantes.
        """
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Seules les déclarations en brouillon peuvent charger les fiches de paie."))

        # Effacer les lignes existantes
        self.line_ids.unlink()

        # Filtrer les payslips de la période
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
            raise UserError(_(
                "Aucune fiche de paie validée trouvée pour la période %s/%s."
            ) % (self.period_month, self.period_year))

        self.payslip_ids = [(6, 0, payslips.ids)]

        # Créer les lignes
        lines_data = []
        plafond = PLAFOND_CNSS_DEFAULT
        for payslip in payslips:
            employee = payslip.employee_id
            
            # N° immatriculation
            if employee.l10n_ma_cnss_occasionnel:
                num_imma = '999999999'
            elif employee.l10n_ma_cnss_num_imma:
                num_imma = employee.l10n_ma_cnss_num_imma
            else:
                num_imma = '000000000'

            # Salaire réel = SBC (salaire brut cotisable, déplafonné)
            sbc_line = payslip.line_ids.filtered(lambda l: l.code == 'SBC')
            sbg_line = payslip.line_ids.filtered(lambda l: l.code == 'SBG')
            salaire_reel = sbc_line[:1].total if sbc_line else (
                sbg_line[:1].total if sbg_line else 0.0
            )

            # Salaire plafonné = min(SBC, plafond CNSS)
            salaire_plaf = min(salaire_reel, plafond)

            # Situation
            situation = payslip.l10n_ma_cnss_situation or ''

            # Jours
            jours = payslip.l10n_ma_cnss_jours or 26

            # Pour situations spéciales : ajuster
            if situation in ('CS', 'MS'):
                jours = 0
                salaire_reel = 0.0
                salaire_plaf = 0.0

            lines_data.append((0, 0, {
                'employee_id': employee.id,
                'payslip_id': payslip.id,
                'num_immatriculation': num_imma,
                'nom_prenom': employee.name,
                'num_cin': employee.identification_id or '',
                'jours_declares': jours,
                'salaire_reel': salaire_reel,
                'salaire_plafonne': salaire_plaf,
                'situation': situation,
                'nb_enfants': employee.children if hasattr(employee, 'children') else 0,
                'is_entrant': self._is_entrant(employee, payslip),
            }))

        self.line_ids = lines_data
        return True

    def _is_entrant(self, employee, payslip):
        """
        Détermine si un employé est un 'entrant' (nouveau dans cette période).
        Un entrant est un employé qui n'a pas de fiche de paie validée 
        dans les mois précédents pour cette société.
        """
        prev_payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', employee.id),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '<', payslip.date_from),
        ], limit=1)
        return not prev_payslips

    def action_validate(self):
        """Valide la déclaration et exécute les contrôles."""
        self.ensure_one()
        errors = []

        # Contrôle entreprise
        if not self.company_id.l10n_ma_cnss_num_affilie:
            errors.append(_("N° d'affiliation CNSS non configuré pour la société."))
        else:
            valid, msg = validate_num_affilie(self.company_id.l10n_ma_cnss_num_affilie)
            if not valid:
                errors.append(_("N° d'affiliation CNSS invalide: %s") % msg)

        if not self.line_ids:
            errors.append(_("Aucune ligne dans la déclaration. Chargez les fiches de paie d'abord."))

        # Contrôle lignes
        for line in self.line_ids:
            if not line.is_entrant:
                # Pour les existants: vérifier numéro immatriculation
                if line.num_immatriculation in ('000000000', ''):
                    errors.append(_(
                        "Employé %s: N° d'immatriculation CNSS manquant. "
                        "Configurez-le dans la fiche employé."
                    ) % line.employee_id.name)
                else:
                    valid, msg = validate_num_immatriculation(line.num_immatriculation)
                    if not valid:
                        errors.append(_(
                            "Employé %s: N° immatriculation invalide (%s) - %s"
                        ) % (line.employee_id.name, line.num_immatriculation, msg))

            # Contrôles spécifiques aux situations
            if line.jours_declares > 26:
                errors.append(_(
                    "Employé %s: jours déclarés (%d) > 26"
                ) % (line.employee_id.name, line.jours_declares))

            if line.situation in ('CS', 'MS') and (
                    line.jours_declares > 0 or line.salaire_reel > 0):
                errors.append(_(
                    "Employé %s: situation %s exige jours=0 et salaire=0"
                ) % (line.employee_id.name, line.situation))

            if line.salaire_plafonne > line.salaire_reel:
                errors.append(_(
                    "Employé %s: salaire plafonné (%s) > salaire réel (%s)"
                ) % (line.employee_id.name, line.salaire_plafonne, line.salaire_reel))

        if errors:
            raise ValidationError('\n'.join([_("Erreurs de validation:")] + errors))

        return True

    def action_generate_bds(self):
        """Génère le fichier BDS au format CNSS."""
        self.ensure_one()
        self.action_validate()

        if self.declaration_type == 'principale':
            content = self._generate_bds_principale()
        else:
            content = self._generate_bds_complementaire()

        # Nom du fichier conforme: DS_NNNNNNN_MMAAAA.txt
        # ou DSCN_NNNNNNN_MMAAAA.txt pour complémentaire
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        period_mmaaaa = f"{self.period_month:02d}{self.period_year:04d}"

        if self.declaration_type == 'principale':
            filename = f"DS_{num_aff}_{period_mmaaaa}.txt"
        else:
            filename = f"DSC{self.sequence_number}_{num_aff}_{period_mmaaaa}.txt"

        self.write({
            'bds_file': base64.b64encode(content.encode('ascii', errors='replace')),
            'bds_filename': filename,
            'bds_generated_date': fields.Datetime.now(),
            'state': 'generated',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=damancom.declaration&id={self.id}'
                   f'&field=bds_file&filename_field=bds_filename&download=true',
            'target': 'self',
        }

    def _build_record_b00(self):
        """Enregistrement type 1: Nature du fichier (B00)."""
        # L_Type_Enreg (3) + N_Identif_Transfert (14) + L_Cat (2) + filler (241) = 260
        # Identif_Transfert : généré par CNSS dans le préétabli
        # En l'absence de préétabli, on utilise 0
        identif_transfert = format_n(0, 14)
        content = (
            'B00' +
            identif_transfert +
            'B0' +
            ' ' * 241
        )
        return pad_record(content)

    def _build_record_b01(self):
        """Enregistrement type 2: Entête Globale (B01)."""
        company = self.company_id
        # B01 + Num_Affilie(7) + Période(6) + Raison(40) + Activité(40) + Adresse(120)
        # + Ville(20) + Code_Postal(6) + Code_Agence(2) + Date_Emission(8) + Date_Exig(8)
        content = (
            'B01' +
            format_n(company.l10n_ma_cnss_num_affilie, 7) +
            self.period_str +  # AAAAMM
            format_an(company.name or '', 40) +
            format_an(company.l10n_ma_cnss_activite or '', 40) +
            format_an(company.street or '', 120) +
            format_an(company.city or '', 20) +
            format_an(company.l10n_ma_cnss_code_postal or company.zip or '', 6) +
            format_n(company.l10n_ma_cnss_code_agence or 0, 2) +
            format_date(self.date_declaration) +
            format_date(self.date_exigibilite or self.date_declaration)
        )
        return pad_record(content)

    def _build_record_b02(self, line):
        """Enregistrement type 3: Détail déclaration sur préétabli (B02) - 1 par employé existant."""
        num_assure = line.num_immatriculation
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        situation_pad = format_an(line.situation or '', 2)
        
        # Calcul S_Ctr (somme horizontale)
        # S_Ctr = N_Num_Assure + N_AF_A_Reverser + N_Jours_Declares 
        #       + N_Salaire_Reel + N_Salaire_Plaf + Rang(Situation)
        rang = SITUATION_RANGS.get(line.situation or '', 0)
        ctr = (int(num_assure) +
               int(round(line.af_a_reverser * 100)) +
               line.jours_declares +
               int(round(line.salaire_reel * 100)) +
               int(round(line.salaire_plafonne * 100)) +
               rang)

        content = (
            'B02' +
            format_n(num_aff, 7) +
            self.period_str +
            format_n(num_assure, 9) +
            format_an(line.nom_prenom, 60) +
            format_n(line.nb_enfants, 2) +
            format_centimes(line.af_a_payer, 6) +
            format_centimes(line.af_a_deduire, 6) +
            format_centimes(line.af_net_a_payer, 6) +
            format_centimes(line.af_a_reverser, 6) +
            format_n(line.jours_declares, 2) +
            format_centimes(line.salaire_reel, 13) +
            format_centimes(line.salaire_plafonne, 9) +
            situation_pad +
            format_n(ctr, 19) +
            ' ' * 104
        )
        return pad_record(content)

    def _build_record_b03(self, existants_lines):
        """Enregistrement type 4: Récap déclaration sur préétabli (B03)."""
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        nbr_salaries = len(existants_lines)
        t_enfants = sum(l.nb_enfants for l in existants_lines)
        t_af_a_payer = sum(l.af_a_payer for l in existants_lines)
        t_af_a_deduire = sum(l.af_a_deduire for l in existants_lines)
        t_af_net = sum(l.af_net_a_payer for l in existants_lines)
        t_af_reverser = sum(l.af_a_reverser for l in existants_lines)
        t_num_imma = sum(int(l.num_immatriculation) for l in existants_lines)
        t_jours = sum(l.jours_declares for l in existants_lines)
        t_sal_reel = sum(l.salaire_reel for l in existants_lines)
        t_sal_plaf = sum(l.salaire_plafonne for l in existants_lines)
        t_ctr = sum(self._compute_line_ctr(l) for l in existants_lines)

        content = (
            'B03' +
            format_n(num_aff, 7) +
            self.period_str +
            format_n(nbr_salaries, 6) +
            format_n(t_enfants, 6) +
            format_centimes(t_af_a_payer, 12) +
            format_centimes(t_af_a_deduire, 12) +
            format_centimes(t_af_net, 12) +
            format_n(t_num_imma, 15) +
            format_centimes(t_af_reverser, 12) +
            format_n(t_jours, 6) +
            format_centimes(t_sal_reel, 15) +
            format_centimes(t_sal_plaf, 13) +
            format_n(t_ctr, 19) +
            ' ' * 116
        )
        return pad_record(content)

    def _build_record_b04(self, line):
        """Enregistrement type 5: Détail déclaration entrants (B04)."""
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        num_assure = line.num_immatriculation
        
        # S_Ctr = N_Num_Assure + N_Jours_Declares + N_Salaire_Reel + N_Salaire_Plaf
        # Note: si num_assure = 9 espaces, alors part = 0
        if num_assure.strip().isdigit():
            num_for_ctr = int(num_assure)
        else:
            num_for_ctr = 0
        
        ctr = (num_for_ctr +
               line.jours_declares +
               int(round(line.salaire_reel * 100)) +
               int(round(line.salaire_plafonne * 100)))

        # Num_CIN obligatoire si num_assure = 000000000
        num_cin = line.num_cin or ''

        content = (
            'B04' +
            format_n(num_aff, 7) +
            self.period_str +
            format_n(num_assure, 9) +
            format_an(line.nom_prenom, 60) +
            format_an(num_cin, 8) +
            format_n(line.jours_declares, 2) +
            format_centimes(line.salaire_reel, 13) +
            format_centimes(line.salaire_plafonne, 9) +
            format_n(ctr, 19) +
            ' ' * 124
        )
        return pad_record(content)

    def _build_record_b04_empty(self):
        """B04 vide (si aucun entrant) : N_Num_Assure = 9 espaces, autres = 0."""
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        content = (
            'B04' +
            format_n(num_aff, 7) +
            self.period_str +
            ' ' * 9 +           # 9 espaces vides
            ' ' * 60 +          # nom_prenom = espaces (AN)
            ' ' * 8 +           # CIN = espaces
            format_n(0, 2) +    # jours = 0
            format_n(0, 13) +   # sal_reel = 0
            format_n(0, 9) +    # sal_plaf = 0
            format_n(0, 19) +   # S_Ctr = 0
            ' ' * 124
        )
        return pad_record(content)

    def _build_record_b05(self, entrants_lines):
        """Enregistrement type 6: Récap entrants (B05)."""
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        
        # Si pas d'entrants, tous les totaux à 0
        if not entrants_lines:
            nbr_salaries = 0
            t_num_imma = 0
            t_jours = 0
            t_sal_reel = 0.0
            t_sal_plaf = 0.0
            t_ctr = 0
        else:
            nbr_salaries = len(entrants_lines)
            t_num_imma = sum(
                int(l.num_immatriculation) if l.num_immatriculation.strip().isdigit() else 0
                for l in entrants_lines
            )
            t_jours = sum(l.jours_declares for l in entrants_lines)
            t_sal_reel = sum(l.salaire_reel for l in entrants_lines)
            t_sal_plaf = sum(l.salaire_plafonne for l in entrants_lines)
            t_ctr = sum(self._compute_line_ctr(l, is_entrant=True) for l in entrants_lines)

        content = (
            'B05' +
            format_n(num_aff, 7) +
            self.period_str +
            format_n(nbr_salaries, 6) +
            format_n(t_num_imma, 15) +
            format_n(t_jours, 6) +
            format_centimes(t_sal_reel, 15) +
            format_centimes(t_sal_plaf, 13) +
            format_n(t_ctr, 19) +
            ' ' * 170
        )
        return pad_record(content)

    def _build_record_b06(self, existants_lines, entrants_lines):
        """Enregistrement type 7: Récap Globale (B06)."""
        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        all_lines = list(existants_lines) + list(entrants_lines)

        nbr_salaries = len(all_lines)
        t_num_imma = sum(
            int(l.num_immatriculation) if l.num_immatriculation.strip().isdigit() else 0
            for l in all_lines
        )
        t_jours = sum(l.jours_declares for l in all_lines)
        t_sal_reel = sum(l.salaire_reel for l in all_lines)
        t_sal_plaf = sum(l.salaire_plafonne for l in all_lines)
        
        # T_Ctr = T_Ctr_existants + T_Ctr_entrants
        t_ctr_exist = sum(self._compute_line_ctr(l) for l in existants_lines)
        t_ctr_entr = sum(self._compute_line_ctr(l, is_entrant=True) for l in entrants_lines)
        t_ctr = t_ctr_exist + t_ctr_entr

        content = (
            'B06' +
            format_n(num_aff, 7) +
            self.period_str +
            format_n(nbr_salaries, 6) +
            format_n(t_num_imma, 15) +
            format_n(t_jours, 6) +
            format_centimes(t_sal_reel, 15) +
            format_centimes(t_sal_plaf, 13) +
            format_n(t_ctr, 19) +
            ' ' * 170
        )
        return pad_record(content)

    def _compute_line_ctr(self, line, is_entrant=False):
        """Calcule le S_Ctr d'une ligne."""
        if is_entrant:
            num = (int(line.num_immatriculation)
                   if line.num_immatriculation.strip().isdigit() else 0)
            return (num +
                    line.jours_declares +
                    int(round(line.salaire_reel * 100)) +
                    int(round(line.salaire_plafonne * 100)))
        else:
            rang = SITUATION_RANGS.get(line.situation or '', 0)
            return (int(line.num_immatriculation) +
                    int(round(line.af_a_reverser * 100)) +
                    line.jours_declares +
                    int(round(line.salaire_reel * 100)) +
                    int(round(line.salaire_plafonne * 100)) +
                    rang)

    def _generate_bds_principale(self):
        """Génère le contenu complet du fichier BDS principal."""
        existants_lines = self.line_ids.filtered(lambda l: not l.is_entrant)
        entrants_lines = self.line_ids.filtered(lambda l: l.is_entrant)

        # Tri par num_assure croissant
        existants_lines = existants_lines.sorted(lambda l: l.num_immatriculation)
        entrants_lines = entrants_lines.sorted(lambda l: l.num_immatriculation)

        lines = []
        # 1 - B00
        lines.append(self._build_record_b00())
        # 1 - B01
        lines.append(self._build_record_b01())
        # N - B02 (existants)
        for line in existants_lines:
            lines.append(self._build_record_b02(line))
        # 1 - B03
        lines.append(self._build_record_b03(existants_lines))
        # N - B04 (entrants) ou 1 B04 vide
        if entrants_lines:
            for line in entrants_lines:
                lines.append(self._build_record_b04(line))
        else:
            lines.append(self._build_record_b04_empty())
        # 1 - B05
        lines.append(self._build_record_b05(entrants_lines))
        # 1 - B06
        lines.append(self._build_record_b06(existants_lines, entrants_lines))

        # Séparateur : retour à la ligne ASCII 10 (LF)
        return '\n'.join(lines) + '\n'

    def _generate_bds_complementaire(self):
        """
        Génère un fichier BDS complémentaire.
        Selon le cahier des charges section IV-5:
        - Seuls les entrants sont déclarés
        - B02 et B03 contiennent une seule ligne avec champs à 0/vides
        - Codes : E00, E01, E02, E03, E04, E05, E06
        """
        entrants_lines = self.line_ids.filtered(lambda l: l.is_entrant)
        if not entrants_lines:
            raise UserError(_(
                "Une déclaration complémentaire doit contenir au moins un entrant."
            ))
        entrants_lines = entrants_lines.sorted(lambda l: l.num_immatriculation)

        num_aff = self.company_id.l10n_ma_cnss_num_affilie
        lines = []

        # E00 - Nature du fichier (séquence : E[N])
        e00 = ('E00' +
               format_n(0, 14) +
               f'E{self.sequence_number}' +
               ' ' * 241)
        lines.append(pad_record(e00))

        # E01 - Entête globale
        e01_content = self._build_record_b01().replace('B01', 'E01', 1)
        lines.append(e01_content)

        # E02 - 1 ligne vide
        e02 = ('E02' +
               format_n(num_aff, 7) +
               self.period_str +
               ' ' * 9 +     # num_assure = espaces
               ' ' * 60 +    # nom_prenom = espaces
               format_n(0, 2) +    # enfants = 0
               format_n(0, 6) +    # AF_A_Payer = 0
               format_n(0, 6) +    # AF_A_Deduire = 0
               format_n(0, 6) +    # AF_Net_A_Payer = 0
               format_n(0, 6) +    # AF_A_Reverser = 0
               format_n(0, 2) +    # Jours_Declares = 0
               format_n(0, 13) +   # Salaire_Reel = 0
               format_n(0, 9) +    # Salaire_Plaf = 0
               ' ' * 2 +     # Situation = espaces
               format_n(0, 19) +   # S_Ctr = 0
               ' ' * 104)
        lines.append(pad_record(e02))

        # E03 - récap vide
        e03 = ('E03' +
               format_n(num_aff, 7) +
               self.period_str +
               format_n(0, 6) * 3 +
               format_n(0, 12) * 3 +
               format_n(0, 15) +
               format_n(0, 12) +
               format_n(0, 6) +
               format_n(0, 15) +
               format_n(0, 13) +
               format_n(0, 19) +
               ' ' * 116)
        lines.append(pad_record(e03))

        # E04 - entrants
        for line in entrants_lines:
            e04_content = self._build_record_b04(line).replace('B04', 'E04', 1)
            lines.append(e04_content)

        # E05 - récap entrants
        e05_content = self._build_record_b05(entrants_lines).replace('B05', 'E05', 1)
        lines.append(e05_content)

        # E06 - récap globale = même que E05 ici (pas d'existants)
        e06_content = self._build_record_b06(self.env['damancom.declaration.line'],
                                              entrants_lines).replace('B06', 'E06', 1)
        lines.append(e06_content)

        return '\n'.join(lines) + '\n'

    def action_download_bds(self):
        """Télécharge le fichier BDS généré."""
        self.ensure_one()
        if not self.bds_file:
            raise UserError(_("Le fichier BDS n'a pas encore été généré."))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=damancom.declaration&id={self.id}'
                   f'&field=bds_file&filename_field=bds_filename&download=true',
            'target': 'self',
        }

    def action_mark_submitted(self):
        """Marque la déclaration comme soumise à Damancom."""
        self.write({'state': 'submitted'})

    def action_mark_validated(self):
        """Marque la déclaration comme validée par la CNSS."""
        self.write({'state': 'validated'})

    def action_mark_rejected(self):
        """Marque la déclaration comme rejetée."""
        self.write({'state': 'rejected'})

    def action_reset_draft(self):
        """Réinitialise la déclaration en brouillon."""
        self.write({
            'state': 'draft',
            'bds_file': False,
            'bds_filename': False,
            'bds_generated_date': False,
        })


class DamancomDeclarationLine(models.Model):
    _name = 'damancom.declaration.line'
    _description = 'Ligne de Déclaration Damancom'
    _order = 'is_entrant, num_immatriculation'

    declaration_id = fields.Many2one(
        'damancom.declaration',
        string='Déclaration',
        required=True,
        ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=True,
    )
    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Fiche de paie',
    )
    num_immatriculation = fields.Char(
        string='N° Immatriculation',
        size=9,
        required=True,
    )
    nom_prenom = fields.Char(
        string='Nom et Prénom',
        required=True,
    )
    num_cin = fields.Char(
        string='N° CIN',
        size=8,
        help="Obligatoire pour les entrants sans numéro d'immatriculation.",
    )
    nb_enfants = fields.Integer(
        string='Nb Enfants AF',
        default=0,
    )
    jours_declares = fields.Integer(
        string='Jours Déclarés',
        default=26,
    )
    salaire_reel = fields.Float(
        string='Salaire Réel (DH)',
        digits=(15, 2),
    )
    salaire_plafonne = fields.Float(
        string='Salaire Plafonné (DH)',
        digits=(15, 2),
    )
    situation = fields.Selection(
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
        string='Situation',
        default='',
    )
    af_a_payer = fields.Float(
        string='AF à Payer (DH)',
        default=0.0,
        digits=(15, 2),
        help="Montant des allocations familiales dues au titre du mois.",
    )
    af_a_deduire = fields.Float(
        string='AF à Déduire (DH)',
        default=0.0,
        digits=(15, 2),
    )
    af_net_a_payer = fields.Float(
        string='AF Net à Payer (DH)',
        default=0.0,
        digits=(15, 2),
    )
    af_a_reverser = fields.Float(
        string='AF à Reverser (DH)',
        default=0.0,
        digits=(15, 2),
    )
    is_entrant = fields.Boolean(
        string='Entrant',
        default=False,
        help="Si coché, ce salarié est nouveau dans la période "
             "(déclaré dans le bloc B04 des entrants).",
    )
