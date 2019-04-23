# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CompanyConsolidationProfile(models.Model):

    _name = 'company.consolidation.profile'
    _description = 'Subsidiary consolidation profile'
    _order = 'sub_company_id'
    _rec_name = 'sub_company_id'

    @api.model
    def _default_consolidation_percentage(self):
        return 100

    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env['res.company']._company_default_get(),
        required=True
    )
    consolidation_percentage = fields.Float(
        string='Consolidation percentage',
        help='Define a percentage to consolidate this company (in percents)',
        default=lambda self: self._default_consolidation_percentage(),
        required=True
    )
    sub_company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        string='Subsidiary'
    )

    @api.constrains('consolidation_percentage')
    def _check_consolidation_percentage(self):
        for profile in self:
            if (
                    profile.consolidation_percentage < 0 or
                    profile.consolidation_percentage > 100
            ):
                raise ValidationError(_(
                    'Consolidation percentage can only be defined in the range'
                    'between 0 and 100.'
                ))

    @api.constrains('sub_company_id')
    def _check_sub_company_unique(self):
        """ Ensure there is only one consolidation profile per sub company. """
        for profile in self:
            count = self.search_count(
                [('sub_company_id', '=', profile.sub_company_id.id)])
            if count > 1:
                raise ValidationError(_(
                    'The company %s is already used in a consolidation '
                    'profile.' % profile.sub_company_id.name))

    @api.multi
    def name_get(self):
        return [(record.id,
                 "%s (%s %%)" % (record.sub_company_id.name,
                                 record.consolidation_percentage)
                 ) for record in self]
