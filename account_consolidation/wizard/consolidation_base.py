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
        'subsidiary_chart_ids': fields.one2many('account.consolidation.subsidiary_chart',
                                             'wizard_id', 'Companies', required=True),
    }

    _defaults = {
        'company_id': _default_company,
    }

    def on_change_company_id(self, cr, uid, ids, company_id, context=None):
        comp_chart_obj = self.pool.get('account.consolidation.subsidiary_chart')
        company_obj = self.pool.get('res.company')

        result = {}
        company = company_obj.browse(cr, uid, company_id, context=context)
        if company.consolidation_chart_account_id:
            result['main_chart_account_id'] = company.consolidation_chart_account_id.id

        # FIXME : wizard id error... (code to fill in the child companies in the wizard)
        #missing wizard_id in comp_chart_obj, but ids input parameter is an empty list...
#        result['subsidiary_chart_ids'] = []
#        for child in company.child_ids:
#            child_comp_chart = {'company_id': child.id}
#            child_comp_chart.update(comp_chart_obj.\
#            on_change_company_id(cr, uid, ids, child.id, context=context)['value'])
#            result['subsidiary_chart_ids'].append(
#                comp_chart_obj.create(cr, uid, child_comp_chart, context=context)
#            )

        return {'value': result}

    def on_change_from_period_id(self, cr, uid, ids, from_period_id, to_period_id, context=None):
        result = {}
        if not to_period_id:
            result['to_period_id'] = from_period_id
        return {'value': result}

    def check_subsidiary_periods(self, cr, uid, ids, holding_company_id, subs_company_id, fyear_ids, context=None):
        """
            Check Subsidiary company periods vs Holding company periods
            Return a list of errors
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
        wizard_id = ids[0]
        form = self.browse(cr, uid, wizard_id, context=context)
        fy_to_check = [form.from_period_id.fiscalyear_id.id,
                       form.to_period_id.fiscalyear_id.id]
        fy_to_check = list(set(fy_to_check))  # unify the ids not to check them twice

        errors_by_company = {}
        for subsidiary_chart in form.subsidiary_chart_ids:
            errors  = \
                self.check_subsidiary_periods(cr, uid, ids,
                                              form.company_id.id,
                                              subsidiary_chart.company_id.id,
                                              fy_to_check,
                                              context=context)
            if errors:
                errors_by_company[subsidiary_chart.company_id.id] = errors

        return errors_by_company

    def _chart_accounts_data(self, cr, uid, ids, chart_account_id, context=None):
        context = context or {}
        account_obj = self.pool.get('account.account')
        res = {}
        account_ids = account_obj.\
        _get_children_and_consol(cr, uid, chart_account_id, context=context)
        accounts = account_obj.browse(cr, uid, account_ids, context)
        for account in accounts:
            holding = context.get('holding_coa', False)
            if holding and account.type == 'view':
                continue
                
            res[account.code] = {}
            if holding:
                res[account.code].update({'browse': account})

            if context.get('validate', False):
                # for all (virtual) chart of accounts, when called from the check wizard
                res[account.code].update({
                    'validate': {  # values to validate holding vs subsidiaries
                        'parent': account.parent_id.code,
                        'level': account.level,
                        'active': account.active}
                })

        return res

    def check_subsidiary_chart(self, cr, uid, ids, holding_chart_account_id, subsidiary_chart_account_id, context=None):
        """
            Check a Holding Chart of Accounts vs a Subsidiary Virtual Chart of Accounts
            All the accounts of the Virtual CoA must exist in the Holding CoA.
            The Holding's CoA may hold accounts which do not exist in the Subsidiary's Virtual CoA.
        """
        context = context or {}
        misconfigured_accounts = {}
        check_ctx = context.copy()
        check_ctx.update({'validate': True})
        holding_accounts = self._chart_accounts_data(cr, uid, ids, holding_chart_account_id, context=check_ctx)
        subsidiary_accounts = self._chart_accounts_data(cr, uid, ids, subsidiary_chart_account_id, context=check_ctx)
        # accounts which are configured on the subsidiary VCoA but not on the holding CoA
        spare_accounts = [code for code in subsidiary_accounts
                          if code not in holding_accounts]

        # misconfigured accounts
        for code, values in holding_accounts.iteritems():
            if not subsidiary_accounts.get(code, False):
                pass  # if you want to get the list of accounts existing on the holding
                      # but not on the subsidiary you will get it here
            else:
                for field, value in values['validate'].iteritems():
                    if subsidiary_accounts[code]['validate'].get(field, False) != value:
                        misconfigured_accounts[code] = {field: value}

        return spare_accounts, misconfigured_accounts

    def check_account_charts(self, cr, uid, ids, context=None):
        wizard_id = ids[0]
        form = self.browse(cr, uid, wizard_id, context=context)

        invalid_items_per_company = {}
        for subsidiary_chart in form.subsidiary_chart_ids:
            invalid_items = \
            self.check_subsidiary_chart(cr, uid, ids,
                                        form.holding_chart_account_id.id,
                                        subsidiary_chart.chart_account_id.id,
                                        context=context)
            if any(invalid_items):
                invalid_items_per_company[subsidiary_chart.company_id.id] = invalid_items

        return invalid_items_per_company

    def run_consolidation(self, cr, uid, ids, context=None):
        """
            Proceed with all checks before launch any consolidation step
            This is a base method intended to be inherited with the next consolidation steps
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
