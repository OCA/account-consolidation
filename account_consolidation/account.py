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
