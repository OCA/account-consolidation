# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import time
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import SavepointCase


class TestAccountConsolidation(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # disable tracking test suite wise
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        subsidiaries = [('subsidiary_a', 'subA'), ('subsidiary_b', 'subB')]

        opening_entries = {
            'date': '%s-01-01' % time.strftime('%Y'),
            'label': 'Opening',
            'subA': [('ass1', 130), ('lia1', -80), ('lia2', -50)],
            'subB': [('ass1', 170), ('lia1', -160), ('lia2', -10)]
        }

        p1_entries = {
            'date': '%s-01-20' % time.strftime('%Y'),
            'label': 'P1',
            'subA': [
                ('exp1', 20), ('exp2', 30), ('exp3', 65), ('rev1', -50),
                ('rev2', -90), ('ass1', 80), ('lia1', -10), ('lia2', -45)
            ],
            'subB': [
                ('exp1', 15), ('exp2', 26), ('exp3', 12), ('rev1', -88),
                ('rev2', -70), ('ass1', 155), ('lia1', -40), ('lia2', -10)
            ]
        }

        p2_entries = {
            'date': '%s-02-15' % time.strftime('%Y'),
            'label': 'P2',
            'subA': [
                ('exp1', 10), ('exp2', 55), ('exp3', 40), ('rev1', -120),
                ('rev2', -75), ('ass1', 40), ('lia1', 50)
            ],
            'subB': [
                ('exp1', 10), ('exp2', 55), ('exp3', 40), ('rev1', -120),
                ('ass1', 80), ('lia1', -30), ('lia2', -35)]
        }

        entries = [opening_entries, p1_entries, p2_entries]

        cls.holding = cls.env.ref(
            'account_consolidation.consolidation_company')

        cls.env.user.write({
            'company_ids': [(4, cls.holding.id, False)]
        })

        for sub in subsidiaries:
            company = cls.env.ref('account_consolidation.%s' % sub[0])
            company.partner_id.company_id = False

            setattr(cls, sub[0], company)

            cls.env.user.write({
                'company_ids': [(4, company.id, False)]
            })
            cls.env.user.company_id = company

            journal = cls.env.ref('account_consolidation.%s_op_journal' %
                                  sub[1])
            setattr(cls, 'op_journal_%s' % sub[0], journal)

            for entry in entries:
                lines_list = []
                for move_tuple in entry[sub[1]]:
                    account = cls.env.ref('account_consolidation.%s_%s' %
                                          (sub[1], move_tuple[0]))
                    line_vals = {
                        'name': entry['label'],
                        'account_id': account.id,
                        'company_id': company.id,
                        'debit': 0,
                        'credit': 0
                    }
                    amount = move_tuple[1]

                    if amount > 0:
                        line_vals.update({'debit': amount})
                    elif amount < 0:
                        line_vals.update({'credit': -amount})

                    lines_list.append(line_vals)

                lines_vals = [(0, 0, l) for l in lines_list]
                move_vals = {
                    'journal_id': journal.id,
                    'company_id': company.id,
                    'ref': entry['label'],
                    'date': fields.Date.from_string(entry['date']),
                    'line_ids': lines_vals
                }
                move = cls.env['account.move'].create(move_vals)

                # Post only moves of subisdiary B
                if sub[0] == 'subsidiary_b':
                    move.post()

        cls.env.user.company_id = cls.holding

        cls.consolidation_manager = cls.env['res.users'].with_context(
            no_reset_password=True
        ).create({
            'name': 'Consolidation manager',
            'login': 'Consolidation manager',
            'email': 'consolidation@manager.com',
            'groups_id': [(6, 0, [
                cls.env.ref(
                    'account_consolidation.group_consolidation_manager').id,
                cls.env.ref('base.group_user').id
            ])],
            'company_ids': [(6, 0, [
                cls.holding.id, cls.subsidiary_a.id, cls.subsidiary_b.id])],
            'company_id': cls.holding.id
        })

    def test_default_values(self):
        wizard = self.env['account.consolidation.consolidate'].create({})
        last_month = date.today() - relativedelta(month=1)
        self.assertEqual(wizard.year, last_month.strftime('%Y'))
        self.assertEqual(wizard.month, last_month.strftime('%m'))
        self.assertEqual(wizard.company_id, self.holding)
        self.assertEqual(wizard.journal_id,
                         self.holding.consolidation_default_journal_id)
        self.assertEqual(wizard.consolidation_profile_ids.mapped(
            'sub_company_id'), self.subsidiary_a | self.subsidiary_b)
        self.assertEqual(wizard.target_move, 'posted')

    def test_consolidation_checks_ok(self):
        wizard = self.env['account.consolidation.check'].create({})
        wizard.check_configuration()
        self.assertEqual(wizard.state, 'ok')

    def test_consolidation_checks_error_account(self):
        self.env.ref('account_consolidation.subA_exp1').write({
            'consolidation_account_id': False
        })
        wizard = self.env['account.consolidation.check'].create({})
        wizard.check_configuration()
        self.assertEqual(wizard.state, 'error')

    def test_consolidation_checks_error_company_partner(self):
        self.subsidiary_a.partner_id.company_id = self.subsidiary_a
        share_partners_rule = self.env.ref('base.res_partner_rule')
        share_partners_rule.active = True
        wizard = self.env['account.consolidation.check'].create({})
        wizard.check_configuration()
        self.assertEqual(wizard.state, 'error')
        share_partners_rule.active = False
        wizard = self.env['account.consolidation.check'].create({})
        wizard.check_configuration()
        self.assertEqual(wizard.state, 'ok')

    def test_consolidation_checks_error_unallowed_company(self):
        self.env.user.write({
            'company_ids': [
                (6, False, [self.holding.id, self.subsidiary_a.id])]
        })
        wizard = self.env['account.consolidation.check'].create({})
        wizard.check_configuration()
        self.assertEqual(wizard.state, 'error')

    def test_consolidation_jan_all_conso_user(self):
        wizard = self.env['account.consolidation.consolidate'].sudo(
            self.consolidation_manager).create({
                'month': '01',
                'target_move': 'all'
            })
        res = wizard.sudo(self.consolidation_manager).run_consolidation()
        line_ids = res['domain'][0][2]
        conso_move_lines = self.env['account.move.line'].sudo(
            self.consolidation_manager).browse(line_ids)

        conso_results = {
            'subA': {
                'exp1': 20, 'exp2': 30, 'exp3': 65, 'rev1': -50,
                'rev2': -90, 'ass1': 210, 'lia1': -90, 'lia2': -95
            },
            'subB': {
                'exp1': 15, 'exp2': 26, 'exp3': 12, 'rev1': -88,
                'rev2': -70, 'ass1': 325, 'lia1': -200, 'lia2': -20, 'ced': 0
            }
        }

        for line in conso_move_lines:

            if line.consol_company_id == self.subsidiary_a:
                conso_comp = 'subA'
                currency_diff = False
            elif line.consol_company_id == self.subsidiary_b:
                conso_comp = 'subB'
                currency_diff = True

            acc = line.account_id.code.lower()

            if currency_diff:
                self.assertEqual(line.amount_currency,
                                 conso_results[conso_comp][acc])
            else:
                self.assertEqual(line.balance,
                                 conso_results[conso_comp][acc])

    def test_consolidation_28_feb_all(self):
        january_wizard = self.env['account.consolidation.consolidate'].create(
            {'month': '01', 'target_move': 'all'}
        )
        january_res = january_wizard.run_consolidation()
        january_line_ids = january_res['domain'][0][2]
        january_conso_lines = self.env['account.move.line'].browse(
            january_line_ids)
        january_moves = january_conso_lines.mapped('move_id')
        january_moves.post()
        for move in january_moves:
            self.assertTrue(move.to_be_reversed)

        february_wizard = self.env['account.consolidation.consolidate'].create(
            {'month': '02', 'target_move': 'all'}
        )
        february_res = february_wizard.run_consolidation()

        for move in january_moves:
            reversed_move = move.reversal_id
            self.assertEqual(reversed_move.amount, move.amount)
            self.assertEqual(reversed_move.date,
                             february_wizard._get_month_first_date())

        february_line_ids = february_res['domain'][0][2]
        february_conso_lines = self.env['account.move.line'].browse(
            february_line_ids)

        february_conso_results = {
            'subA': {
                'exp1': 30, 'exp2': 85, 'exp3': 105, 'rev1': -170,
                'rev2': -165, 'ass1': 250, 'lia1': -40, 'lia2': -95
            },
            'subB': {
                'exp1': 25, 'exp2': 81, 'exp3': 52, 'rev1': -208,
                'rev2': -70, 'ass1': 405, 'lia1': -230, 'lia2': -55, 'ced': 0
            }
        }
        for line in february_conso_lines:

            if line.consol_company_id == self.subsidiary_a:
                conso_comp = 'subA'
                currency_diff = False
            elif line.consol_company_id == self.subsidiary_b:
                conso_comp = 'subB'
                currency_diff = True

            acc = line.account_id.code.lower()

            if currency_diff:
                self.assertEqual(line.amount_currency,
                                 february_conso_results[conso_comp][acc])
            else:
                self.assertEqual(line.balance,
                                 february_conso_results[conso_comp][acc])

    def test_consolidation_jan_with_exchange_rates(self):
        wizard = self.env['account.consolidation.consolidate'].create({
            'month': '01',
        })
        res = wizard.run_consolidation()
        line_ids = res['domain'][0][2]
        conso_move_lines = self.env['account.move.line'].browse(line_ids)

        conso_results = {
            # monthly rate used : 1.3
            'exp1': 11.54, 'exp2': 20, 'exp3': 9.23, 'rev1': -67.69,
            'rev2': -53.85,
            # spot rate used : 1.36
            'ass1': 238.97, 'lia1': -147.06, 'lia2': -14.71,
            'ced': 3.57
        }
        for line in conso_move_lines:

            self.assertEqual(line.consol_company_id, self.subsidiary_b)

            acc = line.account_id.code.lower()

            self.assertEqual(line.balance, conso_results[acc])

    def test_consolidation_jan_with_interco_partner(self):
        # Create intercompany moves
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
                    'partner_id': self.subsidiary_b.partner_id.id
                }), (0, 0, {
                    'account_id': self.env.ref(
                        'account_consolidation.subA_rev1').id,
                    'company_id': self.subsidiary_a.id,
                    'debit': 0,
                    'credit': 100,
                    'partner_id': self.subsidiary_b.partner_id.id
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
                    'partner_id': self.subsidiary_a.partner_id.id
                }), (0, 0, {
                    'account_id': self.env.ref(
                        'account_consolidation.subB_pay1').id,
                    'company_id': self.subsidiary_b.id,
                    'currency_id': self.env.ref('base.EUR').id,
                    'amount_currency': -100,
                    'debit': 0,
                    'credit': 180,
                    'partner_id': self.subsidiary_a.partner_id.id
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

        interco_partners = (
            self.subsidiary_a.partner_id | self.subsidiary_b.partner_id)

        interco_conso_move_lines = conso_move_lines.filtered(
            lambda l: l.consol_partner_id in interco_partners)

        conso_results = {
            'subA': {
                'rev1': -100, 'rec1': 100
            },
            'subB': {
                'exp1': 138.46,  # 180 / monthly rate : 1.3
                'pay1': -132.35,  # 180 / spot rate : 1.36
            }
        }
        for line in interco_conso_move_lines:
            if line.consol_company_id == self.subsidiary_a:
                conso_comp = 'subA'
            elif line.consol_company_id == self.subsidiary_b:
                conso_comp = 'subB'

            acc = line.account_id.code.lower()

            self.assertEqual(line.balance, conso_results[conso_comp][acc])

    def test_consolidation_jan_with_analytic(self):
        # Create analytic accounts
        analytic_model = self.env['account.analytic.account']
        self.analytic_alpha = analytic_model.create({
            'name': 'Alpha',
            'company_id': self.subsidiary_a.id
        })
        self.analytic_beta = analytic_model.create({
            'name': 'Beta',
            'company_id': self.subsidiary_a.id
        })
        self.analytic_gamma = analytic_model.create({
            'name': 'Gamma',
            'company_id': self.subsidiary_b.id
        })
        # Activate analytic distinction on subsidiary A
        subA_profile = self.env.ref('account_consolidation.conso_sub_a')
        subA_profile.distinct_analytic_accounts = True
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
                    'analytic_account_id': self.analytic_alpha.id
                }), (0, 0, {
                    'account_id': self.env.ref(
                        'account_consolidation.subA_rev1').id,
                    'company_id': self.subsidiary_a.id,
                    'debit': 0,
                    'credit': 100,
                    'analytic_account_id': self.analytic_beta.id
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
                    'analytic_account_id': self.analytic_gamma.id,
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

        analytic_accounts = (
            self.analytic_alpha | self.analytic_beta | self.analytic_gamma
        )

        analytic_conso_move_lines = conso_move_lines.filtered(
            lambda l: l.consol_analytic_account_id in analytic_accounts)
        # import pdb; pdb.set_trace()
        # As we didn't activate distinct_analytic_accounts on subB, all results
        # are from subA

        self.assertFalse(analytic_conso_move_lines.filtered(
            lambda l: l.consol_company_id == self.subsidiary_b
        ))

        for line in analytic_conso_move_lines:
            self.assertEqual(line.consol_company_id, self.subsidiary_a)
            if line.account_id.code.lower() == 'rec1':
                self.assertEqual(line.consol_analytic_account_id,
                                 self.analytic_alpha)
            elif line.account_id.code.lower() == 'rev1':
                self.assertEqual(line.consol_analytic_account_id,
                                 self.analytic_beta)
