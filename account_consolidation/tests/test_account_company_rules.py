# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase
from odoo import exceptions


class TestAccountCompanyRules(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_model = cls.env['res.users'].with_context(
            {'no_reset_password': True,
             'mail_create_nosubscribe': True}
        )

        cls.account_model = cls.env['account.account']

        cls.main_company = cls.env.ref('base.main_company')
        cls.consolidation_company = cls.env.ref(
            'account_consolidation.consolidation_company')
        cls.subsidiary_a = cls.env.ref('account_consolidation.subsidiary_a')
        cls.subsidiary_b = cls.env.ref('account_consolidation.subsidiary_b')

        cls.account_user = cls.user_model.create({
            'name': 'Account user',
            'login': 'Account user',
            'email': 'account@user.com',
            'groups_id': [(6, 0, [
                cls.env.ref('account.group_account_user').id,
                cls.env.ref('base.group_user').id
            ])],
            'company_ids': [(6, 0, [cls.main_company.id])],
            'company_id': cls.main_company.id
        })

        cls.account_manager = cls.user_model.create({
            'name': 'Account manager',
            'login': 'Account manager',
            'email': 'account@manager.com',
            'groups_id': [(6, 0, [
                cls.env.ref('account.group_account_manager').id,
                cls.env.ref('base.group_user').id
            ])],
            'company_ids': [(6, 0, [cls.main_company.id])],
            'company_id': cls.main_company.id
        })

        cls.all_companies = (
            cls.main_company | cls.consolidation_company |
            cls.subsidiary_a | cls.subsidiary_b
        )

        cls.consolidation_manager = cls.user_model.create({
            'name': 'Consolidation manager',
            'login': 'Consolidation manager',
            'email': 'consolidation@manager.com',
            'groups_id': [(6, 0, [
                cls.env.ref(
                    'account_consolidation.group_consolidation_manager').id,
                cls.env.ref('base.group_user').id
            ])],
            'company_ids': [(6, 0, cls.all_companies.ids)],
            'company_id': cls.main_company.id
        })

        cls.dummy_account = cls.account_model.create({
            'code': 'DUMMY',
            'name': 'DUMMY',
            'user_type_id': cls.env.ref(
                'account.data_account_type_current_assets').id,
            'company_id': cls.main_company.id
        })

        cls.conso_account = cls.account_model.create({
            'code': 'CONSO',
            'name': 'CONSO',
            'user_type_id': cls.env.ref(
                'account.data_account_type_current_assets').id,
            'company_id': cls.consolidation_company.id
        })

    def _create_account(self, user, name, company=False):
        vals = {
            'code': name,
            'name': name,
            'user_type_id': self.env.ref(
                'account.data_account_type_current_assets').id
        }
        if company:
            vals['company_id'] = company.id

        return self.account_model.sudo(user.id).create(vals)

    def _test_account_main_company_crud(self, user):
        # Create
        create_account = self._create_account(user, 'TEST')
        self.assertEqual(len(create_account), 1)
        # Read
        read_account = self.account_model.sudo(user.id).search([
            ('name', '=', 'TEST')])
        self.assertEqual(create_account, read_account)
        # Write
        read_account.sudo(user.id).write({'name': 'TEST modified'})
        self.assertEqual(read_account.name, 'TEST modified')
        # Delete
        read_account.sudo(user.id).unlink()
        with self.assertRaises(exceptions.MissingError):
            name = read_account.name  # noqa

    def _test_account_main_company_read_only(self, user):
        # Create error
        with self.assertRaises(exceptions.AccessError):
            self._create_account(user, 'TEST')
        # Read
        read_account = self.account_model.sudo(user.id).search([
            ('name', '=', 'DUMMY')])
        self.assertEqual(len(read_account), 1)
        self.assertEqual(read_account.name, 'DUMMY')
        # Write
        with self.assertRaises(exceptions.AccessError):
            read_account.sudo(user.id).write({'name': 'DUMMY modified'})
        # Delete
        with self.assertRaises(exceptions.AccessError):
            read_account.sudo(user.id).unlink()

    def _test_account_multicompany_no_crud(self, user):
        # Create
        with self.assertRaises(exceptions.AccessError):
            self._create_account(
                user, 'TEST', company=self.consolidation_company)
        # Read
        read_account = self.account_model.sudo(user.id).search([
            ('name', '=', 'CONSO')])
        self.assertEqual(len(read_account), 0)
        # Write
        with self.assertRaises(exceptions.AccessError):
            self.conso_account.sudo(user.id).write({'name': 'CONSO modified'})
        # Delete
        with self.assertRaises(exceptions.AccessError):
            self.conso_account.sudo(user.id).unlink()

    def _test_account_multicompany_crud(self, user):
        # Create
        # We use TEST2 because somehow TEST was created although
        # AccessError were raised
        create_account = self._create_account(
            user, 'TEST2', company=self.consolidation_company)
        self.assertEqual(len(create_account), 1)
        # Read
        read_account = self.account_model.sudo(user.id).search([
            ('name', '=', 'CONSO')])
        self.assertEqual(len(read_account), 1)
        self.assertEqual(read_account.name, 'CONSO')
        # Write
        read_account.sudo(user.id).write({'name': 'CONSO modified'})
        self.assertEqual(read_account.name, 'CONSO modified')
        # Delete
        read_account.sudo(user.id).unlink()
        with self.assertRaises(exceptions.MissingError):
            name = read_account.name  # noqa

    def test_account_users(self):
        self._test_account_main_company_crud(self.account_manager)
        self._test_account_main_company_crud(self.consolidation_manager)

        self._test_account_main_company_read_only(self.account_user)

    def test_account_multicompany(self):
        self._test_account_multicompany_no_crud(self.account_user)
        self._test_account_multicompany_no_crud(self.account_manager)

        self.consolidation_manager.company_id = self.subsidiary_a
        self._test_account_multicompany_crud(self.consolidation_manager)
