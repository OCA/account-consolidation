# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountInvoiceLineDistribution(models.Model):
    _name = 'account.invoice.line.distribution'

    name = fields.Char(string="Name", related='company_id.name')

    percent = fields.Float(string="Percentage")
    invoice_line_id = fields.Many2one('account.invoice.line',
                                      string="Bill Line",
                                      readonly=True)

    @api.multi
    def _default_company_id(self):
        return self.env.user.company_id

    company_id = fields.Many2one('res.company', string="Company",
                                 default=_default_company_id)
