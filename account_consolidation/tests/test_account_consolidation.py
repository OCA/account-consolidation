# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import time
import mock
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import TransactionCase

MOCK_PATH = 'odoo.addons.account_consolidation'


class TestAccountConsolidation(TransactionCase):

    def setUp(self):
        super().setUp()

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

        for sub in subsidiaries:
            company = self.env.ref('account_consolidation.%s' % sub[0])
            company.partner_id.company_id = False

            setattr(self, sub[0], company)

            self.env.user.write({
                'company_ids': [(4, company.id, False)]
            })
            self.env.user.company_id = company

            journal = self.env.ref('account_consolidation.%s_op_journal' %
                                   sub[1])
            setattr(self, 'op_journal_%s' % sub[0], journal)

            for entry in entries:
                lines_list = []
                for move_tuple in entry[sub[1]]:
                    account = self.env.ref('account_consolidation.%s_%s' %
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
                move = self.env['account.move'].create(move_vals)

                # Post only moves of subisdiary B
                if sub[0] == 'subsidiary_b':
                    move.post()

        self.holding = self.env.ref(
            'account_consolidation.consolidation_company')

        self.consolidation_manager = self.env['res.users'].create({
            'name': 'Consolidation manager',
            'login': 'Consolidation manager',
            'email': 'consolidation@manager.com',
            'groups_id': [(6, 0, [
                self.env.ref(
                    'account_consolidation.group_consolidation_manager').id,
                self.env.ref('base.group_user').id
            ])],
            'company_ids': [(6, 0, [
                self.holding.id, self.subsidiary_a.id, self.subsidiary_b.id])],
            'company_id': self.holding.id
        })
        # Definition of company on the user should be done after creating
        # consolidation user as this create() switches self.env.user's company
        self.env.user.company_id = self.holding

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
        wizard = self.env['account.consolidation.check'].create({})
        wizard.check_configuration()
        self.assertEqual(wizard.state, 'error')

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
            self.assertTrue(move.auto_reverse)

        february_wizard = self.env['account.consolidation.consolidate'].create(
            {'month': '02', 'target_move': 'all'}
        )
        february_res = february_wizard.run_consolidation()

        for move in january_moves:
            reversed_move = move.reverse_entry_id
            self.assertEqual(reversed_move.amount, move.amount)
            self.assertEqual(fields.Date.to_string(reversed_move.date),
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

    def test_multi_consolidation_(self):
        # run consolidation multiple times and check if accounting entries are
        # created correctly
        wizard = self.env['account.consolidation.consolidate'].sudo(
            self.consolidation_manager).create({
                'month': '01',
                'target_move': 'all'
            })
        res = wizard.sudo(self.consolidation_manager).run_consolidation()
        line_ids = res['domain'][0][2]
        jan_moves = self.env['account.move.line'].sudo(
            self.consolidation_manager).browse(line_ids).mapped('move_id')
        self.assertTrue(all(jan_moves.mapped('auto_reverse')))
        self.assertFalse(all(jan_moves.mapped('reverse_date')))
        self.assertFalse(jan_moves.mapped('reverse_entry_id'))
        wizard = self.env['account.consolidation.consolidate'].sudo(
            self.consolidation_manager).create({
                'month': '02',
                'target_move': 'all'
            })
        res = wizard.sudo(self.consolidation_manager).run_consolidation()
        line_ids = res['domain'][0][2]
        feb_moves = self.env['account.move.line'].sudo(
            self.consolidation_manager).browse(line_ids).mapped('move_id')
        self.assertTrue(all(feb_moves.mapped('auto_reverse')))
        self.assertFalse(all(feb_moves.mapped('reverse_date')))
        self.assertFalse(feb_moves.mapped('reverse_entry_id'))
        # january moves were reversed and stay unposted
        for jan_move in jan_moves:
            self.assertTrue(jan_move.reverse_entry_id)
            self.assertEqual(jan_move.state, 'draft')
        # If reversals of jan entries and feb entries are deleted, they must
        # be generated again with the same values on the next run
        jan_reversals = jan_moves.mapped('reverse_entry_id')
        entry_fields = [
            'state', 'partner_id', 'consol_company_id', 'reverse_entry_id',
            'currency_id', 'reverse_date', 'auto_reverse', 'journal_id',
            'date', 'amount', 'company_id'
        ]
        line_fields = [
            'credit', 'consol_company_id', 'consol_partner_id', 'reconciled',
            'account_id', 'partner_id', 'balance', 'journal_id', 'company_id',
            'amount_currency', 'currency_id', 'company_currency_id',
            'debit', 'quantity', 'consolidated', 'date'
        ]
        jan_reversal_values = jan_reversals.read(entry_fields)
        jan_reversal_lines_values = jan_reversals.mapped('line_ids').read(
            line_fields)
        feb_moves_values = feb_moves.read(entry_fields)
        feb_moves_lines_values = feb_moves.mapped('line_ids').read(line_fields)
        jan_reversals.unlink()
        feb_moves.unlink()
        wizard = self.env['account.consolidation.consolidate'].sudo(
            self.consolidation_manager).create({
                'month': '02',
                'target_move': 'all'
            })
        res = wizard.sudo(self.consolidation_manager).run_consolidation()
        line_ids = res['domain'][0][2]
        new_feb_moves = self.env['account.move.line'].sudo(
            self.consolidation_manager).browse(line_ids).mapped('move_id')
        new_jan_reversals = jan_moves.mapped('reverse_entry_id')
        new_jan_reversal_values = new_jan_reversals.read(entry_fields)
        new_jan_reversal_lines_values = new_jan_reversals.mapped(
            'line_ids').read(line_fields)
        new_feb_moves_values = new_feb_moves.read(entry_fields)
        new_feb_moves_lines_values = new_feb_moves.mapped('line_ids').read(
            line_fields)

        def _compare_new_read_values(list1, list2, flist):
            """ Ensure list1 and list2 are equal out of id fields

            :param list1: Result of a read on a recordset
            :param list2: Result of a read on a recordset
            :param flist: Fields that must be equal
            :return:
            """
            for item1, item2 in zip(list1, list2):
                for fname in flist:
                    self.assertEqual(item1.get(fname), item2.get(fname))
                self.assertNotEqual(item1.get('id'), item2.get('id'))

        _compare_new_read_values(
            jan_reversal_values, new_jan_reversal_values, entry_fields
        )
        _compare_new_read_values(
            jan_reversal_lines_values, new_jan_reversal_lines_values,
            line_fields
        )
        _compare_new_read_values(
            feb_moves_values, new_feb_moves_values, entry_fields
        )
        _compare_new_read_values(
            feb_moves_lines_values, new_feb_moves_lines_values, line_fields
        )
        # Check that reversal ir.cron will not reverse entries automatically
        cron = self.env.ref('account.ir_cron_reverse_entry')
        with mock.patch(
                MOCK_PATH + '.models.consolidation_profile.fields.Date.today'
        ) as fnct:
            # Unposted entries are not selected by the ir.cron, so we post one
            # and check that both entries stay 'unreversed'
            new_feb_moves[0].post()
            fnct.return_value = '%s-06-30' % time.strftime('%Y'),
            cron.method_direct_trigger()
            self.assertTrue(all(new_feb_moves.mapped('auto_reverse')))
            self.assertFalse(new_feb_moves.mapped('reverse_entry_id'))
