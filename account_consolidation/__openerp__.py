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

{
     "name" : "Account Consolidation",
     "version" : "0.0",
     "author" : "Camptocamp",
     'license': 'AGPL-3',
     "category" : "Generic Modules/Accounting",
     "description":
"""
Account consolidation module. Coding in progress...

Some explanations to do...

 - Difference between debit/credit is balanced on the debit/credit default account of the journal?
""",
     "website": "http://www.camptocamp.com",
     "depends" : [
         'base',
         'account',
         'account_reversal',
     ],
     "init_xml" : [],
     "demo_xml" : [
         'demo/consolidation_demo.xml',
         'demo/chart_a_demo.xml',
         'demo/chart_b_demo.xml',
         ],
     "update_xml" : [
         'company_view.xml',
         'account_view.xml',
         'wizard/consolidation_check_view.xml',
         'wizard/consolidation_consolidate_view.xml',
         'consolidation_menu.xml',
     ],
    'test': [
        'test/test_data.yml',
        'test/consolidation_checks.yml',
        'test/consolidation_consolidate.yml',
            ],
     "active": False,
     "installable": False,
}
