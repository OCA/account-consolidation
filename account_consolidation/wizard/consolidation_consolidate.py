# Copyright 2011-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from calendar import monthrange
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

MONTHS = [('01', 'January'),
          ('02', 'February'),
          ('03', 'March'),
          ('04', 'April'),
          ('05', 'May'),
          ('06', 'June'),
          ('07', 'July'),
          ('08', 'August'),
          ('09', 'September'),
          ('10', 'October'),
          ('11', 'November'),
          ('12', 'December')]


class AccountConsolidationConsolidate(models.TransientModel):
    _name = 'account.consolidation.consolidate'
    _inherit = 'account.consolidation.base'

    @api.model
    def _default_journal(self):
        return self._default_company().consolidation_default_journal_id

    @api.model
    def _default_get_month(self):
        today = fields.Date.from_string(fields.Date.context_today(self))
        return (today - relativedelta(month=1)).strftime('%m')

    @api.model
    def _default_get_year(self):
        today = fields.Date.from_string(fields.Date.context_today(self))
        if today.strftime('%m') != '01':
            return today.strftime('%Y')
        else:
            return (today - relativedelta(year=1)).strftime('%Y')

    @api.model
    def _get_month_last_date(self):
        last_day = monthrange(int(self.year), int(self.month))[1]
        return '%s-%s-%s' % (self.year, self.month, last_day)

    @api.model
    def _get_month_first_date(self):
        return '%s-%s-%s' % (self.year, self.month, '01')

    year = fields.Char(
        size=4,
        required=True,
        default=lambda self: self._default_get_year()
    )
    month = fields.Selection(
        MONTHS,
        required=True,
        default=lambda self: self._default_get_month()
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        default=lambda self: self._default_journal(),
        required=True
    )
    target_move = fields.Selection(
        [('posted', 'All Posted Entries'),
         ('all', 'All Entries')],
        string='Target Moves',
        default='posted',
        required=True
    )
    consolidation_profile_ids = fields.Many2many(
        comodel_name='company.consolidation.profile',
        relation='consolidate_profile_rel',
        column1='consolidate_id',
        column2='profile_id',
        default=lambda self: self._get_consolidation_profiles(),
        readonly=True
    )

    @api.multi
    def _get_intercompany_partners(self, subsidiary):
        """
        Return partners linked to subsidiaries which are consolidated, without
        the partner of the actual company being consolidated.

        :param subsidiary: Recordset of company to consolidate
        :return: Recordset of partners
        """
        subsidiaries = self.consolidation_profile_ids.mapped('sub_company_id')
        partners = subsidiaries.mapped('partner_id')
        return partners - subsidiary.partner_id

    def _prepare_rate_difference_line(self, move_lines_list):
        """
        Prepares a move line to balance the move to be created, as the move
        lines can be unbalanced if different currencies are used

        :param move_lines_list: List of move lines to generate
        :return: Dictionnary to create exchange difference move line
        """

        if not move_lines_list:
            return False
        diff_account = self.company_id.consolidation_diff_account_id
        if not diff_account:
            raise UserError(_('Please set the Consolidation difference '
                              'account for company %s in accounting settings.')
                            % self.company_id.name)

        debit = credit = 0.0

        for line_vals in move_lines_list:
            debit += line_vals.get('debit')
            credit += line_vals.get('credit')

        balance = debit - credit

        # We do not want to create counter parts for amount smaller than
        # "holding" company currency rounding policy.
        # As generated lines are in draft state, accountant will be able to
        # manage special cases
        move_is_balanced = self.company_id.currency_id.is_zero(balance)
        if move_is_balanced:
            return False
        else:
            return {
                'account_id': diff_account.id,
                'debit': abs(balance) if balance < 0.0 else 0.0,
                'credit': balance if balance > 0.0 else 0.0,
                'name': _('Consolidation difference (%s %s)') % (
                    dict(MONTHS)[self.month], self.year
                )
            }

    def reverse_moves(self, subsidiary):
        """
        Reverse all consolidation account moves of a subsidiary which have
        the "Auto reversed" flag, and wasn't reversed before this date

        :param subsidiary: Recordset of the subsidiary

        :return: tuple with : Recordset of the reversed moves,
                              Recordset of the reversal moves
        """
        move_obj = self.env['account.move']
        moves_to_reverse = move_obj.search([
            ('journal_id', '=', self.journal_id.id),
            ('auto_reverse', '=', True),
            ('consol_company_id', '=', subsidiary.id),
            ('reverse_entry_id', '=', False),
        ])
        if not moves_to_reverse:
            return moves_to_reverse, False
        try:
            reversal_action = self.env['account.move.reversal'].with_context(
                active_ids=moves_to_reverse.ids,
                __conso_reversal_no_post=True).create({
                    'date': self._get_month_first_date(),
                    'journal_id': self.journal_id.id
                }).reverse_moves()
        except ValidationError as e:
            raise ValidationError(_(
                "The error below appeared while trying to reverse the "
                "following moves: \n %s \n %s") % (
                '\n'.join(['- %s' % m.name for m in moves_to_reverse]),
                e.name
            ))
        reversal_move = move_obj.browse(reversal_action.get('domain')[0][2])

        return moves_to_reverse, reversal_move

    def get_account_balance(self, account, partner=False):
        """
        Gets the accounting balance for the specified account according to
        Wizard settings.

        Flags every processed move line with consolidated=True, so these move
        lines will not be processed two times in the same consolidation.

        :param account: Recordset of the account
        :param partner: Recordset of partner to distinct

        :return: Balance of the account
        """
        domain = [('company_id', '=', account.company_id.id),
                  ('account_id', '=', account.id),
                  ('date', '<=', self._get_month_last_date()),
                  ('consolidated', '!=', True)]

        if partner:
            domain.append(('partner_id', '=', partner.id))

        move_lines = self.env['account.move.line'].sudo().search(domain)

        if self.target_move == 'posted':
            move_lines = move_lines.filtered(lambda l:
                                             l.move_id.state == 'posted')
        if move_lines:
            _logger.debug('Move lines processed : %s ' % move_lines.ids)
            self.env.cr.execute(
                'UPDATE account_move_line SET consolidated = True '
                'WHERE id IN %s;', [tuple(move_lines.ids)])

        return sum([l.balance for l in move_lines])

    def _prepare_consolidate_account(self, holding_account, profile,
                                     partner=False):
        """
        Prepare a dictionnary for each move lines to generate.

        :param holding_account: Recordset of the account to consolidate
                                (on the holding), the method will
                                find the subsidiary's corresponding accounts
        :param profile: Recordset of the subsidiary profile to consolidate
        :param partner: Recordset of partner to distinct

        :return: Dictionnary to create move lines
        """

        _logger.debug('Consolidating subsidiary %s on holding account %s' % (
            profile.sub_company_id.name, holding_account.name)
        )

        account_obj = self.env['account.account']

        subs_accounts = account_obj.search(
            [('company_id', '=', profile.sub_company_id.id),
             ('consolidation_account_id', '=', holding_account.id)])

        if not subs_accounts:
            # an account may exist on the holding and not be used as
            # consolidation account in the subsidiaries,
            # nothing to do
            _logger.debug(
                'No accounts found on %s mapped to holding account %s' % (
                    profile.sub_company_id.name, holding_account.name)
            )
            return False

        vals = {
            'name': _("Consolidation (%s %s)") % (dict(MONTHS)[self.month],
                                                  self.year),
            'account_id': holding_account.id
        }
        sub_balance = 0
        for account in subs_accounts:
            balance = self.get_account_balance(account, partner)
            if not balance:
                continue
            else:
                sub_balance += balance

        if not sub_balance:
            _logger.debug(
                'Accounts mapped to holding account %s were found '
                'on %s but balance is null.' % (holding_account.name,
                                                profile.sub_company_id.name)
            )
            return False

        if partner:
            vals.update({'consol_partner_id': partner.id})

        conso_percentage = profile.consolidation_percentage / 100
        conso_balance = sub_balance * conso_percentage

        holding_currency = holding_account.company_id.currency_id
        subsidiary_currency = account.company_id.currency_id

        # If holding and subsidiary account are in the same currency
        # We can use the subsidiary account balance without conversion
        if holding_currency == subsidiary_currency:
            vals.update({
                'debit': conso_balance if conso_balance > 0.0 else 0.0,
                'credit':
                    abs(conso_balance) if conso_balance < 0.0 else 0.0,
            })
        else:
            # If holding and subsidiary account are in different currencies
            # we use monthly rate for P&L accounts and spot rate for
            # Balance sheet accounts

            if not holding_account.user_type_id.include_initial_balance:
                subsidiary_currency = subsidiary_currency.with_context(
                    monthly_rate=True)
                rate = subsidiary_currency.with_context(
                    date=self._get_month_last_date()).monthly_rate
                rate_text = _('monthly rate : %s') % (
                    subsidiary_currency.round(rate))
            else:
                rate = subsidiary_currency.with_context(
                    date=self._get_month_last_date()).rate
                rate_text = _('spot rate : %s') % (
                    subsidiary_currency.round(rate))

            currency_value = subsidiary_currency._convert(
                conso_balance, holding_currency,
                self.env.user.company_id, self._get_month_last_date()
            )

            vals.update({
                'currency_id': subsidiary_currency.id,
                'amount_currency': conso_balance,
                'debit': currency_value if currency_value > 0.0 else 0.0,
                'credit': abs(
                    currency_value) if currency_value < 0.0 else 0.0,
                'name': '%s - %s' % (vals['name'], rate_text)
            })
        return vals

    def consolidate_subsidiary(self, profile):
        """
        Consolidate one subsidiary on the Holding according to its profile.

        Create a move per subsidiary and a move line per account.
        If intercompany partners were used, extra move lines will be generated
        per partner and account.

        :param profile: Recordset of the consolidation profile of the
                        subsidiary to consolidate on the holding

        :return: Recordset of the created move
        """
        _logger.debug(
            'Consolidating subsidiary %s.' % profile.sub_company_id.name)
        holding_accounts = self.env['account.account'].search(
            [('company_id', '=', self.company_id.id)])

        move_vals = {
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'consol_company_id': profile.sub_company_id.id,
            'ref': _('Consolidation'),
            'date': self._get_month_last_date()
        }

        intercompany_partners = self._get_intercompany_partners(
            profile.sub_company_id)

        move_lines_to_generate = []
        _logger.debug('Consolidating intercompany transactions on %s' %
                      profile.sub_company_id.name)
        for account in holding_accounts:
            # prepare a move line per partner/account
            for partner in intercompany_partners:
                move_line_vals = self._prepare_consolidate_account(
                    account, profile, partner)

                if move_line_vals:
                    move_line_vals.update({
                        'journal_id': self.journal_id.id,
                        'company_id': self.company_id.id,
                        'date': self._get_month_last_date(),
                    })
                    move_lines_to_generate.append(move_line_vals)
        _logger.debug('Consolidating transactions on %s' %
                      profile.sub_company_id.name)
        for account in holding_accounts:
            # prepare a move line per account
            move_line_vals = self._prepare_consolidate_account(
                account, profile)

            if move_line_vals:
                move_line_vals.update({
                    'journal_id': self.journal_id.id,
                    'company_id': self.company_id.id,
                    'date': self._get_month_last_date(),
                })
                move_lines_to_generate.append(move_line_vals)

        # Now that all move lines are processed we reset the flag of processed
        # accounts
        self.env.cr.execute(
            'UPDATE account_move_line SET consolidated = False '
            'WHERE consolidated = True;'
        )

        if move_lines_to_generate:

            # reverse previous entries if it wasn't done before
            self.reverse_moves(profile.sub_company_id)

            # prepare a rate difference move line
            move_line_vals = self._prepare_rate_difference_line(
                move_lines_to_generate)
            if move_line_vals:
                move_line_vals.update({
                    'journal_id': self.journal_id.id,
                    'company_id': self.company_id.id,
                    'date': self._get_month_last_date(),
                })
                move_lines_to_generate.append(move_line_vals)

            # Create the move with all the move lines
            move_vals.update({'line_ids': [
                (0, False, vals) for vals in move_lines_to_generate]})
            return self.env['account.move'].create(move_vals)
        else:
            # Return an empty recordset if there is no move to generate
            return self.env['account.move']

    def run_consolidation(self):
        """Consolidate.

        Consolidate selected subsidiaries according to consolidation profiles
        onto the Holding accounts.

        :return: dict to open an Items view filtered on the created move lines
        """
        super().run_consolidation()

        created_moves = self.env['account.move']

        # Ensure no move line flag is wrongly set from a previous consolidation
        # SQL is required here to ensure it's executed before searching each
        # AML balances
        self.env.cr.execute(
            'UPDATE account_move_line SET consolidated = False '
            'WHERE consolidated = True;')
        for profile in self.consolidation_profile_ids:
            created_moves |= self.consolidate_subsidiary(profile)

        if created_moves:

            # Created moves have to be reversed on the next consolidation
            created_moves.write({
                'auto_reverse': True,
            })

            return {
                'name': _('Consolidation Items'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move.line',
                'domain': [('id', 'in', created_moves.mapped('line_ids').ids)],
            }
        else:
            raise ValidationError(
                _('Could not generate any consolidation entries.'))
