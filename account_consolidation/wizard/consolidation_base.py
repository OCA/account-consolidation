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


class account_consolidation_base(orm.AbstractModel):
    _name = 'account.consolidation.base'
    _description = 'Common consolidation wizard. Intended to be inherited'

    def _default_company(self, cr, uid, context=None):
        comp_obj = self.pool['res.company']
        return comp_obj._company_default_get(cr, uid)

    def _default_chart(self, cr, uid, context=None):
        comp_obj = self.pool['res.company']
        comp_id = comp_obj._company_default_get(cr, uid)
        company = comp_obj.browse(cr, uid, comp_id)
        return company.consolidation_chart_account_id.id

    _columns = {
        'fiscalyear_id': fields.many2one(
            'account.fiscalyear',
            'Fiscal Year',
            required=True,
            help="The checks will be done on the periods of "
                 "the selected fiscal year."),
        'company_id': fields.many2one(
            'res.company', 'Company', required=True),
        'holding_chart_account_id': fields.many2one(
            'account.account',
            'Chart of Accounts',
            required=True,
            domain=[('parent_id', '=', False)]),
        'subsidiary_ids': fields.many2many(
            'res.company',
            'account_conso_comp_rel',
            'conso_id',
            'company_id',
            'Subsidiaries',
            required=True)
    }

    _defaults = {'company_id': _default_company,
                 'holding_chart_account_id': _default_chart,
                 }

    def on_change_company_id(self, cr, uid, ids, company_id, context=None):
        """
        On change of the company, set the chart of account and the subsidiaries

        :param company_id: ID of the selected company

        :return: dict of values to change
        """
        company_obj = self.pool.get('res.company')

        result = {}
        company = company_obj.browse(cr, uid, company_id, context=context)
        if company.consolidation_chart_account_id:
            result['main_chart_account_id'] = company.consolidation_chart_account_id.id

        result['subsidiary_ids'] = [child.id for child in company.child_ids]

        return {'value': result}

    def check_subsidiary_periods(self, cr, uid, ids, holding_company_id,
                                 subs_company_id, fyear_id, context=None):
        """ Check Subsidiary company periods vs Holding company periods and
        returns a list of errors

        The periods checked are the periods within the fiscal year of the
        holding, and the periods of the subsidiary company in the same range of
        time.

        The fiscal year of the subsidiary is deduced from the start/stop date
        of the holding's fiscal year.

        All the periods defined within the group must have the same beginning
        and ending dates to be valid.

        :param holding_company_id: ID of the holding company
        :param subs_company_id: ID of the subsidiary company to check
        :param fyear_id: ID of the fiscal year of the holding.

        :return: dict of list with errors for each company
                 {company_id: ['error 1', 'error2']}
        """
        company_obj = self.pool.get('res.company')
        period_obj = self.pool.get('account.period')
        fy_obj = self.pool.get('account.fiscalyear')

        holding_fiscal_year = fy_obj.browse(cr, uid, fyear_id, context=context)

        # contains errors
        errors = []

        # get holding fiscal year and periods
        holding = company_obj.browse(
                cr, uid, holding_company_id, context=context)
        subsidiary = company_obj.browse(
                cr, uid, subs_company_id, context=context)

        holding_periods_ids = period_obj.search(
            cr, uid,
            [('company_id', '=', holding.id),
             ('fiscalyear_id', '=', holding_fiscal_year.id)],
            context=context)
        holding_periods = period_obj.browse(
                cr, uid, holding_periods_ids, context=context)

        # get subsidiary fiscal year and periods
        subsidiary_fiscal_year = fy_obj.search(
            cr, uid,
            [('company_id', '=', subsidiary.id),
             ('date_start', '=', holding_fiscal_year.date_start),
             ('date_stop', '=', holding_fiscal_year.date_stop),
            ],
            context=context)
        if not subsidiary_fiscal_year:
            errors.append(
                _('The fiscal year of the subsidiary company %s '
                  'does not exists from %s to %s') %
                    (subsidiary.name,
                    holding_fiscal_year.date_start,
                    holding_fiscal_year.date_stop))
        else:
            subsidiary_period_ids = period_obj.search(
                cr, uid,
                [('company_id', '=', subsidiary.id),
                  # 0 because there can be only 1 fiscal year
                  # on the same dates than the holding
                 ('fiscalyear_id', '=', subsidiary_fiscal_year[0])],
                context=context)
            subsidiary_periods = period_obj.browse(
                    cr, uid, subsidiary_period_ids, context=context)

            # a holding fiscal year may have more periods than a subsidiary
            # (a subsidiary created at the middle of the year for example)
            # but the reverse situation is not allowed
            if len(holding_periods) < len(subsidiary_periods):
                errors.append(
                    _('Holding company has less periods than the '
                      'subsidiary company %s!') % subsidiary.name)

            # check subsidiary periods dates vs holding periods
            # for each period of the subsidiary
            for subsidiary_period in subsidiary_periods:
                period_exists = False
                for holding_period in holding_periods:
                    if (subsidiary_period.date_start == holding_period.date_start and
                            subsidiary_period.date_stop == holding_period.date_stop):
                        period_exists = True
                        break
                if not period_exists:
                    errors.append(
                        _('Period from %s to %s not found '
                          'in holding company %s') %
                            (subsidiary_period.date_start,
                            subsidiary_period.date_stop,
                            holding.name))
        return errors

    def check_all_periods(self, cr, uid, ids, context=None):
        """
        Call the period check on each period of all subsidiaries
        Returns the errors by subsidiary

        :return: dict of list with errors for each company
                 {company_id: ['error 1', 'error2']}
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        assert len(ids) == 1, "only 1 id expected"

        form = self.browse(cr, uid, ids[0], context=context)

        errors_by_company = {}
        for subsidiary in form.subsidiary_ids:
            errors = self.check_subsidiary_periods(
                cr, uid,
                ids,
                form.company_id.id,
                subsidiary.id,
                form.fiscalyear_id.id,
                context=context)
            if errors:
                errors_by_company[subsidiary.id] = errors

        return errors_by_company

    def _chart_accounts_data(self, cr, uid, ids, chart_account_id, context=None):
        """
        Returns the list of accounts to use for the consolidation
        for the holding or the subsidiaries.
        Keys of the returned dict are the account codes and
        if the context is holding_coa,
        dict values are the browse instances of the accounts

        :chart_account_id: ID of the Chart of Account for which
                           we want the account codes

        :return: dict with {account codes: browse instances}
        """
        if context is None:
            context = {}
        account_obj = self.pool.get('account.account')
        res = {}
        account_ids = account_obj._get_children_and_consol(
                cr, uid, chart_account_id, context=context)

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
            # we'll need the browse object during the
            # "consolidate wizard" for the holding
            res[account.code] = account if holding else True

        return res

    def check_subsidiary_mapping_account(self, cr, uid, ids, context=None):
        """
        Call the period check on each period of all subsidiaries
        Returns the errors by subsidiary

        :return: dict of list with errors for each company
                 {company_id: ['error 1', 'error2']}
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        assert len(ids) == 1, "only 1 id expected"

        form = self.browse(cr, uid, ids[0], context=context)
        errors_by_company = {}
        for subsidiary in form.subsidiary_ids:
            errors = self._check_subsidiary_mapping_account(
                cr, uid,
                ids,
                subsidiary,
                context=context)
            if errors:
                errors_by_company[subsidiary.id] = errors

        return errors_by_company

    def _check_subsidiary_mapping_account(self, cr, uid, ids,
                                          company_id, context=None):
        if context is None:
            context = {}
        errors = []
        account_obj = self.pool.get('account.account')
        normal_account_ids = account_obj.search(cr, uid,
                                                [('company_id',
                                                  '=',
                                                  company_id.id),
                                                 ('type',
                                                  'not in',
                                                  ['consolidation', 'view'])],
                                                  context=context)
        consolidated_account_ids = account_obj.search(cr, uid,
                                                      [('company_id',
                                                        '=',
                                                        company_id.id),
                                                       ('type',
                                                        '=',
                                                        'consolidation')],
                                                        context=context)
        consolidate_child_ids = []
        for account_id in consolidated_account_ids:
            consolidate_child_ids=consolidate_child_ids+account_obj._get_children_and_consol(cr, uid, account_id, context=context)
        for sub_id in normal_account_ids:
            res = {}
            cpt_occur = consolidate_child_ids.count(sub_id)
            if cpt_occur == 0 or cpt_occur > 1:
                ## We read the code of account
                code = account_obj.read(cr, uid, sub_id, ['code'], context=context)['code']
                message = _("Code %s is mapping %s times" % (code, cpt_occur))
                errors.append(message)
        return errors

    def check_subsidiary_chart(self, cr, uid, ids, holding_chart_account_id,
                               subsidiary_chart_account_id, context=None):
        """
        Check a Holding Chart of Accounts vs a Subsidiary Virtual
        Chart of Accounts
        All the accounts of the Virtual CoA must exist in the Holding CoA.
        The Holding's CoA may hold accounts which do not exist
        in the Subsidiary's Virtual CoA.

        :param holding_chart_account_id: ID of the Chart of Account
                                         of the holding company
        :param subsidiary_chart_account_id: ID of the Chart of Account
                                            of the subsidiary company to check

        :return: List of accounts existing on subsidiary but no on holding COA
        """
        if context is None:
            context = {}
        holding_ctx = dict(context, holding_coa=True)
        holding_accounts = self._chart_accounts_data(
                cr, uid, ids, holding_chart_account_id, context=holding_ctx)
        subsidiary_accounts = self._chart_accounts_data(
                cr, uid, ids, subsidiary_chart_account_id, context=context)
        # accounts which are configured on the subsidiary
        # Virtual CoA but not on the holding CoA
        spare_accounts = [code for code
                          in subsidiary_accounts
                          if code not in holding_accounts]
        return spare_accounts

    def check_account_charts(self, cr, uid, ids, context=None):
        """
        Check the chart of accounts of the holding vs
        each virtual chart of accounts of the subsidiaries
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        assert len(ids) == 1, "only 1 id expected"
        form = self.browse(cr, uid, ids[0], context=context)

        invalid_items_per_company = {}
        for subsidiary in form.subsidiary_ids:
            if not subsidiary.consolidation_chart_account_id:
                raise osv.except_osv(
                        _('Error'),
                        _('No chart of accounts for company %s') % subsidiary)
            invalid_items = self.check_subsidiary_chart(
                    cr, uid,
                    ids,
                    form.holding_chart_account_id.id,
                    subsidiary.consolidation_chart_account_id.id,
                    context=context)
            if any(invalid_items):
                invalid_items_per_company[subsidiary.id] = invalid_items

        return invalid_items_per_company

    def run_consolidation(self, cr, uid, ids, context=None):
        """
        Proceed with all checks before launch any consolidation step
        This is a base method intended to be inherited with the next
        consolidation steps
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        assert len(ids) == 1, "only 1 id expected"

        if self.check_all_periods(cr, uid, ids, context=context):
            raise osv.except_osv(
                _('Error'),
                _('Invalid periods, please launch the '
                  '"Consolidation: Checks" wizard'))
        if self.check_account_charts(cr, uid, ids, context=context):
            raise osv.except_osv(
                _('Error'),
                _('Invalid charts, please launch the '
                  '"Consolidation: Checks" wizard'))

        # inherit to add the next steps of the reconciliation

        return {'type': 'ir.actions.act_window_close'}
