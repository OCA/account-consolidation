# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class OperatingUnit(models.Model):

    _name = 'operating.unit'

    _inherit = ['operating.unit', 'account.consolidation.reference.mixin']
