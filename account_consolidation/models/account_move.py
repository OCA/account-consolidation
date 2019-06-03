# Copyright 2011-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from lxml import etree

from odoo import models, fields, api


class AccountMove(models.Model):

    _inherit = 'account.move'

    consol_company_id = fields.Many2one(
        comodel_name='res.company',
        string='Consolidated from Company',
        readonly=True
    )

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                         submenu=False):
        """Hide fields `consol_company_id` if the user is not connected to
        a consolidation company."""
        res = super()._fields_view_get(
            view_id, view_type, toolbar, submenu
        )
        if view_type == 'form':
            xml = etree.fromstring(res['arch'])
            node = xml.find(".//tree//field[@name='consol_company_id']")
            if node is not None:
                node.set('attrs', str({
                    'column_invisible':
                        not self.env.user.company_id.is_consolidation
                }))
                res['arch'] = etree.tostring(xml)
        return res

    @api.multi
    def post(self):
        """Bypass move posting when reversing consolidation moves"""
        if self.env.context.get('__conso_reversal_no_post'):
            return True
        return super().post()


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    consol_company_id = fields.Many2one(
        comodel_name='res.company',
        related='move_id.consol_company_id',
        string='Consolidated from',
        store=True,  # for the group_by
        readonly=True
    )
    consol_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Intercompany Partner',
        readonly=True
    )
    consolidated = fields.Boolean(default=False)

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                         submenu=False):
        """Hide fields `consol_company_id` and `consol_partner_id` if the
        user is not connected to a consolidation company."""
        res = super()._fields_view_get(
            view_id, view_type, toolbar, submenu
        )

        if view_id == self.env.ref('account.view_move_line_tree').id:
            xml = etree.fromstring(res['arch'])
            company_node = xml.find(".//field[@name='consol_company_id']")
            if company_node is not None:
                company_node.set('attrs', str({
                    'column_invisible':
                        not self.env.user.company_id.is_consolidation
                }))
            partner_node = xml.find(".//field[@name='consol_partner_id']")
            if partner_node is not None:
                partner_node.set('attrs', str({
                    'column_invisible':
                        not self.env.user.company_id.is_consolidation
                }))
            res['arch'] = etree.tostring(xml)

        return res
