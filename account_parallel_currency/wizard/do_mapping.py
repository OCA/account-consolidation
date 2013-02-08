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

from osv import fields,osv
from tools.translate import _

class account_parallel_mapping(osv.osv_memory):

    _name = "account.parallel.mapping"
    
    _columns = {
        'message': fields.text('Message'),
        'remove_old_mapping': fields.boolean('Remove Previous Mapping'),
        }
    
    def do_mapping(self, cr, uid, ids, context=None):
        company_pool = self.pool.get('res.company')
        account_pool = self.pool.get('account.account')
        company_ids = company_pool.search(cr, uid, [])
        wizard =self.browse(cr, uid, ids[0])
        if wizard.remove_old_mapping:
            account_ids = account_pool.search(cr, uid, [])
            account_pool.write(cr, uid, account_ids, {'parallel_account_ids': [(6,0,[])]})
        for company_id in company_ids:
            company = company_pool.browse(cr, uid, company_id)
            if company.parallel_company_ids:
                master_account_ids = account_pool.search(cr, uid, [('company_id', '=', company.id)])
                for master_account_id in master_account_ids:
                    master_account = account_pool.browse(cr, uid, master_account_id)
                    for parallel_company in company.parallel_company_ids:
                        parallel_account_ids = account_pool.search(cr, uid, [
                            ('code', '=', master_account.code),
                            ('company_id', '=', parallel_company.id),
                            ])
                        if len(parallel_account_ids) > 1:
                            raise osv.except_osv(_('Error'), _('Duplicated account %s for company %s')
                                % (master_account.code,parallel_company.name))
                        elif not parallel_account_ids:
                            print _('No account %s for company %s') % (master_account.code,parallel_company.name)
                        elif len(parallel_account_ids) == 1:
                            master_account.write({'parallel_account_ids':
                                [(4,parallel_account_ids[0])]})
        self.write(cr, uid, ids, {'message': _('Done')})
        return True
        
account_parallel_mapping()
