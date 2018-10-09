# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api


class ConsolidationReferenceMixin(models.AbstractModel):

    _name = 'consolidation.reference.mixin'

    consolidation_company_id = fields.Many2one(
        'res.company', store=True,
        compute='_compute_consolidation_company'
    )

    @api.depends(
        'company_id.sub_consolidation_profile_id.company_id')
    def _compute_consolidation_company(self):
        for item in self:
            profile = item.company_id.sub_consolidation_profile_id
            if profile:
                item.consolidation_company_id = profile.company_id
            else:
                item.consolidation_company_id = False
