# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011 Camptocamp SA (http://www.camptocamp.com)
#
# Author : Guewen Baconnier (Camptocamp)
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import osv, fields


class account_account(osv.osv):
    _inherit = 'account.account'

    _columns = {
        'consolidation_rate_type_id': fields.many2one('res.currency.rate.type',
                                                      'Consolidation Currency Rate Type',
                                                      help="Currency rate type used on this account for the consolidation, Leave empty to use the rate type of the account type."),
        'consolidation_mode':  fields.selection([('', ''),
                                                 ('ytd', 'YTD'),
                                                 ('period', 'Period Movements'),
                                                 ],
                                                 'Consolidation Mode'),
    }

account_account()


class account_account_type(osv.osv):
    _inherit = 'account.account.type'

    _columns = {
        'consolidation_rate_type_id': fields.many2one('res.currency.rate.type',
                                                      'Consolidation Currency Rate Type',
                                                      help="Currency rate type used on this account type for the consolidation, Leave empty to use the 'spot' rate type."),
        'consolidation_mode':  fields.selection([('ytd', 'YTD'),
                                                 ('period', 'Period Movements'),],
                                                 'Consolidation Mode'),
    }

    _defaults = {
        'consolidation_mode': 'ytd',
    }

account_account_type()


class account_move(osv.osv):
    _inherit = 'account.move'

    _columns = {
        'consol_company_id': fields.many2one('res.company', 'Consolidated from Company', readonly=True),
    }

account_move()
