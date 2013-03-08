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

from openerp.osv import orm, fields
from openerp.osv.osv import except_osv
from openerp.tools.translate import _


class account_consolidation_consolidate(orm.TransientModel):
    _name = 'account.consolidation.consolidate'
    _inherit = 'account.consolidation.base'

    _columns = {
        'from_period_id': fields.many2one(
            'account.period',
            'Start Period',
            required=True,
            help="Select the same period in 'from' and 'to' "
                 "if you want to proceed with a single period. "
                 "Start Period is ignored for Year To Date accounts."),
        'to_period_id': fields.many2one(
            'account.period',
            'End Period',
            required=True,
            help="The consolidation will be done at the very "
                 "last date of the selected period."),
        'journal_id': fields.many2one(
            'account.journal', 'Journal', required=True),
        'target_move': fields.selection(
            [('posted', 'All Posted Entries'),
             ('all', 'All Entries')],
            'Target Moves',
            required=True),
        'subsidiary_ids': fields.many2many(
            'res.company',
            'account_conso_conso_comp_rel',
            'conso_id',
            'company_id',
            string='Subsidiaries',
            required=True),
    }

    _defaults = {
        'target_move': 'posted'
    }

    def _check_periods_fy(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        assert len(ids) == 1, "only 1 id expected"

        form = self.browse(cr, uid, ids[0], context=context)
        return (form.from_period_id.fiscalyear_id.id ==
                form.to_period_id.fiscalyear_id.id)

    _constraints = [
        (_check_periods_fy,
         'Start Period and End Period must be of the same Fiscal Year !',
         ['from_period_id', 'to_period_id']),
    ]

    def on_change_from_period_id(self, cr, uid, ids, from_period_id,
                                 to_period_id, context=None):
        """ On change of the From period, set the To period
        to the same period if it is empty

        :param from_period_id: ID of the selected from period id
        :param to_period_id: ID of the current from period id

        :return: dict of values to change
        """
        result = {}
        period_obj = self.pool.get('account.period')
        from_period = period_obj.browse(
                cr, uid, from_period_id, context=context)
        if not to_period_id:
            result['to_period_id'] = from_period_id
        else:
            to_period = period_obj.browse(
                    cr, uid, to_period_id, context=context)
            if to_period.date_start < from_period.date_start:
                result['to_period_id'] = from_period_id

        result['fiscalyear_id'] = from_period.fiscalyear_id.id
        return {'value': result}

    def _currency_rate_type(self, cr, uid, ids, account, context=None):
        """
        Returns the currency rate type to use

        :param account: browse_record instance of account.account

        :return: id of the currency rate type to use
        """
        if account.consolidation_rate_type_id:
            return account.consolidation_rate_type_id.id

        elif account.user_type.consolidation_rate_type_id:
            return account.user_type.consolidation_rate_type_id.id

        else:
            return False

    def _consolidation_mode(self, cr, uid, ids, account, context=None):
        """
        Returns the consolidation mode to use

        :param account: browse instance of account.account

        :return: 'ytd' or 'period'
        """
        return (account.consolidation_mode or
                account.user_type.consolidation_mode)

    def _periods_holding_to_subsidiary(self, cr, uid, ids, period_ids,
                                       subsidiary_id, context=None):
        """
        Returns the periods of a subsidiary company which
        correspond to the holding periods (same beginning and ending dates)

        :param period_ids: list of periods of the holding
        :param subsidiary_id: ID of the subsidiary for which
                              we want the period IDs

        :return: list of periods of the subsidiaries
        """
        period_obj = self.pool.get('account.period')
        if isinstance(period_ids, (int, long)):
            period_ids = [period_ids]

        subs_period_ids = []
        for period in period_obj.browse(cr, uid, period_ids, context=context):
            subs_period_ids += period_obj.search(
                cr, uid,
                [('date_start', '=', period.date_start),
                 ('date_stop', '=', period.date_stop),
                 ('company_id', '=', subsidiary_id)],
                context=context)
        return subs_period_ids

    def create_rate_difference_line(self, cr, uid, ids, move_id, context):
        """
        We can have consolidation difference when a account is in YTD but in normal counterpart
        has a different setting.
        """
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        move = move_obj.browse(cr, uid, move_id, context=context)

        if not move.line_id:
            return False
        diff_account = move.company_id.consolidation_diff_account_id
        if not diff_account:
            raise except_osv(_('Settings ERROR'),
                             _('Please set the "Consolidation difference account"'
                               ' in company %s') % move.company_id.name)
        debit = credit = 0.0
        for line in move.line_id:
            debit += line.debit
            credit += line.credit
        balance = debit - credit
        if balance:
            diff_vals = {'account_id': diff_account.id,
                         'move_id': move.id,
                         'journal_id': move.journal_id.id,
                         'period_id': move.period_id.id,
                         'company_id': move.company_id.id,
                         'date': move.date,
                         'debit': balance if balance > 0.0 else 0.0,
                         'credit': abs(balance) if balance < 0.0 else 0.0
                         }
            return move_line_obj.create(cr, uid, diff_vals, context=context)
        return False


    def consolidate_account(self, cr, uid, ids, consolidation_mode,
                            subsidiary_period_ids, state, move_id,
                            holding_account_id, subsidiary_id, context=None):
        """
        Consolidates the subsidiary account on the holding account
        Creates move lines on the move with id "move_id"

        :param consolidation_mode: consolidate by Periods or
                                   Year To Date ('period' or 'ytd')
        :param subsidiary_period_ids: IDs of periods for which we
                                      want to sum the debit/credit
        :param state: state of the moves to consolidate ('all' or 'posted')
        :param move_id: ID of the move on which all the
                        created move lines will be linked
        :param holding_account_id: ID of the account to consolidate
                                   (on the holding), the method will
                                   find the subsidiary's corresponding account
        :param subsidiary_id: ID of the subsidiary to consolidate

        :return: list of IDs of the created move lines
        """
        if context is None:
            context = {}

        account_obj = self.pool.get('account.account')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')

        move = move_obj.browse(cr, uid, move_id, context=context)
        holding_account = account_obj.browse(
                cr, uid, holding_account_id, context=context)

        subsidiary_account_id = account_obj.search(
                cr, uid,
                [('code', '=', holding_account.code),
                 ('company_id', '=', subsidiary_id)],
                context=context)

        if not subsidiary_account_id:
            # an account may exist on the holding and not in the subsidiaries,
            # nothing to do
            return []

        browse_ctx = dict(context, state=state, periods=subsidiary_period_ids)
        # 1st item because the account's code is unique per company
        subs_account = account_obj.browse(
                cr, uid, subsidiary_account_id[0], context=browse_ctx)

        vals = {
            'name': _("Consolidation line in %s mode") % consolidation_mode,
            'account_id': holding_account.id,
            'move_id': move.id,
            'journal_id': move.journal_id.id,
            'period_id': move.period_id.id,
            'company_id': move.company_id.id,
            'date': move.date
        }

        balance = subs_account.balance
        print balance
        if not balance:
            return None
        if (holding_account.company_currency_id.id ==
                subs_account.company_currency_id.id):
            vals.update({
                'debit': balance if balance > 0.0 else 0.0,
                'credit': abs(balance) if balance < 0.0 else 0.0,
            })
        else:
            currency_rate_type = self._currency_rate_type(
                    cr, uid, ids, holding_account, context=context)

            currency_value = currency_obj.compute(
                    cr, uid,
                    holding_account.company_currency_id.id,
                    subs_account.company_currency_id.id,
                    balance,
                    currency_rate_type_from=False,  # means spot
                    currency_rate_type_to=currency_rate_type,
                    context=context)
            vals.update({
                'currency_id': subs_account.company_currency_id.id,
                'amount_currency': subs_account.balance,
                'debit': currency_value if currency_value > 0.0 else 0.0,
                'credit': abs(currency_value) if currency_value < 0.0 else 0.0,
            })
        move_line_id = move_line_obj.create(cr, uid, vals, context=context)
        return move_line_id

    def reverse_moves(self, cr, uid, ids, subsidiary_id, journal_id,
                      reversal_date, context=None):
        """
        Reverse all account moves of a journal which have
        the "To be reversed" flag

        :param subsidiary_id: ID of the subsidiary moves to reverse
        :param journal_id: ID of the journal with moves to reverse
        :param reversal_date: date when to create the reversal

        :return: tuple with : list of IDs of the reversed moves,
                              list of IDs of the reversal moves
        """
        move_obj = self.pool.get('account.move')
        reversed_ids = move_obj.search(
                cr, uid,
                [('journal_id', '=', journal_id),
                 ('to_be_reversed', '=', True),
                 ('consol_company_id', '=', subsidiary_id)],
                context=context)
        reversal_ids = move_obj.create_reversals(
                cr, uid, reversed_ids, reversal_date, context=context)
        return reversed_ids, reversal_ids

    def consolidate_subsidiary(self, cr, uid, ids,
                               subsidiary_id, context=None):
        """
        Consolidate one subsidiary on the Holding.
        Create a move per subsidiary and consolidation type (YTD/Period)
        and an move line per account of the subsidiary

        :param subsidiary_id: ID of the subsidiary to consolidate
                              on the holding

        :return: Tuple of form:
                 (list of IDs of the YTD moves,
                  list of IDs of the Period Moves)
        """
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]
        assert len(ids) == 1, "only 1 id expected"

        company_obj = self.pool.get('res.company')
        move_obj = self.pool.get('account.move')
        period_obj = self.pool.get('account.period')

        form = self.browse(cr, uid, ids[0], context=context)
        subsidiary = company_obj.browse(cr, uid, subsidiary_id, context=None)

        data_ctx = dict(context, holding_coa=True)
        holding_accounts_data = self._chart_accounts_data(
                cr, uid,
                ids,
                form.holding_chart_account_id.id,
                context=data_ctx)
        subs_accounts_codes = self._chart_accounts_data(
                cr, uid,
                ids,
                subsidiary.consolidation_chart_account_id.id,
                context=context)
        holding_accounts = [values for key, values
                            in holding_accounts_data.iteritems()
                            if key in subs_accounts_codes]

        # split accounts in ytd and periods modes
        # a move per type will be created
        consolidation_modes = {'ytd': [], 'period': []}
        for account in holding_accounts:
            cm = self._consolidation_mode(
                    cr, uid, ids, account, context=context)
            consolidation_modes[cm].append(account)

        period_ids = period_obj.build_ctx_periods(
                cr, uid,
                form.from_period_id.id,
                form.to_period_id.id)

        generic_move_vals = {
            'journal_id': form.journal_id.id,
            'company_id': form.company_id.id,
            'consol_company_id': subsidiary.id,
        }

        ytd_move_ids = []
        period_move_ids = []
        for consolidation_mode, accounts in consolidation_modes.iteritems():
            if not accounts:
                continue

            # get list of periods for which we have to create a move
            # in period mode : a move per period
            # in ytd mode : a move at the last period
            # (which will contains lines from 1st january to last period)
            move_period_ids = (period_ids
                                if consolidation_mode == 'period'
                                else [form.to_period_id.id])

            for move_period_id in move_period_ids:
                period = period_obj.browse(
                        cr, uid, move_period_id, context=context)

                # in ytd we compute the amount from the first
                # day of the fiscal year
                # in period, only for the period
                if consolidation_mode == 'ytd':
                    date_from = period.fiscalyear_id.date_start
                else:
                    date_from = period.date_start
                date_to = period.date_stop

                period_ctx = dict(context, company_id=subsidiary.id)
                compute_from_period_id = period_obj.find(
                        cr, uid, date_from, context=period_ctx)[0]
                compute_to_period_id = period_obj.find(
                        cr, uid, date_to, context=period_ctx)[0]
                compute_period_ids = period_obj.build_ctx_periods(
                        cr, uid,
                        compute_from_period_id,
                        compute_to_period_id)

                # reverse previous entries with flag 'to_be_reversed' (YTD)
                self.reverse_moves(
                        cr, uid,
                        ids,
                        subsidiary.id,
                        form.journal_id.id,
                        date_to,
                        context=context)

                # create the account move
                # at the very last date of the end period
                move_vals = dict(
                        generic_move_vals,
                        ref=_("Consolidation %s") % consolidation_mode,
                        period_id=period.id,
                        date=period.date_stop)
                move_id = move_obj.create(cr, uid, move_vals, context=context)

                # create a move line per account
                for account in accounts:
                    self.consolidate_account(
                            cr, uid, ids,
                            consolidation_mode,
                            compute_period_ids,
                            form.target_move,
                            move_id,
                            account.id,
                            subsidiary.id,
                            context=context)
                self.create_rate_difference_line(
                        cr, uid, ids, move_id, context=context)

                locals()[consolidation_mode + '_move_ids'].append(move_id)

        return ytd_move_ids, period_move_ids

    def run_consolidation(self, cr, uid, ids, context=None):
        """
        Consolidate all selected subsidiaries Virtual Chart of Accounts
        on the Holding Chart of Account

        :return: dict to open an Entries view filtered on the created moves
        """
        super(account_consolidation_consolidate, self).run_consolidation(
                cr, uid, ids, context=context)

        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        move_obj = self.pool.get('account.move')
        form = self.browse(cr, uid, ids[0], context=context)

        move_ids = []
        ytd_move_ids = []
        for subsidiary in form.subsidiary_ids:
            new_move_ids = self.consolidate_subsidiary(
                    cr, uid, ids, subsidiary.id, context=context)
            ytd_move_ids += new_move_ids[0]
            move_ids += sum(new_move_ids, [])

        # YTD moves have to be reversed on the next consolidation
        move_obj.write(
                cr, uid,
                ytd_move_ids,
                {'to_be_reversed': True},
                context=context)

        context.update({'move_ids': move_ids})
        __, action_id = mod_obj.get_object_reference(
                cr, uid, 'account', 'action_move_journal_line')
        action = act_obj.read(cr, uid, [action_id], context=context)[0]
        action['domain'] = unicode([('id', 'in', move_ids)])
        action['name'] = _('Consolidated Entries')
        action['context'] = unicode({'search_default_to_be_reversed': 0})
        return action
