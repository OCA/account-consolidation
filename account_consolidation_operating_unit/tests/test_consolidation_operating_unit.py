# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import time
from odoo.addons.account_consolidation.tests.common import TestBaseAccountConsolidation
from odoo import fields


class TestAccountConsolidationOperatingUnit(TestBaseAccountConsolidation):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.conso_company = cls.env.ref(
            'account_consolidation.consolidation_company')

        cls.subsidiary_a = cls.env.ref('account_consolidation.subsidiary_a')
        cls.subsidiary_b = cls.env.ref('account_consolidation.subsidiary_b')
        cls.ou_business_sub_a = cls.env['operating.unit'].create({
            'name': 'Business A',
            'code': 'BA',
            'company_id': cls.subsidiary_a.id,
            'partner_id': cls.subsidiary_a.partner_id.id
        })
        cls.ou_private_sub_a = cls.env['operating.unit'].create({
            'name': 'Private A',
            'code': 'PA',
            'company_id': cls.subsidiary_a.id,
            'partner_id': cls.subsidiary_a.partner_id.id,
        })
        cls.ou_business_sub_b = cls.env['operating.unit'].create({
            'name': 'Business B',
            'code': 'BB',
            'company_id': cls.subsidiary_b.id,
            'partner_id': cls.subsidiary_b.partner_id.id
        })

    def test_consolidation_jan_with_operating_unit(self):
        # Activate operating unit distinction on subsidiary A
        subA_profile = self.env.ref('account_consolidation.conso_sub_a')
        subA_profile.distinct_operating_units = True
        self.env.user.company_id = self.subsidiary_a
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
                    'operating_unit_id': self.ou_business_sub_a.id
                }), (0, 0, {
                    'account_id': self.env.ref(
                        'account_consolidation.subA_rev1').id,
                    'company_id': self.subsidiary_a.id,
                    'debit': 0,
                    'credit': 100,
                    'operating_unit_id': self.ou_private_sub_a.id
                })
            ]
        })
        self.env.user.company_id = self.subsidiary_b
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
                    'operating_unit_id': self.ou_business_sub_b.id,
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
        self.env.user.company_id = self.conso_company
        # Run consolidation
        wizard = self.env['account.consolidation.consolidate'].create({
            'month': '01',
            'target_move': 'all'
        })
        res = wizard.run_consolidation()
        line_ids = res['domain'][0][2]
        conso_move_lines = self.env['account.move.line'].browse(line_ids)

        operating_units = self.ou_business_sub_a | self.ou_private_sub_a

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
                                 self.ou_business_sub_a)
            elif line.account_id.code.lower() == 'rev1':
                self.assertEqual(line.consol_operating_unit_id,
                                 self.ou_private_sub_a)
