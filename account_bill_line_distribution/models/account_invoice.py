# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        if self.invoice_line_ids
        # Due From
        account_move = self.env['account.move']
        df_vals = {
            'name': self.reference,
            'journal_id': self.company_id.due_fromto_payment_journal_id.id,
            'state': 'draft',
            'company_id': self.company_id.id,
            'ref': self.id,
            'line_ids': False
        }
        lines = []
        companies = []
        # Lines
        for invoice_line_id in self.invoice_line_ids:
            for distribution_id in invoice_line_id.distribution_ids:
                # Get total # of companies involved
                if distribution_id.company_id not in companies:
                    companies.append(distribution_id.company_id)
                # Credit our companies distribution
                if distribution_id.company_id == self.company_id:
                    lines.append((0, 0, {
                        'name': invoice_line_id.name,
                        'credit': invoice_line_id.\
                        price_subtotal * distribution_id.percent / 100,
                        'account_id': invoice_line_id.product_id.\
                        property_account_expense_id.id, }))
                # Debit other companies distributions
                else:
                    # If we already have a line for this compnay
                    # just append debit amount
                    found = False
                    for line in lines:
                        if line[2]['account_id'] == \
                                distribution_id.\
                                company_id.due_from_account_id.id:
                            line[2]['debit'] += invoice_line_id.\
                                price_subtotal * distribution_id.percent / 100
                            found = True
                    # If not, make new line
                    if not found:
                        lines.append((0, 0, {
                            'name': invoice_line_id.name,
                            'debit': invoice_line_id.\
                            price_subtotal * distribution_id.percent / 100,
                            'account_id': distribution_id.\
                            company_id.due_from_account_id.id,
                            'partner_id': distribution_id.\
                            company_id.partner_id.id}))
        
        # Create Journal Entry
        if lines:
            df_vals['line_ids'] = lines
            account_move.sudo().create(df_vals)

        # Due To's
        for company_id in companies:
            lines = []
            # Skip our compnay because that has been taken care of already
            if company_id.id != self.company_id.id:
                dt_vals = {
                    'name': self.reference,
                    'journal_id': company_id.due_fromto_payment_journal_id.id,
                    'state': 'draft',
                    'company_id': company_id.id,
                }
                # Credit company "Due_To" Account with debit 
                # amount from its previous "Due from" Account entry
                for line_id in df_vals['line_ids']:
                    if line_id[2]['account_id'] == \
                            company_id.due_from_account_id.id:
                        lines.append((0, 0, {
                        'name': invoice_line_id.name,
                        'credit': line_id[2]['debit'],
                        'account_id': self.company_id.due_to_account_id.id,
                        'partner_id': self.company_id.partner_id.id}))

                # Debit Product Expense Accounts
                for invoice_line_id in self.invoice_line_ids:
                    for distribution_id in invoice_line_id.distribution_ids:
                        if distribution_id.company_id == company_id:
                            lines.append((0, 0, {
                                'name': invoice_line_id.name,
                                'debit': invoice_line_id.\
                                price_subtotal * distribution_id.percent / 100,
                                'account_id': invoice_line_id.product_id.\
                                property_account_expense_id.id,
                                'partner_id': self.partner_id.id }))
                # Create Journal Entry
                if lines:
                    dt_vals['line_ids'] = lines
                    account_move.sudo().create(dt_vals)
        return res
