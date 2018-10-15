# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from itertools import combinations
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CompanyConsolidationProfile(models.Model):
    """Consolidation profile is used to define consolidation rules.

    It links ONE consolidation company to MULTIPLE subsidiaries you want to
    consolidate.
    It also allows to specify some options like consolidation percentage, and
    enable distinctions on intercompany partners and analytic accounts
    """

    _name = 'account.consolidation.profile'
    _description = 'Subsidiary consolidation profile'
    _order = 'sub_company_id'
    _rec_name = 'sub_company_id'

    @api.model
    def _default_consolidation_percentage(self):
        return 100

    # This is the consolidation company
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env['res.company']._company_default_get(),
        required=True
    )
    # This is the subsidiary (company to consolidate)
    sub_company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        string='Subsidiary'
    )

    consolidation_percentage = fields.Float(
        string='Consolidation percentage',
        help='Define a percentage to consolidate this company (in percents)',
        default=lambda self: self._default_consolidation_percentage(),
        required=True
    )
    distinct_interco_partners = fields.Boolean(
        string="Distinct inter-company partners",
        default=True,
        help="Check this box if you do not want to group move lines from "
             "inter-company partners."
    )
    distinct_analytic_accounts = fields.Boolean(
        string="Distinct analytic accounts",
        help="Check this box if you do not want to group move lines from "
             "different analytic accounts."
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

    @api.model
    def _distinction_fields(self):
        """Return a list of possible distinction to apply on consolidation.

        Each element must match a field on consolidation profile using
        distinct_* ."""
        return [
            field_name for field_name in list(
                self.env['account.consolidation.profile']._fields
            ) if field_name.startswith('distinct')]

    @api.multi
    def get_distinctions(self):
        """Return a list of all possible distinctions combinations as tuples
        according to the activated flags distinct_*.

        Example : if distinct_analytic_accounts AND distinct_interco_partners
        are both marked, we want to get all the combinations of any length,
        (i.e including the empty one) ordered by their length reversed:
        [('distinct_analytic_accounts', 'distinct_interco_partners'),
         ('distinct_interco_partners'),
         ('distinct_analytic_accounts'),
         ()]"""
        self.ensure_one()
        res = []
        distinctions = self._distinction_fields()
        values = self.read(distinctions)[0]
        for length in range(0, len(distinctions) + 1):
            for subset in combinations(distinctions, length):
                if all([values.get(s) for s in subset if s]):
                    res.append(subset)
        return sorted(res, key=lambda d: len(d), reverse=True)

    @api.model
    def create(self, vals):
        """Ensure inverse relation to sub_company_id
        (sub_consolidation_profile_id) is defined on the subsidiary company."""
        profile = super().create(vals)
        profile.sub_company_id.sub_consolidation_profile_id = profile.id
        return profile

    @api.multi
    def write(self, vals):
        """Ensure inverse relation to sub_company_id
        (sub_consolidation_profile_id) is up to date on the subsidiary
        company."""
        res = super().write(vals)
        if vals.get('sub_company_id'):
            self.sub_company_id.sub_consolidation_profile_id = self.id
        return res
