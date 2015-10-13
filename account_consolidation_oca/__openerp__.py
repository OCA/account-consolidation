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
{"name": "Account Consolidation",
 "version": "1.0",
 "author": "Camptocamp,Odoo Community Association (OCA)",
 "license": "AGPL-3",
 "category": "Generic Modules/Accounting",
 "description": """
Account consolidation
=====================

Introduction
------------

Consolidate chart of accounts on subsidiaries
in a virtual chart of accounts of the holding.

Installation
------------
The `account_reversal` module is required,
it can be found on the account-financial-tools_
project

.. _account-financial-tools: https://launchpad.net/account-financial-tools""",

 "website": "http://www.camptocamp.com",
 "depends": ['base',
             'account',
             'account_reversal',  # TODO check account_constraints compat.
             ],

 "demo_xml": ['demo/consolidation_demo.xml',
              'demo/chart_a_demo.xml',
              'demo/chart_b_demo.xml',
              ],

 "data": ['data.xml',
          'account_move_line_view.xml',
          'company_view.xml',
          'account_view.xml',
          'wizard/consolidation_check_view.xml',
          'wizard/consolidation_consolidate_view.xml',
          'consolidation_menu.xml',
          'analysis_view.xml'
          ],

 "test": ['test/test_data.yml',
          'test/consolidation_checks.yml',
          'test/consolidation_consolidate.yml',
          ],

 "active": False,
 'installable': False,
 }
