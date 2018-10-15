# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import SavepointCase


class TestPartnerMulticompany(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_company = cls.env.ref('base.main_company')
        cls.conso_company = cls.env.ref(
            'account_consolidation.consolidation_company')
        cls.subsidiary_a = cls.env.ref(
            'account_consolidation.subsidiary_a')
        cls.subsidiary_b = cls.env.ref(
            'account_consolidation.subsidiary_b')
        cls.demo_user = cls.env.ref('base.user_demo')
        cls.conso_user = cls.env.ref(
            'account_consolidation.consolidation_manager_user')

    def test_demo_user_main_company_only(self):
        """Test that demo user can only access main company stuff"""
        # Do not share partners between companies
        self.env.ref('base.res_partner_rule').active = True

        self.assertIn(self.main_company, self.demo_user.company_ids)
        self.assertNotIn(self.conso_company, self.demo_user.company_ids)
        self.assertNotIn(self.subsidiary_a, self.demo_user.company_ids)
        self.assertNotIn(self.subsidiary_b, self.demo_user.company_ids)
        self.assertEqual(self.main_company, self.demo_user.company_id)

        demo_user_partners_allowed = self.env['res.partner'].sudo(
            self.demo_user).search([])
        self.assertNotIn(self.conso_company.partner_id,
                         demo_user_partners_allowed)
        self.assertNotIn(self.subsidiary_a.partner_id,
                         demo_user_partners_allowed)
        self.assertNotIn(self.subsidiary_b.partner_id,
                         demo_user_partners_allowed)

    def test_conso_user_conso_company_rule(self):

        # Ensure conso users has access to conso and subs
        self.assertIn(self.conso_company, self.conso_user.company_ids)
        self.assertIn(self.subsidiary_a, self.conso_user.company_ids)
        self.assertIn(self.subsidiary_b, self.conso_user.company_ids)
        self.assertEqual(self.conso_company, self.conso_user.company_id)

        # Share partners between companies
        self.env.ref('base.res_partner_rule').active = False
        self.assertEqual(self.subsidiary_a.partner_id.company_id,
                         self.subsidiary_a)
        self.assertEqual(self.subsidiary_b.partner_id.company_id,
                         self.subsidiary_b)

        conso_user_partners = self.env['res.partner'].sudo(
            self.conso_user).search([])
        self.assertIn(self.conso_company.partner_id, conso_user_partners)
        self.assertIn(self.subsidiary_a.partner_id, conso_user_partners)
        self.assertIn(self.subsidiary_b.partner_id, conso_user_partners)

        # Do not share partners between companies
        self.env.ref('base.res_partner_rule').active = True

        # When rule is active we should remove the company_id from the
        # partner so they are available in conso company
        self.subsidiary_a.partner_id.company_id = None
        self.subsidiary_b.partner_id.company_id = None

        conso_user_partners = self.env['res.partner'].sudo(
            self.conso_user).search([])
        self.assertIn(self.conso_company.partner_id, conso_user_partners)
        self.assertIn(self.subsidiary_a.partner_id, conso_user_partners)
        self.assertIn(self.subsidiary_b.partner_id, conso_user_partners)

    def test_conso_user_create_move_line_partner(self):
        # Do not share partners between companies
        self.env.ref('base.res_partner_rule').active = True

        # When rule is active we should remove the company_id from the
        # partner so they are available in conso company
        self.subsidiary_a.partner_id.company_id = None
        self.subsidiary_b.partner_id.company_id = None

        conso_journal = self.env.ref(
            'account_consolidation.conso_consolidation_journal')
        test_conso_move = self.env['account.move'].create({
            'company_id': self.conso_company.id,
            'journal_id': conso_journal.id,
            'consol_company_id': self.subsidiary_a.id,
            'ref': 'Consolidation test',
            'date': '2018-10-03',
            'line_ids': [
                (0, False, {
                    'company_id': self.conso_company.id,
                    'journal_id': conso_journal.id,
                    'date': '2018-10-03',
                    'account_id': self.env.ref(
                        'account_consolidation.conso_exp1').id,
                    'debit': 10.0,
                    'credit': 0.0,
                    'name': 'Consolidation test debit',
                    'consol_partner_id': self.subsidiary_a.partner_id.id,
                }),
                (0, False, {
                    'company_id': self.conso_company.id,
                    'journal_id': conso_journal.id,
                    'date': '2018-10-03',
                    'account_id': self.env.ref(
                        'account_consolidation.conso_lia1').id,
                    'debit': 0.0,
                    'credit': 10.0,
                    'name': 'Consolidation test credit',
                })
            ]
        })
        self.assertEqual(test_conso_move.company_id, self.conso_company)
        for line in test_conso_move.line_ids:
            if line.debit:
                self.assertEqual(line.consol_partner_id,
                                 self.subsidiary_a.partner_id)
