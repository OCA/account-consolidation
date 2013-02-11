# -*- coding: utf-8 -*-
##############################################################################
#    
#    Copyright (C) 2012 Agile Business Group sagl (<http://www.agilebg.com>)
#    Copyright (C) 2012 Domsense srl (<http://www.domsense.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from tools.translate import _
import time

class account_account(osv.osv):
    _inherit = "account.account"
    
    _columns = {
        'parallel_account_ids': fields.many2many('account.account',
            'parallel_account_rel', 'parent_id',
            'child_id', 'Parallel Currency Accounts',
            Help="Set here the accounts you want to automatically move when registering entries in this account"),
        'master_parallel_account_ids': fields.many2many('account.account',
            'parallel_account_rel', 'child_id',
            'parent_id', 'Master Parallel Currency Accounts',
            Help="You can see here the accounts that automatically move this account", readonly=True),
        }


#and tax codes?
class account_move(osv.osv):
    _inherit = "account.move"
    
    _columns = {
        'parallel_move_ids': fields.one2many('account.move', 'master_parallel_move_id', 'Parallel Entries',
            readonly=True),
        'master_parallel_move_id': fields.many2one('account.move', 'Master Parallel Entry'),
        }
    
    def button_cancel(self, cr, uid, ids, context=None):
        res = super(account_move, self).button_cancel(cr, uid, ids, context=context)
        for move in self.browse(cr, uid, ids, context=context):
            for parallel_move in move.parallel_move_ids:
                parallel_move.button_cancel(context=context)
                parallel_move.unlink(context=context)
        return res

    def lines_balance(self, move_lines):
        """
        returns 0 if lines are balanced, difference if unbalanced
        """
        balance = 0.0
        curr_pool = self.pool.get('res.currency')
        for line_tuple in move_lines:
            balance += line_tuple[2]['debit'] or (- line_tuple[2]['credit']) or 0.0
        return balance
        
    def balance_lines(self, cr, uid, move_lines, currency_id, context=None):
        """
        Balance move lines that were unbalanced due to roundings.
        """
        balance = self.lines_balance(move_lines)
        acc_pool = self.pool.get('account.account')
        curr_pool = self.pool.get('res.currency')
        if curr_pool.is_zero(cr, uid, curr_pool.browse(cr, uid, currency_id), balance):
            return move_lines
        else:
            found = False
            for line_tuple in move_lines:
                account = acc_pool.browse(cr, uid, line_tuple[2]['account_id'], context)
                # search for liquidity, receivable or payable accounts
                # beacause usually they are the result of operations (invoice total).
                # So, if we made the invoice in parallel currency, we'd get that different invoice total
                if account.type == 'liquidity' or account.type == 'receivable' or account.type == 'payable':
                    if line_tuple[2]['debit']:
                        line_tuple[2]['debit'] -= balance
                        found = True
                        break
                    elif line_tuple[2]['credit']:
                        line_tuple[2]['credit'] += balance
                        found = True
                        break
            if not found:
                # if no liquidity, receivable or payable accounts are present, we use the first line (randomly).
                # TODO check if this makes sense
                if move_lines[0][2]['debit']:
                    move_lines[0][2]['debit'] -= balance
                elif move_lines[0][2]['credit']:
                    move_lines[0][2]['credit'] += balance
            return move_lines

    def post(self, cr, uid, ids, context=None):
        res = super(account_move, self).post(cr, uid, ids, context=context)
        if context is None:
            context = {}
        curr_pool = self.pool.get('res.currency')
        user_pool = self.pool.get('res.users')
        company_pool = self.pool.get('res.company')
        user = user_pool.browse(cr, uid, uid, context=context)
        if user.parallel_user_id:
            uid = user.parallel_user_id.id
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == 'posted':
                new_move_lines = []
                parallel_data = {}
                for line in move.line_id:
                    for parallel_account in line.account_id.parallel_account_ids:
                        parallel_data[parallel_account.company_id.id] = {}
                        parallel_data[parallel_account.company_id.id]['move_name'] = line.move_id.name
                        parallel_data[parallel_account.company_id.id]['ref'] = line.move_id.ref
                        parallel_data[parallel_account.company_id.id]['date'] = line.date
                        parallel_data[parallel_account.company_id.id]['move_id'] = line.move_id.id
                            
                        # search period by move date and parallel company
                        period_ids = self.pool.get('account.period').search(cr, uid, [
                            ('date_start','<=',line.date),
                            ('date_stop','>=',line.date ),
                            ('company_id', '=', parallel_account.company_id.id)])
                            
                        if len(period_ids) == 0:
                            raise osv.except_osv(_('Error !'), _('Period %s does not exist in company %s !')
                                % (line.date, parallel_account.company_id.name))
                        if len(period_ids) > 1:
                            raise osv.except_osv(_('Error !'), _('Too many periods %s for company %s !')
                                % (line.date, parallel_account.company_id.name))
                        
                        parallel_data[parallel_account.company_id.id]['period_id'] = period_ids[0]
                        
                        # search parallel journals for the parallel company
                        parallel_journal_ids = []
                        for journal in line.journal_id.parallel_journal_ids:
                            if journal.company_id.id == parallel_account.company_id.id:
                                parallel_journal_ids.append(journal.id)
                        
                        if len(parallel_journal_ids) == 0:
                            raise osv.except_osv(_('Error !'), _('Journal %s does not exist in company %s !')
                                % (line.journal_id.name, parallel_account.company_id.name))
                        if len(parallel_journal_ids) > 1:
                            raise osv.except_osv(_('Error !'), _('Too many journals %s for company %s !')
                                % (line.journal_id.name, parallel_account.company_id.name))
                        
                        parallel_data[parallel_account.company_id.id]['journal_id'] = parallel_journal_ids[0]

                        new_line_values = {
                            'name': line.name,
                            'date_maturity': line.date_maturity or False,
                            'account_id': parallel_account.id,
                            'period_id': period_ids[0],
                            'journal_id': parallel_journal_ids[0],
                            'company_id': parallel_account.company_id.id,
                            'partner_id': line.partner_id and line.partner_id.id or False,
                            }

                        if line.currency_id and line.amount_currency:
                            parallel_sec_curr_iso_code = line.currency_id.name
                            amount = line.amount_currency
                        else:
                            parallel_sec_curr_iso_code = line.company_id.currency_id.name
                            amount = line.debit or ( - line.credit)
                            
                        # search parallel currency by ISO code and parallel company
                        parallel_secondary_curr_ids = curr_pool.search(cr, uid, [
                            ('name', '=', parallel_sec_curr_iso_code),
                            ('company_id', '=', parallel_account.company_id.id),
                            ], context=context)
                            
                        if len(parallel_secondary_curr_ids) == 0:
                            raise osv.except_osv(_('Error !'), _('Currency %s does not exist in company %s !')
                                % (parallel_sec_curr_iso_code, parallel_account.company_id.name))
                        if len(parallel_secondary_curr_ids) > 1:
                            raise osv.except_osv(_('Error !'), _('Too many currencies %s for company %s !')
                                % (parallel_sec_curr_iso_code, parallel_account.company_id.name))
                        
                        # compute parallel base amount from document currency, using move date
                        context.update({'date': line.date})
                        parallel_base_amount = curr_pool.compute(cr, uid, parallel_secondary_curr_ids[0],
                            parallel_account.company_id.currency_id.id, amount,
                            context=context)
                            
                        new_line_values['amount_currency'] = amount or False
                        new_line_values['currency_id'] = parallel_secondary_curr_ids[0]
                        new_line_values['debit'] = 0.0
                        new_line_values['credit'] = 0.0
                        if parallel_base_amount > 0:
                            new_line_values['debit'] = abs(parallel_base_amount)
                        elif parallel_base_amount < 0:
                            new_line_values['credit'] = abs(parallel_base_amount)
                        
                        new_move_lines.append((parallel_account.company_id.id, (0,0,new_line_values)))
                        #parallel_data[parallel_account.company_id.id]['move_lines'].append((0,0,new_line_values))
                        
                for company_id in parallel_data:
                    move_lines = []
                    for new_move_line in new_move_lines:
                        if new_move_line[0] == company_id:
                            move_lines.append(new_move_line[1])
                    move_lines=self.balance_lines(cr, uid, move_lines, company_pool.browse(cr, uid, company_id).currency_id.id, context=context)
                    move_values = {
                        'name': parallel_data[company_id]['move_name'],
                        'period_id': parallel_data[company_id]['period_id'],
                        'journal_id': parallel_data[company_id]['journal_id'],
                        'date': parallel_data[company_id]['date'],
                        'company_id': company_id,
                        'line_id': move_lines,
                        'master_parallel_move_id': parallel_data[company_id]['move_id'],
                        'ref': parallel_data[company_id]['ref'],
                        }
                    move_id = self.create(cr, uid, move_values, context=context)
                    self.post(cr, uid, [move_id], context=context)
                
        return res


class account_journal(osv.osv):
    _inherit = "account.journal"
    
    _columns = {
        'parallel_journal_ids': fields.many2many('account.journal',
            'parallel_journal_rel', 'parent_id',
            'child_id', 'Parallel Currency Journals',
            Help="Set here the journals you want to automatically move when registering entries in this journal"),
        'master_parallel_journal_ids': fields.many2many('account.journal',
            'parallel_journal_rel', 'child_id',
            'parent_id', 'Master Parallel Currency Journals',
            Help="You can see here the journals that automatically move this journal", readonly=True),
        }
