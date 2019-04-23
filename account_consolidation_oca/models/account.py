# Copyright 2011-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class AccountAccount(models.Model):

    _inherit = 'account.account'

    def _compute_conso_company(self):
        """Computes the consolidation company of the account's company."""
        for acc in self:
            profile = self.env['company.consolidation.profile'].search(
                [('sub_company_id', '=', acc.company_id.id)])
            if profile:
                acc.consolidation_company_id = profile.company_id

    consolidation_company_id = fields.Many2one(
        comodel_name='res.company',
        compute=lambda self: self._compute_conso_company()
    )
    consolidation_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Consolidation account',
        domain="[('company_id', '=', consolidation_company_id)]",
        help='Consolidation moves will be generated on this account'
    )

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        """Display the account company if the user is connected to it.."""
        if self.env.user.has_group(
                'account_consolidation.group_consolidation_manager'):
            result = []
            for account in self:
                if account.company_id != self.env.user.company_id:
                    name = '%s %s (%s)' % (account.code, account.name,
                                           account.company_id.name)
                else:
                    name = account.code + ' ' + account.name
                result.append((account.id, name))
        else:
            result = super().name_get()
        return result
