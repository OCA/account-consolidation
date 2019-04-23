# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, SUPERUSER_ID


def disable_rule(cr, registry):
    """disable rule for multicompanies so consolidation manager can access
    account, earlier was done in yml """
    env = api.Environment(cr, SUPERUSER_ID, {})
    rule = env.ref('account.account_comp_rule')
    rule.active = False


def post_init(cr, registry):
    disable_rule(cr, registry)
