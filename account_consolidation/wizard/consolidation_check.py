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

from osv import osv


class account_consolidation_base(osv.osv_memory):
    _name = 'account.consolidation.check'
    _inherit = 'account.consolidation.base'
    _description = 'Consolidation Checks. Model used for views'

    def check_account_charts(self, cr, uid, ids, context=None):
        invalid_items_per_company = \
        super(account_consolidation_base, self).check_account_charts(cr, uid, ids, context=context)
        if invalid_items_per_company:
            raise osv.except_osv('Error',
                                 'Invalid charts, TODO display a report %s'
                                 % (invalid_items_per_company,))
        # open a confirmation view ?
        return True

    def check_all_periods(self, cr, uid, ids, context=None):
        errors_by_company = \
        super(account_consolidation_base, self).check_all_periods(cr, uid, ids, context=context)
        if errors_by_company:
            raise osv.except_osv('Error',
                                 'Invalid periods, TODO display a report %s' % (errors_by_company,))
        # open a confirmation view ?
        return True

account_consolidation_base()
