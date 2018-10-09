# Copyright 2011-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Consolidation",
    "version": "11.0.1.0.0",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Generic Modules/Accounting",
    "website": "https://github.com/OCA/account-consolidation",
    "depends": [
        'account_reversal',
        'currency_monthly_rate',
        'l10n_generic_coa',
    ],
    "data": [
        'security/res_groups.xml',
        'security/account_consolidation_security.yml',
        'security/account_consolidation_security.xml',
        'security/ir.model.access.csv',
        'views/account_move_line_view.xml',
        'views/res_config_settings.xml',
        'views/account_view.xml',
        'views/account_consolidation_profile.xml',
        'wizard/consolidation_check_view.xml',
        'wizard/consolidation_consolidate_view.xml',
        'views/consolidation_menu.xml',
    ],
    "demo": [
        'demo/company_demo.xml',
        'demo/currency_demo.xml',
        'demo/consolidation_demo.xml',
        'demo/company_a_demo.xml',
        'demo/company_b_demo.xml',
    ],
    "installable": True,
}
