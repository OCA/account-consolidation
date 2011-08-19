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
from tools.translate import _


class account_consolidation_base(osv.osv_memory):
    _name = 'account.consolidation.base'
    _description = 'Common consolidation wizard. Intended to be inherited'

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]

    _columns = {
        'from_period_id': fields.many2one('account.period', 'Start Period', required=True,
            help="Select the same period in 'from' and 'to' if you want to proceed with a single period."),
        'to_period_id': fields.many2one('account.period', 'End Period', required=True,
            help="The consolidation will be done at the very last date of the selected period."),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'holding_chart_account_id': fields.many2one('account.account',
                                                 'Chart of Accounts',
                                                 required=True,
                                                 domain=[('parent_id', '=', False)]),
        'subsidiary_ids': fields.many2many('res.company', 'account_conso_comp_rel', 'id', 'id',
                                           'Subsidiaries', required=True)
    }

    _defaults = {
        'company_id': _default_company,
    }

    def on_change_company_id(self, cr, uid, ids, company_id, context=None):
        """
        On change of the company, set the chart of account and the subsidiaries

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of the wizard IDs (commonly the first element is the current ID)
        @param company_id: ID of the selected company
        @param context: A standard dictionary for contextual values

        @return: dict of values to change
        """
        company_obj = self.pool.get('res.company')

        result = {}
        company = company_obj.browse(cr, uid, company_id, context=context)
        if company.consolidation_chart_account_id:
            result['main_chart_account_id'] = company.consolidation_chart_account_id.id

        result['subsidiary_ids'] = [child.id for child in company.child_ids]

        return {'value': result}

    def on_change_from_period_id(self, cr, uid, ids, from_period_id, to_period_id, context=None):
        """
        On change of the From period, set the To period to the same period if it is empty

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of the wizard IDs (commonly the first element is the current ID)
        @param from_period_id: ID of the selected from period id
        @param to_period_id: ID of the current from period id
        @param context: A standard dictionary for contextual values

        @return: dict of values to change
        """
        result = {}
        if not to_period_id:
            result['to_period_id'] = from_period_id
        return {'value': result}

    def check_subsidiary_periods(self, cr, uid, ids, holding_company_id, subs_company_id, fyear_ids, context=None):
        """
        Check Subsidiary company periods vs Holding company periods and returns a list of errors
        All the periods defined within the group must be the same (same beginning and ending dates)

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of the wizard IDs (commonly the first element is the current ID)
        @param holding_company_id: ID of the holding company
        @param subs_company_id: ID of the subsidiary company to check
        @param fyear_ids: List of IDs of the fiscal years to compare
        @param context: A standard dictionary for contextual values

        @return: dict of list with errors for each company {company_id: ['error 1', 'error2']}
        """
        company_obj = self.pool.get('res.company')
        period_obj = self.pool.get('account.period')
        fy_obj = self.pool.get('account.fiscalyear')

        # contains errors
        errors = []
        for fyear_id in fy_obj.browse(cr, uid, fyear_ids, context=context):
            # get holding fiscal year and periods
            holding = company_obj.browse(cr, uid, holding_company_id, context=context)
            subsidiary = company_obj.browse(cr, uid, subs_company_id, context=context)

            holding_fiscal_year = fyear_id
            holding_periods_ids = period_obj.search(cr, uid,
                [('company_id', '=', holding.id),
                 ('fiscalyear_id', '=', holding_fiscal_year.id)],
                context=context)
            holding_periods = period_obj.browse(cr, uid, holding_periods_ids, context=context)

            # get subsidiary fiscal year and periods
            subsidiary_fiscal_year = fy_obj.search(cr, uid,
                [('company_id', '=', subsidiary.id),
                 ('date_start', '=', holding_fiscal_year.date_start),
                 ('date_stop', '=', holding_fiscal_year.date_stop),
                ])
            if not subsidiary_fiscal_year:
                errors.append(_('The fiscal year of the subsidiary company %s does not exists from %s to %s')
                % (subsidiary.name, holding_fiscal_year.date_start, holding_fiscal_year.date_stop))

            subsidiary_period_ids = period_obj.search(cr, uid,
                [('company_id', '=', subsidiary.id),
                 ('fiscalyear_id', '=', subsidiary_fiscal_year[0])],  # 0 because there can be only 1 fiscal year on the same dates as the holding
                context=context)
            subsidiary_periods = period_obj.browse(cr, uid, subsidiary_period_ids, context=context)

            # check subsidiary periods vs holding periods
            for holding_period in holding_periods:
                period_exists = False
                for subsidiary_period in subsidiary_periods:
                    if subsidiary_period.date_start == holding_period.date_start \
                    and subsidiary_period.date_stop == holding_period.date_stop:
                        period_exists = True
                        break
                if not period_exists:
                    errors.append(_('Period not found in subsidiary company %s from %s to %s')
                    % (holding.name, holding_period.date_start, holding_period.date_stop))

        return errors

    def check_all_periods(self, cr, uid, ids, context=None):
        """
        Call the period check on each period of all subsidiaries
        Returns the errors by subsidiary

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of the wizard IDs (commonly the first element is the current ID)
        @param context: A standard dictionary for contextual values

        @return: dict of list with errors for each company {company_id: ['error 1', 'error2']}
        """
        form = self.browse(cr, uid, ids[0], context=context)
        fy_to_check = [form.from_period_id.fiscalyear_id.id,
                       form.to_period_id.fiscalyear_id.id]
        fy_to_check = list(set(fy_to_check))  # unify the ids not to check them twice

        errors_by_company = {}
        for subsidiary in form.subsidiary_ids:
            errors = \
                self.check_subsidiary_periods(cr, uid, ids,
                                              form.company_id.id,
                                              subsidiary.id,
                                              fy_to_check,
                                              context=context)
            if errors:
                errors_by_company[subsidiary.id] = errors

        return errors_by_company

    def _chart_accounts_data(self, cr, uid, ids, chart_account_id, context=None):
        """
        Returns the list of accounts to use for the consolidation for the holding
        or the subsidiaries. Keys of the returned dict are the account codes and
        if the context is holding_coa, dict values are the browse instances of the accounts

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of the wizard IDs (commonly the first element is the current ID)
        @chart_account_id: ID of the "Chart" Account for which we want the account codes
        @param context: A standard dictionary for contextual values

        @return: dict with {account codes: browse instances}
        """
        context = context or {}
        account_obj = self.pool.get('account.account')
        res = {}
        account_ids = account_obj.\
        _get_children_and_consol(cr, uid, chart_account_id, context=context)

        # do not consolidate chart root
        account_ids.remove(chart_account_id)

        for account in account_obj.browse(cr, uid, account_ids, context):
            holding = context.get('holding_coa', False)

            # do not consolidate to view accounts
            if holding and account.type == 'view':
                continue

            # only consolidate the consolidation accounts
            if not holding and account.type != 'consolidation':
                continue

            res[account.code] = {}
            # we'll need the browse object during the "consolidate wizard" for the holding
            res[account.code] = holding and account or True

        return res

    def check_subsidiary_chart(self, cr, uid, ids, holding_chart_account_id, subsidiary_chart_account_id, context=None):
        """
        Check a Holding Chart of Accounts vs a Subsidiary Virtual Chart of Accounts
        All the accounts of the Virtual CoA must exist in the Holding CoA.
        The Holding's CoA may hold accounts which do not exist in the Subsidiary's Virtual CoA.

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of the wizard IDs (commonly the first element is the current ID)
        @param holding_chart_account_id: ID of the "Chart" Account of the holding company
        @param subsidiary_chart_account_id: ID of the "Chart" Account of the subsidiary company to check
        @param context: A standard dictionary for contextual values

        @return: List of accounts existing on subsidiary but no on holding COA
        """
        context = context or {}
        holding_ctx = context.copy()
        holding_ctx.update({'holding_coa': True})
        holding_accounts = self._chart_accounts_data(cr, uid, ids, holding_chart_account_id, context=holding_ctx)
        subsidiary_accounts = self._chart_accounts_data(cr, uid, ids, subsidiary_chart_account_id, context=context)
        # accounts which are configured on the subsidiary VCoA but not on the holding CoA
        spare_accounts = [code for code
                          in subsidiary_accounts
                          if code not in holding_accounts]

        return spare_accounts

    def check_account_charts(self, cr, uid, ids, context=None):
        """
        Check the chart of accounts of the holding vs each virtual chart of accounts of the subsidiaries

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of the wizard IDs (commonly the first element is the current ID)
        @param context: A standard dictionary for contextual values
        """
        form = self.browse(cr, uid, ids[0], context=context)

        invalid_items_per_company = {}
        for subsidiary in form.subsidiary_ids:
            if not subsidiary.consolidation_chart_account_id:
                raise osv.except_osv(_('Error'), _('No chart of accounts for company %s') % (subsidiary,))

            invalid_items = \
            self.check_subsidiary_chart(cr, uid, ids,
                                        form.holding_chart_account_id.id,
                                        subsidiary.company_id.consolidation_chart_account_id.id,
                                        context=context)
            if any(invalid_items):
                invalid_items_per_company[subsidiary.id] = invalid_items

        return invalid_items_per_company

    def run_consolidation(self, cr, uid, ids, context=None):
        """
        Proceed with all checks before launch any consolidation step
        This is a base method intended to be inherited with the next consolidation steps

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of the wizard IDs (commonly the first element is the current ID)
        @param context: A standard dictionary for contextual values
        """

        if self.check_all_periods(cr, uid, ids, context=context):
            raise osv.except_osv(_('Error'),
                                 _('Invalid periods, please launch the "Consolidation: Checks" wizard'))
        if self.check_account_charts(cr, uid, ids, context=context):
            raise osv.except_osv(_('Error'),
                                 _('Invalid charts, please launch the "Consolidation: Checks" wizard'))

        # inherit to add the next steps of the reconciliation

        return {'type': 'ir.actions.act_window_close'}


account_consolidation_base()
