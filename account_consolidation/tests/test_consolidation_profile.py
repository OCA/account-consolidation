# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase


class TestConsolidationProfile(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.conso_company = cls.env.ref(
            'account_consolidation.consolidation_company')
        cls.new_company = cls.env['res.company'].create({
            'name': 'New company'
        })

    def test_profile_get_distinctions(self):
        profile_a = self.env.ref('account_consolidation.conso_sub_a')
        # Check default values
        self.assertTrue(profile_a.distinct_interco_partners)
        self.assertFalse(profile_a.distinct_analytic_accounts)
        res = [('distinct_interco_partners',), (), ]
        self.assertEqual(profile_a.get_distinctions(), res)
        profile_a.distinct_analytic_accounts = True
        distinctions = profile_a.get_distinctions()
        for index, dist in enumerate(distinctions):
            # First element must include both distincts
            if index == 0:
                self.assertIn('distinct_analytic_accounts', dist)
                self.assertIn('distinct_interco_partners', dist)
            if 0 < index < len(distinctions) - 1:
                self.assertIn(dist[0], [
                    'distinct_analytic_accounts',
                    'distinct_interco_partners'])
            # Last element must be empty
            if index == len(distinctions) - 1:
                self.assertEqual((), dist)

    def test_consolidation_profile_company_relations(self):
        profile = self.env['account.consolidation.profile'].create({
            'company_id': self.conso_company.id,
            'sub_company_id': self.new_company.id,
        })
        self.assertEqual(self.new_company.sub_consolidation_profile_id,
                         profile)
        self.assertIn(profile, self.conso_company.consolidation_profile_ids)
        base_company = self.env.ref('base.main_company')
        profile.sub_company_id = base_company
        self.assertEqual(base_company.sub_consolidation_profile_id, profile)
