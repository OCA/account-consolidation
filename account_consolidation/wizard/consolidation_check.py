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

from tools.translate import _


class account_consolidation_check(osv.osv_memory):
    _name = 'account.consolidation.check'
    _inherit = 'account.consolidation.base'
    _description = 'Consolidation Checks. Model used for views'

    _columns = {
        'subsidiary_ids': fields.many2many('res.company', 'account_conso_check_comp_rel', 'conso_id', 'company_id',
                                            'Subsidiaries', required=True),
    }

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
