# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    consol_operating_unit_id = fields.Many2one(
        comodel_name='operating.unit',
        string='Consol Operating Unit',
        readonly=True,
    )
