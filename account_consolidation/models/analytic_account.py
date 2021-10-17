# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class AnalyticAccount(models.Model):

    _name = 'account.analytic.account'
    _inherit = [
        'account.analytic.account', 'account.consolidation.reference.mixin'
    ]
