# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2011-2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    consolidation_mode = fields.Selection(
        [('year', 'for each year in selected period'),
         ('month', 'Monthly Movements')],
        string='Consolidation Mode',
        related='user_type_id.consolidation_mode',
        help="This must be set on the holding company accounts only")

    consolidate_to = fields.Many2one(
        'account.account',
        string='Consolidate To',
    )

    consolidated_childs = fields.One2many('account.account','consolidate_to')

    @api.constrains('consolidate_to')
    def _check_parent_company(self):
        for rec in self:
            if self.consolidate_to.company_id and \
                    self.consolidate_to.company_id != \
                            self.company_id.parent_id:
                raise ValidationError("Account to consolidate must be " +
                                      "account of parent company")


class AccountAccountType(models.Model):
    _inherit = 'account.account.type'

    consolidation_mode = fields.Selection(
        [('year', 'for each year in selected period'),
         ('month', 'Monthly Movements')],
        string='Consolidation Mode',
        default='year',
        help="This must be set on the holding company accounts only")

class AccountMove(models.Model):
    _inherit = 'account.move'

    consol_company_id = fields.Many2one(
        'res.company',
        'Consolidated from Company',
        readonly=True)
