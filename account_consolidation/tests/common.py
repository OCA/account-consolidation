# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import time
from odoo import fields
from odoo.tests.common import SavepointCase


class TestBaseAccountConsolidation(SavepointCase):

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
