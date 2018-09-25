# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import time
from odoo.addons.account_consolidation.tests.\
    test_account_consolidation import TestAccountConsolidation
from odoo import fields


class TestAccountConsolidationOperatingUnit(TestAccountConsolidation):

    def test_consolidation_jan_with_operating_unit(self):
        # Get operating units
        ou_b2b = self.env.ref('operating_unit.b2b_operating_unit')
        ou_b2c = self.env.ref('operating_unit.b2c_operating_unit')
        # Activate operating unit distinction on subsidiary A
        subA_profile = self.env.ref('account_consolidation.conso_sub_a')
        subA_profile.distinct_operating_units = True
        self.env['account.move'].create({
            'journal_id': self.op_journal_subsidiary_a.id,
            'company_id': self.subsidiary_a.id,
            'ref': '/',
            'date': fields.Date.from_string('%s-01-26' % time.strftime('%Y')),
            'line_ids': [
                (0, 0, {
                    'account_id': self.env.ref(
                        'account_consolidation.subA_rec1').id,
                    'company_id': self.subsidiary_a.id,
                    'debit': 100,
                    'credit': 0,
                    'operating_unit_id': ou_b2b.id
                }), (0, 0, {
                    'account_id': self.env.ref(
                        'account_consolidation.subA_rev1').id,
                    'company_id': self.subsidiary_a.id,
                    'debit': 0,
                    'credit': 100,
                    'operating_unit_id': ou_b2c.id
                })
            ]
        })

        self.env['account.move'].create({
            'journal_id': self.op_journal_subsidiary_b.id,
            'company_id': self.subsidiary_b.id,
            'ref': '/',
            'date': fields.Date.from_string('%s-01-26' % time.strftime('%Y')),
            'currency_id': self.env.ref('base.EUR').id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.env.ref(
                        'account_consolidation.subB_exp1').id,
                    'company_id': self.subsidiary_b.id,
                    'currency_id': self.env.ref('base.EUR').id,
                    'amount_currency': 100,
                    'debit': 180,
                    'credit': 0,
                    'operating_unit_id': ou_b2b.id,
                }), (0, 0, {
                    'account_id': self.env.ref(
                        'account_consolidation.subB_pay1').id,
                    'company_id': self.subsidiary_b.id,
                    'currency_id': self.env.ref('base.EUR').id,
                    'amount_currency': -100,
                    'debit': 0,
                    'credit': 180,
                })
            ]
        }).post()

        # Run consolidation
        wizard = self.env['account.consolidation.consolidate'].create({
            'month': '01',
            'target_move': 'all'
        })
        res = wizard.run_consolidation()
        line_ids = res['domain'][0][2]
        conso_move_lines = self.env['account.move.line'].browse(line_ids)

        operating_units = ou_b2b | ou_b2c

        op_unit_conso_move_lines = conso_move_lines.filtered(
            lambda l: l.consol_operating_unit_id in operating_units)

        # As we didn't activate distinct_operating_units on subB, all results
        # are from subA

        self.assertFalse(op_unit_conso_move_lines.filtered(
            lambda l: l.consol_company_id == self.subsidiary_b
        ))

        for line in op_unit_conso_move_lines:
            self.assertEqual(line.consol_company_id, self.subsidiary_a)
            if line.account_id.code.lower() == 'rec1':
                self.assertEqual(line.consol_operating_unit_id,
                                 ou_b2b)
            elif line.account_id.code.lower() == 'rev1':
                self.assertEqual(line.consol_operating_unit_id,
                                 ou_b2c)
