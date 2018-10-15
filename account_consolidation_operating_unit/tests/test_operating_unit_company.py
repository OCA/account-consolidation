# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import SavepointCase


class TestOperatingUnitCompany(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        main_company = cls.env.ref('base.main_company')
        subsidiary_a = cls.env.ref('account_consolidation.subsidiary_a')
        subsidiary_b = cls.env.ref('account_consolidation.subsidiary_b')

        cls.ou_business_sub_a = cls.env['operating.unit'].create({
            'name': 'Business A',
            'code': 'BA',
            'company_id': subsidiary_a.id,
            'partner_id': subsidiary_a.partner_id.id
        })
        cls.ou_private_sub_a = cls.env['operating.unit'].create({
            'name': 'Private A',
            'code': 'PA',
            'company_id': subsidiary_a.id,
            'partner_id': subsidiary_a.partner_id.id,
        })

        cls.ou_business_sub_b = cls.env['operating.unit'].create({
            'name': 'Business B',
            'code': 'BB',
            'company_id': subsidiary_b.id,
            'partner_id': subsidiary_b.partner_id.id
        })
        cls.ou_private_sub_b = cls.env['operating.unit'].create({
            'name': 'Private B',
            'code': 'PB',
            'company_id': subsidiary_b.id,
            'partner_id': subsidiary_b.partner_id.id,
        })

        cls.ou_b2b = cls.env.ref('operating_unit.b2b_operating_unit')
        cls.ou_b2c = cls.env.ref('operating_unit.b2c_operating_unit')

        cls.ou_b2c.company_id = main_company

        cls.demo_user = cls.env.ref('base.user_demo')
        cls.conso_user = cls.env.ref(
            'account_consolidation.consolidation_manager_user')

    def test_demo_user_only_demo(self):
        demo_ous = self.env['operating.unit'].sudo(self.demo_user).search([])

        self.assertIn(self.ou_b2c, demo_ous)
        self.assertIn(self.ou_b2b, demo_ous)
        self.assertNotIn(self.ou_business_sub_a, demo_ous)
        self.assertNotIn(self.ou_private_sub_a, demo_ous)
        self.assertNotIn(self.ou_business_sub_b, demo_ous)
        self.assertNotIn(self.ou_private_sub_b, demo_ous)

    def test_conso_user_all(self):
        conso_ous = self.env['operating.unit'].sudo(self.conso_user).search([])

        self.assertNotIn(self.ou_b2c, conso_ous)
        self.assertNotIn(self.ou_b2b, conso_ous)
        self.assertIn(self.ou_business_sub_a, conso_ous)
        self.assertIn(self.ou_private_sub_a, conso_ous)
        self.assertIn(self.ou_business_sub_b, conso_ous)
        self.assertIn(self.ou_private_sub_b, conso_ous)
