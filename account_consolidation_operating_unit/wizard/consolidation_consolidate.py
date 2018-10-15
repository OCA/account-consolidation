# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class AccountConsolidationConsolidate(models.TransientModel):

    _inherit = 'account.consolidation.consolidate'

    def _prepare_ml_partner_analytic_operating_unit(self, account, profile):
        mls_to_generate = []
        intercompany_partners = self._get_intercompany_partners(
            profile.sub_company_id)
        for partner in intercompany_partners:
            analytic_accounts = self.env['account.analytic.account'].search([
                ('company_id', '=', profile.sub_company_id.id)
            ])
            for analytic in analytic_accounts:
                operating_units = self.env['operating.unit'].search([
                    ('company_id', '=', profile.sub_company_id.id)
                ])
                for op_unit in operating_units:
                    domain = [
                        ('partner_id', '=', partner.id),
                        ('analytic_account_id', '=', analytic.id),
                        ('operating_unit_id', '=', op_unit.id),
                    ]
                    ml_vals = self._prepare_consolidate_account(
                        account, profile, base_domain=domain)
                    if ml_vals:
                        ml_vals.update({
                            'consol_partner_id': partner.id,
                            # FIXME define fields and security rules
                            'consol_analytic_account_id': analytic.id,
                            'consol_operating_unit_id': op_unit.id,
                        })
                        mls_to_generate.append(
                            self._finish_ml_preparation(ml_vals))
        return mls_to_generate

    def _prepare_ml_partner_operating_unit(self, account, profile):
        mls_to_generate = []
        intercompany_partners = self._get_intercompany_partners(
            profile.sub_company_id)
        for partner in intercompany_partners:
            operating_units = self.env['operating.unit'].search([
                ('company_id', '=', profile.sub_company_id.id)
            ])
            for op_unit in operating_units:
                domain = [
                    ('partner_id', '=', partner.id),
                    ('operating_unit_id', '=', op_unit.id),
                ]
                ml_vals = self._prepare_consolidate_account(
                    account, profile, base_domain=domain)
                if ml_vals:
                    ml_vals.update({
                        'consol_partner_id': partner.id,
                        # FIXME define field and security rules
                        'consol_operating_unit_id': op_unit.id,
                    })
                    mls_to_generate.append(
                        self._finish_ml_preparation(ml_vals))
        return mls_to_generate

    def _prepare_ml_analytic_operating_unit(self, account, profile):
        mls_to_generate = []
        analytic_accounts = self.env['account.analytic.account'].search([
            ('company_id', '=', profile.sub_company_id.id)
        ])
        for analytic in analytic_accounts:
            operating_units = self.env['operating.unit'].search([
                ('company_id', '=', profile.sub_company_id.id)
            ])
            for op_unit in operating_units:
                domain = [
                    ('analytic_account_id', '=', analytic.id),
                    ('operating_unit_id', '=', op_unit.id),
                ]
                ml_vals = self._prepare_consolidate_account(
                    account, profile, base_domain=domain)
                if ml_vals:
                    ml_vals.update({
                        # FIXME define fields and security rules
                        'consol_analytic_account_id': analytic.id,
                        'consol_operating_unit_id': op_unit.id,
                    })
                    mls_to_generate.append(
                        self._finish_ml_preparation(ml_vals))
        return mls_to_generate

    def _prepare_ml_operating_unit(self, account, profile):
        mls_to_generate = []
        operating_units = self.env['operating.unit'].search([
            ('company_id', '=', profile.sub_company_id.id)
        ])
        for op_unit in operating_units:
            domain = [
                ('operating_unit_id', '=', op_unit.id),
            ]
            ml_vals = self._prepare_consolidate_account(
                account, profile, base_domain=domain)
            if ml_vals:
                ml_vals.update({
                    # FIXME define fields and security rules
                    'consol_operating_unit_id': op_unit.id,
                })
                mls_to_generate.append(
                    self._finish_ml_preparation(ml_vals))
        return mls_to_generate

    def _get_prepare_function(self, distinctions):
        # TODO improve me ?
        if 'operating_units' not in distinctions:
            return super()._get_prepare_function(distinctions)
        else:
            if 'interco_partners' in distinctions:
                if 'analytic_accounts' in distinctions:
                    return self._prepare_ml_partner_analytic_operating_unit
                else:
                    return self._prepare_ml_partner_operating_unit
            else:
                if 'analytic_accounts' in distinctions:
                    return self._prepare_ml_analytic_operating_unit
                else:
                    return self._prepare_ml_operating_unit
