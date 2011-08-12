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

    def _account_type_rate_types(self, cr, uid, ids, context=None):
        """ Get all the rate types of the account types to
            avoid read them at each account computation
        """
        res = {}
        acc_type_obj = self.pool.get('account.account.type')
        ids = acc_type_obj.search(cr, uid, [])
        rate_types = acc_type_obj.read(cr, uid, ids, ['id', 'consolidation_rate_type'], context)
        for rt in rate_types:
            res[rt['id']] = rt['consolidation_rate_type']
        return res

    def _get_account_rate_type(self, cr, uid, ids, account_id, context=None):
        """ Returns the account's rate type if defined on account otherwise
            returns the account type's rate type.
        """
        account_obj = self.pool.get('account.account')
        acc_type_obj = self.pool.get('account.account.type')
        ids = acc_type_obj.search(cr, uid, [])
        res = acc_type_obj.read(cr, uid, ids, ['code', 'name'], context=context)
        return [(r['code'], r['name']) for r in res]

    def consolidate_account(self, cr, uid, ids, context=None):
        pass

    def consolidate_subsidiary(self, cr, uid, ids, subsidiary_chart_id, context=None):
        subsidiary_chart_obj = self.pool.get('account.consolidation.subsidiary_chart')

        form = self.browse(cr, uid, ids[0], context=context)
        subsidiary_chart = subsidiary_chart_obj.browse(cr, uid, subsidiary_chart_id, context=None)

        # store account types rate types to not read them each time
        account_type_rate_types = self._account_type_rate_types(cr, uid, ids, context=context)



        import pdb; pdb.set_trace()
        
        return True

    def _holding_accounts_data(self, cr, uid, ids, context=None):
        form = self.browse(cr, uid, ids[0], context=context)
        

        return


    def run_consolidation(self, cr, uid, ids, context=None):
        """

        """
        super(account_consolidation_consolidate, self).run_consolidation(cr, uid, ids, context=context)
        form = self.browse(cr, uid, ids[0], context=context)

        for subsidiary_chart in form.subsidiary_chart_ids:
            self.consolidate_subsidiary(cr, uid, ids, subsidiary_chart.id, context=context)

        return {'type': 'ir.actions.act_window_close'}

account_consolidation_consolidate()
