# Copyright 2011-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, _, api
from odoo.exceptions import UserError


class AccountConsolidationBase(models.AbstractModel):
    _name = 'account.consolidation.base'
    _description = 'Common consolidation wizard. Intended to be inherited'

    @api.model
    def _default_company(self):
        return self.env['res.company']._company_default_get()

    @api.model
    def _get_consolidation_profiles(self):
        return self._default_company().consolidation_profile_ids

    @api.model
    def default_get(self, fields):
        """Raise an error if user is not connected to consolidation company."""
        if not self.env.user.company_id.is_consolidation:
            raise UserError(_('Consolidation wizards can only be called from '
                              'a consolidation company.'))
        return super().default_get(fields)

    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self._default_company(),
        domain=[('is_consolidation', '=', True)],
        string='Company',
        required=True,
        readonly=True,
    )

    def check_subsidiary_mapping(self, conso_holding_accounts, subsidiary):
        """Check the mapping between accounts of subsidiary and the accounts
        of holding.

        All the active accounts of the subsidiary must be linked to an active
        account in the holding.
        :param conso_holding_accounts: Recordset of the holding company
                                       accounts
        :param subsidiary: Recordset of the subsidiary company to check

        :return: Dictionnary of accounts not correctly mapped to an holding
                 company account
        """
        subsidiary_accounts = self.env['account.account'].search([
            ('company_id', '=', subsidiary.id)])

        mapping_errors = {}

        for account in subsidiary_accounts:
            account_errors = []
            if not account.consolidation_account_id:
                account_errors.append(_(
                    'No consolidation account defined for this account'))
                mapping_errors.update({account: account_errors})
                continue

            conso_acc = account.consolidation_account_id

            if conso_acc not in conso_holding_accounts:
                if conso_acc.company_id != self.company_id:
                    account_errors.append(_(
                        'The consolidation account defined for this account '
                        'should be on company %s.') % self.company_id.name)

                mapping_errors.update({account: account_errors})

        return mapping_errors

    def check_account_mapping(self):
        """Check subsidiaries mapping against hodling's."""
        self.ensure_one()

        invalid_items_per_company = {}

        conso_holding_accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_id.id)])

        for subsidiary in self.company_id.consolidation_profile_ids.mapped(
                'sub_company_id'):

            invalid_items = self.check_subsidiary_mapping(
                conso_holding_accounts, subsidiary)

            if any(invalid_items):
                invalid_items_per_company[subsidiary] = invalid_items

        return invalid_items_per_company

    def check_interco_partner(self):
        """Check that subsidiaries' partners defined in profiles are not linked
        to a company.
        """
        self.ensure_one()

        invalid_partners = {}

        conso_profiles = self.company_id.consolidation_profile_ids
        for subsidiary in conso_profiles.mapped('sub_company_id'):
            partner = subsidiary.partner_id
            if partner.company_id:
                invalid_partners[partner] = partner.company_id

        return invalid_partners

    def check_companies_allowed(self):
        """Check that the user has access to subsidiaries defined in profiles.
        """
        self.ensure_one()

        subsidiaries = self.company_id.consolidation_profile_ids.mapped(
            'sub_company_id')

        return subsidiaries - self.env.user.company_ids

    @api.multi
    def run_consolidation(self):
        """Consolidate.

        Proceed with all checks before launch any consolidation step.
        This is a base method intended to be inherited with the next
        consolidation steps.
        """
        self.ensure_one()

        if (
                self.check_account_mapping() or
                self.check_interco_partner() or
                self.check_companies_allowed()
        ):
            raise UserError(
                _('Invalid configuration, please launch the '
                  '"Consolidation: Checks" wizard'))

        return {'type': 'ir.actions.act_window_close'}
