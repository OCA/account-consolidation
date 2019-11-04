# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.exceptions import ValidationError
from odoo import _, api, fields, models


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    distribution_ids = fields.One2many('account.invoice.line.distribution',
                                       'invoice_line_id',
                                       string='Distribution',
                                       copy=True)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        for dist_id in res.distribution_ids:
            dist_id.invoice_line_id = res.id
        self._check_percentages()
        return res

    @api.model
    def write(self, vals):
        res = super().write(vals)
        if vals.get('distribution_ids', False):
            for dist_id in self.distribution_ids:
                dist_id.invoice_line_id = self.id
            self._check_percentages()
        return res

    @api.multi
    def _check_percentages(self):
        for line_id in self:
            if line_id.distribution_ids:
                total = 0.00
                for dist_id in line_id.distribution_ids:
                    total += dist_id.percent
                if total != 100.00:
                    raise ValidationError(_('Line {} distribution does \
                                            not total 100%').format(line_id.\
                                            name))
