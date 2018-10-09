# Copyright 2011-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class AccountAccount(models.Model):

    _name = 'account.account'
    _inherit = ['account.account', 'account.consolidation.reference.mixin']

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
            result = super(AccountAccount, self).name_get()
        return result
