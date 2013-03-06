# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi Guewen Baconnier
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


class AccountMoveLine(orm.Model):
    _inherit = 'account.move.line'

    def _current_company(self, cursor, uid, ids, name, args, context=None):
        company_id = self.pool['res.company']._company_default_get(cursor, uid)
        curr_ids = self.search(cursor, uid, [('company_id', '=', company_id)])
        res = dict([(tid, tid in curr_ids) for tid in ids])
        return res


    def search_is_current_company(self, cursor, uid, obj, name, args, context=None):
        company_id = self.pool['res.company']._company_default_get(cursor, uid)
        res = self.search(cursor, uid, [('company_id', '=', company_id)])
        return [('id', 'in', res)]

    _columns = {'consol_company_id': fields.related('move_id', 'consol_company_id',
                                                    relation='res.company',
                                                    type="many2one",
                                                    string='Subsidaries',
                                                    store=True,  # for the group_by
                                                    readonly=True),

                'is_current_company': fields.function(_current_company,
                                                      string="Current company",
                                                      type="boolean",
                                                      fnct_search=search_is_current_company)
                }
