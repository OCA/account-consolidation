# -*- coding: utf-8 -*-
##############################################################################
#    
#    Copyright (C) 2012-2013 Agile Business Group sagl
#    (<http://www.agilebg.com>)
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
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, orm
from tools.translate import _
import logging
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)


class account_account(orm.Model):
    _inherit = "account.account"

    def _get_parallel_accounts_summary(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for account in self.browse(cr, SUPERUSER_ID, ids, context):
            text = 'Configured parallel accounts:\n'
            text2 = ''
            for parallel_account in account.parallel_account_ids:
                text2 += _('Account code: %s. Company: %s\n') % (
                    parallel_account.code, parallel_account.company_id.name)
            if text2:
                res[account.id] = text + text2
            else:
                res[account.id] = _("No parallel accounts found")
        return res

    _columns = {
        'parallel_account_ids': fields.many2many('account.account',
            'parallel_account_rel', 'parent_id',
            'child_id', 'Parallel Currency Accounts',
            Help="""Set here the accounts you want to automatically move when
                registering entries in this account"""),
        'master_parallel_account_ids': fields.many2many('account.account',
            'parallel_account_rel', 'child_id',
            'parent_id', 'Master Parallel Currency Accounts',
            Help="You can see here the accounts that automatically move this account",
            readonly=True),
        'parallel_accounts_summary': fields.function(
            _get_parallel_accounts_summary, type='text',
            string='Parallel accounts summary'),
        }

    def _search_parallel_account(self, cr, uid, account_code, parallel_company,
        context=None):
        parallel_acc_ids = self.search(cr, uid, [
            ('company_id', '=', parallel_company.id),
            ('code', '=', account_code),
            ], context=context)
        if len(parallel_acc_ids) > 1:
            raise orm.except_orm(_('Error'), _('Too many accounts %s for company %s')
                % (account_code, parallel_company.name))
        return parallel_acc_ids and parallel_acc_ids[0] or False

    def _build_account_vals(self, cr, uid, account_vals, parallel_company, context=None):
        # build only fields I need
        vals = {}
        if 'name' in account_vals:
            vals['name'] = account_vals['name']
        if 'code' in account_vals:
            vals['code'] = account_vals['code']
        if 'type' in account_vals:
            vals['type'] = account_vals['type']
        if 'user_type' in account_vals:
            vals['user_type'] = account_vals['user_type']
        if 'active' in account_vals:
            vals['active'] = account_vals['active']
        if 'parent_id' in account_vals:
            parent_account = self.browse(cr, uid, account_vals['parent_id'], context)
            parent_parallel_acc_id = self._search_parallel_account(
                cr, uid, parent_account.code, parallel_company, context=context)
            if not parent_parallel_acc_id:
                raise orm.except_orm(_('Error'),
                    _('No parent account %s found in company %s') %
                    (parent_account.code, parallel_company.name))
            vals['parent_id'] = parent_parallel_acc_id
        return vals

    def create_parallel_accounts(self, cr, uid, ids, context=None):
        for account in self.browse(cr, SUPERUSER_ID, ids, context):
            for parallel_company in account.company_id.parallel_company_ids:
                parent_parallel_acc_id = self._search_parallel_account(
                    cr, SUPERUSER_ID, account.parent_id.code, parallel_company,
                    context=context)
                new_id = self.create(cr, SUPERUSER_ID, {
                    'company_id': parallel_company.id,
                    'parent_id': parent_parallel_acc_id,
                    'name': account.name,
                    'code': account.code,
                    'type': account.type,
                    'user_type': account.user_type and account.user_type.id or False,
                    'active': account.active,
                    })
                cr.execute("insert into parallel_account_rel(parent_id,child_id) values (%d,%d)"
                    % (account.id, new_id))
        return True

    '''
    def sync_parallel_accounts(self, cr, uid, ids, vals={}, context=None):
        for account in self.browse(cr, uid, ids, context):
            new_parallel_acc_ids = []
            company_id = vals.get('company_id') or account.company_id.id
            code = vals.get('code') or account.code
            company = self.pool.get('res.company').browse(cr, uid, company_id, context)
            for parallel_company in company.parallel_company_ids:
                parallel_acc_id = self._search_parallel_account(
                    cr, uid, code, parallel_company, context=context)
                if not parallel_acc_id:
                    # Then I create it, linked to parent account
                    #parallel_acc_id = self.create(cr, uid,
                        #self._build_account_vals(cr, uid,
                        #vals, parallel_company, context=context), context=context)
                    pass
                else:
                    super(account_account,self).write(cr, uid, [parallel_acc_id],
                        self._build_account_vals(cr, uid,
                        vals, parallel_company, context=context), context)
                    _logger.info(
                        _("Parallel account %s (company %s) written") %
                        (code, parallel_company.name))
                new_parallel_acc_ids.append(parallel_acc_id)
        return new_parallel_acc_ids
    '''

    def write(self, cr, uid, ids, vals, context=None):
        if 'parallel_account_ids' not in vals:
            # write/create parallel accounts only if 'parallel_account_ids' not explicity written
            for acc_id in ids:
                account = self.browse(cr, SUPERUSER_ID, acc_id, context)
                for parallel_account in account.parallel_account_ids:
                    parallel_vals = self._build_account_vals(
                        cr, SUPERUSER_ID, vals, parallel_account.company_id,
                        context=context)
                    parallel_account.write(parallel_vals)
        res=super(account_account,self).write(cr, uid, ids, vals, context=context)
        return res
    
    def create(self, cr, uid, vals, context=None):
        res=super(account_account,self).create(cr, uid, vals, context)
        self.create_parallel_accounts(cr, uid, [res], context=None)
        return res
        
    def unlink(self, cr, uid, ids, context=None):
        for account in self.browse(cr, SUPERUSER_ID, ids, context):
            for parallel_account in account.parallel_account_ids:
                parallel_account.unlink()
        res=super(account_account,self).unlink(cr, uid, ids, context=context)
        return res

class account_move(orm.Model):
    _inherit = "account.move"
    
    _columns = {
        'parallel_move_ids': fields.one2many('account.move', 'master_parallel_move_id', 'Parallel Entries',
            readonly=True),
        'master_parallel_move_id': fields.many2one('account.move', 'Master Parallel Entry'),
        }
    
    def button_cancel(self, cr, uid, ids, context=None):
        res = super(account_move, self).button_cancel(cr, uid, ids, context=context)
        for move in self.browse(cr, SUPERUSER_ID, ids, context=context):
            for parallel_move in move.parallel_move_ids:
                parallel_move.button_cancel(context=context)
                parallel_move.unlink(context=context)
        return res

    def lines_balance(self, move_lines):
        """
        returns 0 if lines are balanced, difference if unbalanced
        """
        balance = 0.0
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
        company_pool = self.pool.get('res.company')
        uid = SUPERUSER_ID
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == 'posted' and not move.parallel_move_ids:
                # avoid double post in case of 'Skip Draft State for Manual Entries'
                new_move_lines = []
                parallel_data = {}
                for line in move.line_id:
                    for parallel_account in line.account_id.parallel_account_ids:
                        parallel_data[parallel_account.company_id.id] = {}
                        parallel_data[parallel_account.company_id.id]['move_name'] = line.move_id.name
                        parallel_data[parallel_account.company_id.id]['ref'] = line.move_id.ref
                        parallel_data[parallel_account.company_id.id]['date'] = line.date
                        parallel_data[parallel_account.company_id.id]['move_id'] = line.move_id.id
                            
                        # search period by code and parallel company
                        period_ids = self.pool.get('account.period').search(cr, uid, [
                            ('code','=',line.period_id.code),
                            ('company_id', '=', parallel_account.company_id.id),
                            ])
                            
                        if len(period_ids) == 0:
                            raise orm.except_orm(_('Error !'), _('Period %s does not exist in company %s !')
                                % (line.period_id.code, parallel_account.company_id.name))
                        if len(period_ids) > 1:
                            raise orm.except_orm(_('Error !'), _('Too many periods %s for company %s !')
                                % (line.period_id.code, parallel_account.company_id.name))
                        
                        parallel_data[parallel_account.company_id.id]['period_id'] = period_ids[0]
                        
                        # search parallel journals for the parallel company
                        parallel_journal_ids = []
                        for journal in line.journal_id.parallel_journal_ids:
                            if journal.company_id.id == parallel_account.company_id.id:
                                parallel_journal_ids.append(journal.id)
                        
                        if len(parallel_journal_ids) == 0:
                            raise orm.except_orm(_('Error !'), _('Journal %s does not exist in company %s !')
                                % (line.journal_id.name, parallel_account.company_id.name))
                        if len(parallel_journal_ids) > 1:
                            raise orm.except_orm(_('Error !'), _('Too many journals %s for company %s !')
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
                            
                        parallel_base_amount = amount
                        if parallel_sec_curr_iso_code != parallel_account.company_id.currency_id.name:
                            # only if parallel company currency is != master move currency
                            # search parallel currency by ISO code and parallel company
                            parallel_secondary_curr_ids = curr_pool.search(cr, uid, [
                                ('name', '=', parallel_sec_curr_iso_code),
                                ('company_id', '=', parallel_account.company_id.id),
                                ], context=context)
                                
                            if len(parallel_secondary_curr_ids) == 0:
                                raise orm.except_orm(_('Error !'), _('Currency %s does not exist in company %s !')
                                    % (parallel_sec_curr_iso_code, parallel_account.company_id.name))
                            if len(parallel_secondary_curr_ids) > 1:
                                raise orm.except_orm(_('Error !'), _('Too many currencies %s for company %s !')
                                    % (parallel_sec_curr_iso_code, parallel_account.company_id.name))
                            
                            # compute parallel base amount from document currency, using move date
                            context.update({'date': line.date})
                            parallel_base_amount = curr_pool.compute(cr, uid, parallel_secondary_curr_ids[0],
                                parallel_account.company_id.currency_id.id, amount,
                                context=context)
                            
                            new_line_values['amount_currency'] = amount
                            new_line_values['currency_id'] = parallel_secondary_curr_ids[0]
                            
                        new_line_values['debit'] = 0.0
                        new_line_values['credit'] = 0.0
                        if parallel_base_amount > 0:
                            new_line_values['debit'] = abs(parallel_base_amount)
                        elif parallel_base_amount < 0:
                            new_line_values['credit'] = abs(parallel_base_amount)
                        
                        if line.tax_code_id and line.tax_amount:
                            # search parallel tax codes for the parallel company
                            parallel_tax_code_ids = []
                            for tax_code in line.tax_code_id.parallel_tax_code_ids:
                                if tax_code.company_id.id == parallel_account.company_id.id:
                                    parallel_tax_code_ids.append(tax_code.id)
                            
                            if len(parallel_tax_code_ids) == 0:
                                raise orm.except_orm(_('Error !'), _('Tax code %s does not exist in company %s !')
                                    % (line.tax_code_id.name, parallel_account.company_id.name))
                            if len(parallel_tax_code_ids) > 1:
                                raise orm.except_orm(_('Error !'), _('Too many tax_codes %s for company %s !')
                                    % (line.tax_code_id.name, parallel_account.company_id.name))
                            
                            new_line_values['tax_code_id'] = parallel_tax_code_ids[0]
                            total_tax = new_line_values['debit'] - new_line_values['credit']
                            new_line_values['tax_amount'] = line.tax_amount < 0 \
                                and - abs(total_tax) \
                                or line.tax_amount > 0 \
                                and abs(total_tax) \
                                or 0.0
                        
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
                    self.create(cr, uid, move_values, context=context)
                    # self.post(cr, uid, [move_id], context=context)
                
        return res


class account_journal(orm.Model):
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

class account_tax_code(orm.Model):
    _inherit = "account.tax.code"

    def _get_parallel_tax_codes_summary(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for tax_code in self.browse(cr, SUPERUSER_ID, ids, context):
            text='Configured parallel tax codes:\n'
            text2=''
            for parallel_tax_code in tax_code.parallel_tax_code_ids:
                text2+= _('Tax code: %s. Company: %s\n') % (
                    parallel_tax_code.code, parallel_tax_code.company_id.name)
            if text2:
                res[tax_code.id] = text + text2
            else:
                res[tax_code.id] = _("No parallel tax codes found")
        return res
    
    _columns = {
        'parallel_tax_code_ids': fields.many2many('account.tax.code',
            'parallel_tax_code_rel', 'parent_id',
            'child_id', 'Parallel Currency Tax Codes',
            Help="Set here the tax codes you want to automatically move when registering entries in this tax code"),
        'master_parallel_tax_code_ids': fields.many2many('account.tax.code',
            'parallel_tax_code_rel', 'child_id',
            'parent_id', 'Master Parallel Currency Tax Codes',
            Help="You can see here the tax codes that automatically move this journal", readonly=True),
        'parallel_tax_codes_summary': fields.function(_get_parallel_tax_codes_summary, type='text', string='Parallel tax codes summary'),
        }
    
    def _search_parallel_tax_code(self, cr, uid, tax_code, parallel_company,
        context=None):
        parallel_tax_code_ids = self.search(cr, uid, [
                ('company_id','=', parallel_company.id),
                ('code','=', tax_code),
                ], context=context)
        if len(parallel_tax_code_ids) > 1:
            raise orm.except_orm(_('Error'), _('Too many tax codes %s for company %s')
                    % (tax_code,parallel_company.name))
        return parallel_tax_code_ids and parallel_tax_code_ids[0] or False
    
    def _build_tax_code_vals(self, cr, uid, tax_code_vals, parallel_company, context=None):
        # build only fields I need
        vals={}
        if tax_code_vals.has_key('name'):
            vals['name'] = tax_code_vals['name']
        if tax_code_vals.has_key('code'):
            vals['code'] = tax_code_vals['code']
        if tax_code_vals.has_key('type'):
            vals['type'] = tax_code_vals['type']
        if tax_code_vals.has_key('user_type'):
            vals['user_type'] = tax_code_vals['user_type']
        if tax_code_vals.has_key('active'):
            vals['active'] = tax_code_vals['active']
        if tax_code_vals.has_key('parent_id'):
            parent_tax_code = self.browse(cr, uid, tax_code_vals['parent_id'], context)
            parent_parallel_acc_id = self._search_parallel_tax_code(
                cr, uid, parent_tax_code.code, parallel_company, context=context)
            if not parent_parallel_acc_id:
                raise orm.except_orm(_('Error'),
                    _('No parent tax code %s found in company %s') %
                    (parent_tax_code.code, parallel_company.name))
            vals['parent_id'] = parent_parallel_acc_id
        return vals
    
    def create_parallel_tax_codes(self, cr, uid, ids, context=None):
        for tax_code in self.browse(cr, SUPERUSER_ID, ids, context):
            for parallel_company in tax_code.company_id.parallel_company_ids:
                if not tax_code.parent_id:
                    raise orm.except_orm(_('Error'),_('Tax code %s does not have parent')
                        % tax_code.code)
                existing_ids = self.search(cr, SUPERUSER_ID, [
                    ('code', '=', tax_code.code),
                    ('company_id', '=', parallel_company.id),
                    ])
                if existing_ids:
                    raise orm.except_orm(_('Error'),
                    _('Tax code %s already exists for company %s')
                    % (tax_code.code, parallel_company.name))
                parent_parallel_tax_code_id = self._search_parallel_tax_code(
                    cr, SUPERUSER_ID, tax_code.parent_id.code, parallel_company,
                    context=context)
                new_id = self.create(cr, SUPERUSER_ID,{
                    'company_id': parallel_company.id,
                    'parent_id': parent_parallel_tax_code_id,
                    'name': tax_code.name,
                    'code': tax_code.code,
                    'notprintable': tax_code.notprintable,
                    'sign': tax_code.sign,
                    'info': tax_code.info,
                    })
                cr.execute(
                    "insert into parallel_tax_code_rel(parent_id,child_id) values (%d,%d)"
                    % (tax_code.id,new_id))
        return True

    def write(self, cr, uid, ids, vals, context=None):
        if not vals.has_key('parallel_tax_code_ids'):
            # write/create parallel tax codes only if 'parallel_tax_code_ids' not explicity written
            for tax_code_id in ids:
                tax_code = self.browse(cr, SUPERUSER_ID, tax_code_id, context)
                for parallel_tax_code in tax_code.parallel_tax_code_ids:
                    parallel_vals = self._build_tax_code_vals(
                        cr, SUPERUSER_ID, vals, parallel_tax_code.company_id, context=context)
                    parallel_tax_code.write(parallel_vals)
        res=super(account_tax_code,self).write(cr, uid, ids, vals, context=context)
        return res
    
    def create(self, cr, uid, vals, context=None):
        res=super(account_tax_code,self).create(cr, uid, vals, context)
        self.create_parallel_tax_codes(cr, uid, [res], context=None)
        return res
