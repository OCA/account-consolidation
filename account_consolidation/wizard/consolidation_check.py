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

from tools.translate import _


class account_consolidation_check(osv.osv_memory):
    _name = 'account.consolidation.check'
    _inherit = 'account.consolidation.base'
    _description = 'Consolidation Checks. Model used for views'

    def check_account_charts(self, cr, uid, ids, context=None):
        """
        Action launched with the button on the view.
        Check the account charts and display a report of the errors

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of the wizard IDs (commonly the first element is the current ID)
        @param context: A standard dictionary for contextual values
        """
        invalid_items_per_company = \
        super(account_consolidation_check, self).check_account_charts(cr, uid, ids, context=context)
        if invalid_items_per_company:
            err_lines = []
            for company_id, account_codes in invalid_items_per_company.iteritems():
                company_obj = self.pool.get('res.company')
                company = company_obj.browse(cr, uid, company_id, context=context)
                err_lines.append(_("%s :") % (company.name,))
                [err_lines.append(_("Account with code %s does not exist on the Holding company.") % (account_code,))
                                  for account_code
                                  in account_codes]
                err_lines.append('')

            raise osv.except_osv(_('Invalid charts'),
                                 '\n'.join(err_lines))

        else:
            raise osv.except_osv(_('Validation'), _('Chart of Accounts are OK.'))
        # open a confirmation view ?
        return True

    def check_all_periods(self, cr, uid, ids, context=None):
        """
        Action launched with the button on the view.
        Check the periods and display a report of the errors

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of the wizard IDs (commonly the first element is the current ID)
        @param context: A standard dictionary for contextual values
        """
        errors_by_company = \
        super(account_consolidation_check, self).check_all_periods(cr, uid, ids, context=context)

        if errors_by_company:
            company_obj = self.pool.get('res.company')

            err_lines = []
            for company_id, errors in errors_by_company.iteritems():
                company = company_obj.browse(cr, uid, company_id, context=context)
                err_lines.append(_("%s :") % (company.name,))
                [err_lines.append(error) for error in errors]
                err_lines.append('')

            raise osv.except_osv(_('Invalid periods'),
                                 '\n'.join(err_lines))
        else:
            raise osv.except_osv(_('Validation'), _('Periods are OK.'))
        # open a confirmation view ?
        return True

account_consolidation_check()
