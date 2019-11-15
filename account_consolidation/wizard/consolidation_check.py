# Copyright 2011-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, _


class AccountConsolidationCheck(models.TransientModel):
    _name = 'account.consolidation.check'
    _inherit = 'account.consolidation.base'
    _description = 'Consolidation Checks. Model used for views'

    message = fields.Html(readonly=True)
    state = fields.Selection(
        [('open', 'Open'),
         ('error', 'Error'),
         ('ok', 'Checks ok')],
        default='open'
    )

    def check_account_mapping(self):
        """Convert errors message to a HTML list of errors."""
        invalid_items_per_company = super().check_account_mapping()

        err_lines = []
        for company, account_errors in invalid_items_per_company.items():
            err_lines.append("<div><ul><li>%s :</li><ul>" % company.name)
            for account, error in account_errors.items():
                err_lines.append("<li>%s (%s) : %s</li>" % (
                    account.code, account.name, ', '.join(error)))
            err_lines.append('</ul></ul></div>')

        return err_lines

    def check_interco_partner(self):
        """Convert errors message to a HTML list of errors."""
        invalid_partners = super().check_interco_partner()
        err_lines = []
        if invalid_partners:
            err_lines.append('<div><ul>')
            for partner, company in invalid_partners.items():
                err_lines.append('<li>%s : %s</li>' % (partner.name,
                                                       company.name))
            err_lines.append('</ul></div>')
        return err_lines

    def check_companies_allowed(self):
        """Convert errors message to a HTML list of errors."""
        unallowed_companies = super().check_companies_allowed()
        err_lines = []
        if unallowed_companies:
            err_lines.append('<div><ul>')
            for comp in unallowed_companies:
                err_lines.append(
                    '<li>%s : User has no access to this company.</li>' % (
                        comp.name)
                )
            err_lines.append('</ul></div>')
        return err_lines

    def check_configuration(self):
        """Action launched with the button on the view.

        Calls the checks and display the result as HTML
        """
        mapping_errors = self.check_account_mapping()
        partner_errors = self.check_interco_partner()
        company_allowed_errors = self.check_companies_allowed()
        messages = []
        if mapping_errors:
            messages.append(_('<h3>Invalid account mapping</h3>') + ''.join(
                mapping_errors))
        if partner_errors:
            messages.append(_(
                '<h3>Company defined on intercompany partners</h3>') + ''.join(
                partner_errors))
        if company_allowed_errors:
            messages.append(_(
                '<h3>Company access not allowed</h3>') + ''.join(
                company_allowed_errors))

        if messages:
            self.message = _(
                '<h2>Consolidation configuration errors</h2>') + ''.join(
                messages)
            self.state = 'error'
        else:
            self.message = _(
                '<h2>No configuration error detected ! '
                'You can now proceed with the consolidation.</h2>')
            self.state = 'ok'
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'res_model': self._name,
            'target': 'new',
        }
