# Copyright 2011-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):

    _inherit = 'res.company'

    consolidation_diff_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Consolidation difference account',
        help="Conso. differences will be affected to this account"
    )
    consolidation_default_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Default consolidation journal',
        help="Default journal to generate consolidation entries"
    )
    consolidation_profile_ids = fields.One2many(
        comodel_name='company.consolidation.profile',
        inverse_name='company_id'
    )
    # This field is used only on subsidiaries and is the only way to get to the
    # profile from a record part of a subsidiary
    # It's the inverse field of sub_company_id on company.consolidation.profile
    sub_consolidation_profile_id = fields.Many2one(
        comodel_name='company.consolidation.profile',
        readonly=True,
    )
    consolidation_percentage = fields.Float(
        related='sub_consolidation_profile_id.consolidation_percentage',
        readonly=True,
    )
    is_consolidation = fields.Boolean(string='Consolidation company')

    @api.constrains('is_consolidation')
    def _check_single_conso_company(self):
        """Ensure there is only one company defined as consolidation."""
        if self.search_count([('is_consolidation', '=', True)]) > 1:
            raise ValidationError(_(
                'Only one company can be defined as consolidation company.'))
