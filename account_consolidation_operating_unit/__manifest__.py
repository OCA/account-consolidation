# Copyright 2011-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Consolidation Operating Unit",
    "version": "11.0.1.0.0",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Generic Modules/Accounting",
    "website": "https://github.com/OCA/account-consolidation",
    "depends": [
        'account_consolidation',
        'account_operating_unit',
    ],
    "data": [
        'security/account_consolidation_security.yml',
        'security/account_consolidation_security.xml',
        'views/account_move_line.xml',
        'views/consolidation_profile.xml',
    ],
    "installable": True,
}
