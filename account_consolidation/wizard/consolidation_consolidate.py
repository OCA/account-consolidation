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


class account_consolidation_consolidate(osv.osv_memory):
    _name = 'account.consolidation.consolidate'
    _inherit = 'account.consolidation.base'

    _columns = {
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),
        'gain_account_id': fields.many2one('account.account', 'Gain Account', required=True,),
        'loss_account_id': fields.many2one('account.account', 'Loss Account', required=True,),
        'target_move': fields.selection([('posted', 'All Posted Entries'),
                                         ('all', 'All Entries'),
                                        ], 'Target Moves', required=True),
    }

    _defaults = {
        'target_move': 'posted'
    }

    def _currency_rate_type(self, cr, uid, ids, account, context=None):
        """ account is a browse instance of account.account
            Returns the currency rate type to use
        """
        return account.consolidation_rate_type or account.user_type.consolidation_rate_type

    def _consolidation_mode(self, cr, uid, ids, account, context=None):
        """ account is a browse instance of account.account
            Returns the consolidation mode to use
        """
        return account.consolidation_mode or account.user_type.consolidation_mode

    def _periods_holding_to_subsidiary(self, cr, uid, ids, period_ids, subsidiary_id, context=None):
        period_obj = self.pool.get('account.period')
        if isinstance(period_ids, (int, long)):
            period_ids = [period_ids]
        subs_period_ids = []
        for period in period_obj.browse(cr, uid, period_ids, context=context):
            subs_period_ids.extend(period_obj.search(cr, uid,
                [('date_start', '=', period.date_start),
                 ('date_stop', '=', period.date_stop),
                 ('company_id', '=', subsidiary_id)])
            )
        return subs_period_ids

    def create_rate_difference_line(self, cr, uid, ids, move_id, context):
        # see account/account.py:1390 ?
        pass

    def consolidate_account(self, cr, uid, ids, consolidation_mode, holding_period_ids, state, move_id,
                            holding_account_id, subsidiary_id, context=None):
        """ Consolidates the subsidiary account on the holding account
            Creates move lines on the move with id "move_id"
        """
        form = self.browse(cr, uid, ids[0], context=context)
        account_obj = self.pool.get('account.account')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')

        move = move_obj.browse(cr, uid, move_id, context=context)
        holding_account = account_obj.browse(cr, uid, holding_account_id, context=context)

        # [0] because only one account per company for one code is permitted
        # if no subsidiary account has been found, it means that the checks have not been runned
        # or the code of the checks is defective
        subsidiary_account_id = account_obj.search(cr, uid, [('code', '=', holding_account.code),
                                                             ('company_id', '=', subsidiary_id)],
                                                   context=context)[0]

        if not subsidiary_account_id:
            return []  # an account may exist on the holding and not in the subsidiaries, nothing to do

        subs_period_ids = self._periods_holding_to_subsidiary(cr, uid, ids, holding_period_ids,
                                                              subsidiary_id, context=context)

        browse_ctx = context.copy()
        browse_ctx.update({
            'state': state,
            'periods': subs_period_ids,
        })
        subs_account = account_obj.browse(cr, uid, subsidiary_account_id, context=browse_ctx)

        vals = {
            'name': _("Consolidation line in %s mode") % (consolidation_mode,),
            'account_id': holding_account.id,
            'move_id': move.id,
            'journal_id': move.journal_id.id,
            'period_id': move.period_id.id,
            'company_id': move.company_id.id,
        }

        if holding_account.company_currency_id.id != subs_account.company_currency_id.id:
            # TODO use currency rate type spot or average, waiting for OpenERP implementation
            currency_rate_type = self._currency_rate_type(cr, uid, ids, holding_account, context=context)

            amount_type = subs_account.debit and 'debit' or 'credit'
            subs_amount = getattr(subs_account, amount_type)
            amount_curr = currency_obj.compute(cr, uid,
                                               subs_account.company_currency_id.id,
                                               holding_account.company_currency_id.id,
                                               subs_amount,
                                               context=context)
            vals.update({
                amount_type: amount_curr,
                'currency_id': subs_account.company_currency_id.id,
                'amount_currency': subs_account.balance,
            })
        else:
            vals.update({
                'debit': subs_account.debit,
                'credit': subs_account.credit,
            })

        move_line_id = move_line_obj.create(cr, uid, vals, context=context)

        return move_line_id

    def consolidate_subsidiary(self, cr, uid, ids, subsidiary_chart_id, context=None):
        """ Consolidate a subsidiary on the Holding.
            Create a move per subsidiary and consolidation type (YTD/Period)
            and an move line per account of the subsidiary
            Plus a move line for the currency gain / loss
        """
        context = context or {}
        subsidiary_chart_obj = self.pool.get('account.consolidation.subsidiary_chart')
        move_obj = self.pool.get('account.move')
        period_obj = self.pool.get('account.period')
        form = self.browse(cr, uid, ids[0], context=context)
        subsidiary_chart = subsidiary_chart_obj.browse(cr, uid, subsidiary_chart_id, context=None)
        subs_company = subsidiary_chart.company_id

        data_ctx = context.copy()
        data_ctx.update({'holding_coa': True})
        holding_accounts_data = self._chart_accounts_data(cr, uid, ids, subsidiary_chart.chart_account_id.id, context=data_ctx)
        holding_accounts = [values['browse'] for key, values in holding_accounts_data.iteritems()]

        # split accounts in ytd and periods modes
        consolidation_modes = {'ytd': [], 'period': []}
        for account in holding_accounts:
            cm = self._consolidation_mode(cr, uid, ids, account, context=context)
            consolidation_modes[cm].append(account)

        period_ids = period_obj.build_ctx_periods(cr, uid, form.from_period_id.id, form.to_period_id.id)

        move_ids = []
        generic_move_vals = {
            'journal_id': form.journal_id.id,
            'company_id': form.company_id.id,
            'consol_company_id': subs_company.id,
        }
        for consolidation_mode, accounts in consolidation_modes.iteritems():
            if not accounts:
                continue

            # get list of periods for which we have to create a move
            # in period mode : a move per period
            # in ytd mode : a move at the last period (which will contains lines from first period to last period)
            move_period_ids = consolidation_mode == 'period' \
                              and period_ids \
                              or [form.to_period_id.id]
            for move_period_id in move_period_ids:
                period = period_obj.browse(cr, uid, move_period_id, context=context)

                # TODO in YTD: reverse previous entries

                # TODO if moves found for the same period : skip ?

                # create the account move
                # at the very last date of the end period
                move_vals = generic_move_vals.copy()
                move_vals.update({
                    'name': _("Consolidation %s") % (consolidation_mode,),
                    'ref': _("Consolidation %s") % (consolidation_mode,),
                    'period_id': period.id,
                    'date': period.date_stop,
                    'account_journal_reversal': consolidation_mode == 'ytd',
                })
                move_id = move_obj.create(cr, uid, move_vals, context=context)

                # for the move lines, in ytd mode we create move lines for all periods
                move_line_period_ids = consolidation_mode == 'period' \
                                       and [move_period_id] \
                                       or period_ids

                # create a move line per account
                for account in accounts:
                    self.consolidate_account(cr, uid, ids,
                                             consolidation_mode,
                                             move_line_period_ids,
                                             form.target_move,
                                             move_id,
                                             account.id,
                                             subs_company.id,
                                             context=context)

                # TODO calculate currency rate difference (all move lines debit - all move lines credit) and post a move line
                # on the gain / loss account
                # will works IF : counterparts are always configured with the same mode (YTD/Periods)
                self.create_rate_difference_line(cr, uid, ids,
                                                 move_id, context=context)


                move_ids.append(move_id)

        return move_ids

    def run_consolidation(self, cr, uid, ids, context=None):
        """

        """
        super(account_consolidation_consolidate, self).run_consolidation(cr, uid, ids, context=context)

        mod_obj = self.pool.get('ir.model.data')
        form = self.browse(cr, uid, ids[0], context=context)

        move_ids = []
        for subsidiary_chart in form.subsidiary_chart_ids:
            move_ids = self.consolidate_subsidiary(cr, uid, ids, subsidiary_chart.id, context=context)

        context.update({'move_ids': move_ids})
        model_data_ids = mod_obj.search(cr, uid, [('model', '=', 'ir.ui.view'),
                                                  ('name', '=', 'view_move_form')],
                                        context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        return {
            'domain': "[('id','in', [" + ','.join([str(move_id) for move_id in move_ids]) + "])]",
            'name': 'Entries',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [(False, 'tree'), (resource_id, 'form')],
            'type': 'ir.actions.act_window',
        }

account_consolidation_consolidate()
