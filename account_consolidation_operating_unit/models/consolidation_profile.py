# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api


class CompanyConsolidationProfile(models.Model):

    _inherit = 'account.consolidation.profile'

    distinct_operating_units = fields.Boolean()

    @api.model
    def _distinction_fields(self):
        res = super()._distinction_fields()
        if 'distinct_operating_units' not in res:
            res.append('distinct_operating_units')
        return res
