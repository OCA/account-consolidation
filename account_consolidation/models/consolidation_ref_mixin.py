# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class ConsolidationReferenceMixin(models.AbstractModel):

    _name = 'consolidation.reference.mixin'

    consolidation_company_id = fields.Many2one(
        'res.company',
        compute='_compute_consolidation_company'
    )

    def _compute_consolidation_company(self):
        conso_company = self.env['res.company'].search(
            [('is_consolidation', '=', True)])
        for item in self:
            subs = conso_company.consolidation_profile_ids.mapped(
                'sub_company_id')
            if item.company_id in subs:
                item.consolidation_company_id = conso_company.id
            else:
                item.consolidation_company_id = False
