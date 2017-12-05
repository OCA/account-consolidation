from odoo import models, fields, api, _
import datetime
from dateutil.relativedelta import relativedelta


def last_day_of_month(date):
    next_month = date.replace(day=28) + datetime.timedelta(days=4)
    return next_month - datetime.timedelta(days=next_month.day)


class ConsolidationConsolidate(models.TransientModel):

    _name = 'account.consolidation.consolidate'

    def _default_journal(self):
        comp_obj = self.env['res.company']
        journ_obj = self.env['account.journal']
        comp_id = comp_obj._company_default_get()
        journal_id = journ_obj.search(
            [('company_id', '=', comp_id.id)], limit=1)
        if journal_id:
            return journal_id[0]
        return False


    company_id = fields.Many2one('res.company')
    subsidiaries = fields.One2many('res.company', related='company_id.child_ids')
    calculated_lines = fields.One2many('account.consolidation.calculated', 'wizard_id')
    currency_rate = fields.Float(string='Currency rate')
    period_start = fields.Date()
    period_end = fields.Date()
    journal_id = fields.Many2one('account.journal',
                                 'Journal',
                                 required=True,
                                 default=_default_journal)

    @api.onchange('period_start','period_end')
    def _adjust_period(self):
        if self.period_start:
            start = fields.Date.from_string(self.period_start)
            self.period_start = fields.Date.to_string(start.replace(day=1))
        if self.period_end:
            end = fields.Date.from_string(self.period_end)
            day = last_day_of_month(end).day
            self.period_end = fields.Date.to_string(end.replace(day=day))

    def consolidation_periods(self, mode):

        """create periods for year or month depending cosolidation mode"""

        start = fields.Date.from_string(self.period_start)
        end = fields.Date.from_string(self.period_end)
        if mode=='year':
            if start.year == end.year:
                periods = [(start.replace(day=1, month=1),
                            start.replace(day=31, month=12))]
            else:
                periods = []
                start_year = start.year
                while start_year <= end.year:
                    periods.append(
                        (start.replace(day=1, month=1, year=start_year),
                         start.replace(day=31, month=12, year=start_year)))
                    start_year +=1
        if mode =='month':
            if start.year == end.year and start.month == end.month:
                periods = [(start, end)]    # dates already adjusted when entered by user
            else:
                #  TODO use date_range module here
                periods = []
                start_of_month = start
                end_of_month = last_day_of_month(start)
                while end_of_month < end:
                    periods.append(start_of_month,end_of_month)
                    start_of_month += relativedelta(months=1)
                    relativedelta(months=1)
        return periods

    def consolidate_account(self, consolidation_mode,
                            period, state, move,
                            holding_account, subsidiary):
        """
        Consolidates the subsidiary account on the holding account
        Creates move lines on the move with id "move_id"

        :param consolidation_mode: consolidate by Periods or
                                   Year To Date ('period' or 'ytd')
        :param period: Tuple with start and end of period for which we
                                      want to sum the debit/credit
        :param state: state of the moves to consolidate ('all' or 'posted')
        :param move_id: ID of the move on which all the
                        created move lines will be linked
        :param holding_account_id: ID of the account to consolidate
                                   (on the holding), the method will
                                   find the subsidiary's corresponding account
        :param subsidiary_id: ID of the subsidiary to consolidate

        :return: list of IDs of the created move lines
        """


        account_obj = self.env['account.account']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']


        subsidiary_accounts = account_obj.search([('consolidate_to', '=', holding_account.id),
                                                    ('company_id', '=', subsidiary.id)])

        if not subsidiary_accounts:
            # accounts may exist on the holding and not in the subsidiaries,
            # nothing to do
            return []

        #browse_ctx = dict(state=state, periods=subsidiary_period_ids)
        move_lines=[]
        for subs_account in subsidiary_accounts:

            vals = {
                'name': _("Consolidation line in %s mode") % consolidation_mode,
                'account_id': holding_account.id,
                'move_id': move.id,
                'journal_id': move.journal_id.id,
                'company_id': move.company_id.id,
                'date': move.date
            }

            account_moves = self.env['account.move.line'].search(
                [('account_id', '=', subs_account.id),
                 ('date', '>', fields.Date.to_string(period[0])),
                 ('date', '<', fields.Date.to_string(period[1]))])
            if not account_moves:
                continue
            cred = sum(account_moves.mapped('credit'))
            debt = sum(account_moves.mapped('debit'))
            if not cred and not debt:
                return False
            vals.update({
                'debit': debt,
                'credit': cred,
            })
            line = move_line_obj.with_context(check_move_validity=False).create(vals)
            move_lines.append(line)
        return move_lines


            # if (holding_account.company_currency_id.id ==
            #         subs_account.company_currency_id.id):
            #     vals.update({
            #         'debit': balance if balance > 0.0 else 0.0,
            #         'credit': abs(balance) if balance < 0.0 else 0.0,
            #     })
            # else:
            #     currency_rate_type = self._currency_rate_type(holding_account)
            #
            #     currency_value = currency_obj.compute(holding_account.company_currency_id.id,
            #                                           subs_account.company_currency_id.id,
            #                                           balance,
            #                                           currency_rate_type_from=False,  # means spot
            #                                           currency_rate_type_to=currency_rate_type)
            #     vals.update({
            #         'currency_id': subs_account.company_currency_id.id,
            #         'amount_currency': subs_account.balance,
            #         'debit': currency_value if currency_value > 0.0 else 0.0,
            #         'credit': abs(currency_value) if currency_value < 0.0 else 0.0,
            #    })


    def consolidate_subsidiary(self, subsidiary):
        """
        Consolidate one subsidiary on the Holding.
        Create a move per subsidiary and consolidation type (YTD/Period)
        and an move line per account of the subsidiary

        :param subsidiary: subsidiary to consolidate
                              on the holding

        :return: Tuple of form:
                 (list of IDs of the YTD moves,
                  list of IDs of the Period Moves)
        """
        self.ensure_one()
        company_obj = self.env['res.company']
        move_obj = self.env['account.move']
        acc_obj = self.env['account.account']
        cons_holding_accounts = acc_obj.search(
            [('consolidated_childs', '!=', False),('company_id', '=', self.company_id.id)])
        cons_subsidiary_accounts = acc_obj.search([('consolidate_to', '!=', False), ('company_id', '=', subsidiary.id)])
        consolidation_modes = {'year': [], 'month': []}
        for account in cons_holding_accounts:
            cm = account.consolidation_mode
            consolidation_modes[cm].append(account)

        generic_move_vals = {
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'consol_company_id': subsidiary.id,
        }


        year_move_ids = []
        month_move_ids = []
        for consolidation_mode, accounts in consolidation_modes.items():
            if not accounts:
                continue
            periods = self.consolidation_periods(consolidation_mode)

            for period in periods:

                move_vals = dict(
                    generic_move_vals,
                    ref=_("Consolidation %s") % consolidation_mode,
                    date=period[1])
                move = move_obj.create(move_vals)
                has_move_line = False
                for account in accounts:
                    m_id = self.consolidate_account(
                        consolidation_mode,
                        period,
                        'posted',
                        move,
                        account,
                        subsidiary,)
                    if m_id:
                        has_move_line = True
                if has_move_line:
                    locals()[consolidation_mode + '_move_ids'].append(move)
                else:
                    move.unlink()
        return year_move_ids, month_move_ids


    def run_consolidation(self):
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        move_obj = self.env['account.move']

        monthly_move_ids = []
        single_move_id = []

        for subsidiary in self.subsidiaries:
            new_move_ids = self.consolidate_subsidiary(subsidiary)
            single_move_id += new_move_ids[0]
            monthly_move_ids += sum(new_move_ids, [])


class ConsolidationCalculated(models.TransientModel):

    _name = 'account.consolidation.calculated'

    wizard_id = fields.Many2one('account.consolidation.consolidate')
    account_id = fields.Many2one('account.account')
    consolidated_to = fields.Many2one('account.account')
    debit_amount = fields.Float(string='Total Debit')
    credit_amount = fields.Float(string='Total Credit')
    cur_rate_diff = fields.Float(string='Currency rate difference')
    period_start = fields.Date()
    period_end = fields.Date()
    move = fields.Char(string="Move name")
    entry = fields.Char(string="Entry name")
