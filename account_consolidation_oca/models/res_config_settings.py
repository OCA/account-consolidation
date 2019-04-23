# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    consolidation_diff_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Consolidation difference account',
        related='company_id.consolidation_diff_account_id',
        help='Conso. differences will be affected to this account',
        readonly=False,
    )
    consolidation_default_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Default consolidation journal',
        related='company_id.consolidation_default_journal_id',
        help='Default journal to generate consolidation entries',
        readonly=False,
    )
    is_consolidation = fields.Boolean(
        string='Consolidation company',
        related='company_id.is_consolidation',
        help='Check this box if you want to consolidate in this company.',
        readonly=False,
    )
    consolidation_profile_ids = fields.One2many(
        comodel_name='company.consolidation.profile',
        related='company_id.consolidation_profile_ids',
        string='Consolidation profiles',
        readonly=False,
    )
