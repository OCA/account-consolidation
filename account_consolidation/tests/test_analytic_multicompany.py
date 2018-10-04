# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import SavepointCase


class TestAnalyticMulticompany(SavepointCase):

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

        analytic_model = cls.env['account.analytic.account'].with_context(
            tracking_disable=True)
        cls.analytic_test_a = analytic_model.create({
            'name': 'Test A',
            'company_id': cls.subsidiary_a.id
        })
        cls.analytic_test_b = analytic_model.create({
            'name': 'Test B',
            'company_id': cls.subsidiary_b.id
        })
        cls.analytic_internal = cls.env.ref('analytic.analytic_internal')

    def test_demo_analytic_company_only(self):
        # Switch demo user to sub A
        self.demo_user.write({
            'company_ids': [(4, self.subsidiary_a.id)],
            'company_id': self.subsidiary_a.id
        })
        analytic_accounts = self.env['account.analytic.account'].sudo(
            self.demo_user).search([])
        self.assertIn(self.analytic_test_a, analytic_accounts)
        self.assertNotIn(self.analytic_test_b, analytic_accounts)

    def test_conso_all_analytic(self):
        analytic_accounts = self.env['account.analytic.account'].sudo(
            self.conso_user).search([])
        self.assertIn(self.analytic_test_a, analytic_accounts)
        self.assertIn(self.analytic_test_b, analytic_accounts)
        # TODO WTH do we get this record in analytic_accounts ?!
        self.assertNotIn(self.analytic_internal, analytic_accounts)

    def test_analytic_conso_company(self):
        self.assertEqual(self.analytic_test_a.consolidation_company_id,
                         self.conso_company)
        self.assertEqual(self.analytic_test_b.consolidation_company_id,
                         self.conso_company)

        self.assertEqual(self.analytic_internal.company_id,
                         self.env.ref('base.main_company'))
        self.assertFalse(self.analytic_internal.consolidation_company_id)
