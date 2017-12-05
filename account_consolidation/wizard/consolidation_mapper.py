from odoo import models, fields, api

class ConsolidationMapper(models.TransientModel):

    _name = 'account.consolidation.mapper'

    company_id = fields.Many2one('res.company')
    subsidiary_id = fields.Many2one('res.company')
    mapper_lines = fields.One2many('account.consolidation.mapper.lines', 'mapper_id', string="Accounts Mapping")

    def load_map(self):
        pass

    def load_current_map(self):
        pass

    def load_unmapped(self):
        pass

    def load_by_group(self):
        pass


class ConsolidationMapperLines(models.TransientModel):

    _name = 'account.consolidation.mapper.lines'

    mapping_method = fields.Selection([
        ('usertype', 'By type'),
        ('group', 'By group hierarchy'),
        ('direct', 'Direct mapping')
    ],)

    mapper_id = fields.Many2one('account.consolidation.mapper')
    company_id = fields.Many2one(related='mapper_id.company_id')
    subsidiary_id = fields.Many2one(related='mapper_id.subsidiary_id')
    account_id = fields.Many2one(
        'account.account',
        string="Consolidation account",
        domain="[('company_id', '=', company_id)]"
    )
    consolidated_account_id = fields.Many2one(
        'account.account',
        string="Consolidated accounts",
        domain="[('company_id', '=', subsidiary_id)]"
    )
