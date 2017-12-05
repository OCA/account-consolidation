# -* coding: utf-8 -*-
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

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    consolidation_group = fields.Many2one(
        'account.account.group',
        'Consolidation account parent group',
        help=('Current company root account group used for consolidation')
    )

    consolidation_diff_account_id = fields.Many2one(
        'account.account',
        'Consolidation difference account',
        help=("Conso. differences will be affected to this account"))
