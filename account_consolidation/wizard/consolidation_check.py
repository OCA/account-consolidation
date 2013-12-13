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

from openerp.osv import osv, orm, fields
from openerp.tools.translate import _


class account_consolidation_check(orm.TransientModel):
    _name = 'account.consolidation.check'
    _inherit = 'account.consolidation.base'
    _description = 'Consolidation Checks. Model used for views'

    _columns = {
        'subsidiary_ids': fields.many2many(
            'res.company',
            'account_conso_check_comp_rel',
            'conso_id',
            'company_id',
            'Subsidiaries',
            required=True),
    }

    def check_account_charts(self, cr, uid, ids, context=None):
        """
        Action launched with the button on the view.
        Check the account charts and display a report of the errors
        """
        company_obj = self.pool.get('res.company')
        invalid_items_per_company = super(account_consolidation_check, self).\
                check_account_charts(cr, uid, ids, context=context)

        if not invalid_items_per_company:
            raise osv.except_osv(
                _('Validation'),
                _('Chart of Accounts are OK.'))

        err_lines = []
        for company_id, account_codes in invalid_items_per_company.iteritems():
            company = company_obj.browse(
                    cr, uid, company_id, context=context)
            err_lines.append(_("%s :") % company.name)
            for account_code in account_codes:
                err_lines.append(
                    _("Account with code %s does not exist on the "
                      "Holding company.") % account_code)
            err_lines.append('')

        raise osv.except_osv(
            _('Invalid charts'), '\n'.join(err_lines))

    def check_all_periods(self, cr, uid, ids, context=None):
        """
        Action launched with the button on the view.
        Check the periods and display a report of the errors
        """
        errors_by_company = super(account_consolidation_check, self).\
                check_all_periods(cr, uid, ids, context=context)

        if not errors_by_company:
            raise osv.except_osv(_('Validation'), _('Periods are OK.'))

        company_obj = self.pool.get('res.company')

        err_lines = []
        for company_id, errors in errors_by_company.iteritems():
            company = company_obj.browse(cr, uid, company_id, context=context)
            err_lines.append(_("%s :") % company.name)
            for error in errors:
                err_lines.append(error)
            err_lines.append('')

        raise osv.except_osv(_('Invalid periods'),
                             '\n'.join(err_lines))


    def check_subsidiary_mapping_account(self, cr, uid, ids, context=None):
        """
        Action launched with the button on the view.
        Check the periods and display a report of the errors
        """
        errors_by_company = super(account_consolidation_check, self).\
                check_subsidiary_mapping_account(cr, uid, ids, context=context)

        if not errors_by_company:
            raise osv.except_osv(_('Validation'), _('All account is mapped'))

        company_obj = self.pool.get('res.company')

        err_lines = []
        for company_id, errors in errors_by_company.iteritems():
            company = company_obj.browse(cr, uid, company_id, context=context)
            err_lines.append(_("%s :") % company.name)
            for error in errors:
                err_lines.append(error)
            err_lines.append('')

        raise osv.except_osv(_('Invalid periods'),
                             '\n'.join(err_lines))

