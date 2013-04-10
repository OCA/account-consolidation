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

_logger = logging.getLogger(__name__)

class account_parallel_mapping(orm.TransientModel):

    _name = "account.parallel.mapping"
    
    _columns = {
        'message': fields.text('Message'),
        'remove_old_mapping': fields.boolean('Remove Previous Mapping'),
        }
    
    def do_mapping(self, cr, uid, ids, context=None):
        company_pool = self.pool.get('res.company')
        account_pool = self.pool.get('account.account')
        tax_code_pool = self.pool.get('account.tax.code')
        company_ids = company_pool.search(cr, uid, [])
        wizard =self.browse(cr, uid, ids[0])
        if wizard.remove_old_mapping:
            account_ids = account_pool.search(cr, uid, [])
            account_pool.write(cr, uid, account_ids, {'parallel_account_ids': [(6,0,[])]})
        for company_id in company_ids:
            company = company_pool.browse(cr, uid, company_id)
            if company.parallel_company_ids:
                master_account_ids = account_pool.search(cr, uid, [('company_id', '=', company.id)])
                master_tax_code_ids = tax_code_pool.search(cr, uid, [('company_id', '=', company.id)])
                # account mapping
                for master_account_id in master_account_ids:
                    master_account = account_pool.browse(cr, uid, master_account_id)
                    for parallel_company in company.parallel_company_ids:
                        parallel_account_ids = account_pool.search(cr, uid, [
                            ('code', '=', master_account.code),
                            ('company_id', '=', parallel_company.id),
                            ])
                        if len(parallel_account_ids) > 1:
                            raise orm.except_orm(_('Error'), _('Duplicated account %s for company %s')
                                % (master_account.code,parallel_company.name))
                        elif not parallel_account_ids:
                            raise orm.except_orm(_('Error'), _('No account %s for company %s')
                                % (master_account.code,parallel_company.name))
                        elif len(parallel_account_ids) == 1:
                            master_account.write({'parallel_account_ids':
                                [(4,parallel_account_ids[0])]})
                # tax code mapping
                for master_tax_code_id in master_tax_code_ids:
                    master_tax_code = tax_code_pool.browse(cr, uid, master_tax_code_id)
                    for parallel_company in company.parallel_company_ids:
                        parallel_tax_code_ids = tax_code_pool.search(cr, uid, [
                            ('code', '=', master_tax_code.code),
                            ('company_id', '=', parallel_company.id),
                            ])
                        if len(parallel_tax_code_ids) > 1:
                            raise orm.except_orm(_('Error'), _('Duplicated tax code %s for company %s')
                                % (master_tax_code.code,parallel_company.name))
                        elif not parallel_tax_code_ids:
                            raise orm.except_orm(_('Error'), _('No tax code %s for company %s')
                                % (master_tax_code.code,parallel_company.name))
                        elif len(parallel_tax_code_ids) == 1:
                            master_tax_code.write({'parallel_tax_code_ids':
                                [(4,parallel_tax_code_ids[0])]})
        self.write(cr, uid, ids, {'message': _('Done')})
        return True

