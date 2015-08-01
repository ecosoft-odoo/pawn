# -*- encoding: utf-8 -*-
from openerp.osv import fields, osv
from dateutil.relativedelta import relativedelta
from datetime import datetime
import time


class pawn_jor6_wizard(osv.osv_memory):

    _name = 'pawn.jor6.wizard'

    def _get_pawn_shop_id(self, cr, uid, context=None):
        shop_obj = self.pool.get('pawn.shop')
        shop_ids = shop_obj.search(cr, uid, [])
        return shop_ids and shop_ids[0] or False

    def _get_pawn_rule_id(self, cr, uid, context=None):
        rule_obj = self.pool.get('pawn.rule')
        rule_ids = rule_obj.search(cr, uid, [])
        return rule_ids and rule_ids[0] or False

    _columns = {
        'pawn_shop_id': fields.many2one('pawn.shop', 'Pawnshop', required=True),
        'journal_id': fields.many2one('account.journal', 'Journal', domain=[('type', '=', 'cash'), ('pawn_journal', '=', True)], required=True),
        'pawn_rule_id': fields.many2one('pawn.rule', 'Pawn Rule', required=True),
        'report_from_date': fields.date('Date From', required=True),
        'report_to_date': fields.date('Date To', required=True),
        'announce_date': fields.date('Announce Date', required=True),
        'reposessed_date': fields.date('Reposessed Date', required=True),
    }
    _defaults = {
        'pawn_shop_id': _get_pawn_shop_id,
        'pawn_rule_id': _get_pawn_rule_id,
        'report_from_date': lambda self,c,u,ctx={}: (datetime.strptime(fields.date.context_today(self,c,u,context=ctx), '%Y-%m-%d') - relativedelta(days=10)).strftime('%Y-%m-%d'),
        'report_to_date': lambda self,c,u,ctx={}: (datetime.strptime(fields.date.context_today(self,c,u,context=ctx), '%Y-%m-%d') - relativedelta(days=1)).strftime('%Y-%m-%d'),
        'announce_date': fields.date.context_today,
        'reposessed_date': lambda self,c,u,ctx={}: (datetime.strptime(fields.date.context_today(self,c,u,context=ctx), '%Y-%m-%d') + relativedelta(months=1)).strftime('%Y-%m-%d'),        
    }

    def start_report(self, cr, uid, ids, data, context=None):
        for wiz_obj in self.read(cr, uid, ids):
            if 'form' not in data:
                data['form'] = {}
            data['form']['pawn_shop_id'] = wiz_obj['pawn_shop_id'][0]
            data['form']['journal_id'] = wiz_obj['journal_id'][0]
            data['form']['pawn_rule_id'] = wiz_obj['pawn_rule_id'][0]
            data['form']['report_from_date'] = wiz_obj['report_from_date']
            data['form']['report_to_date'] = wiz_obj['report_to_date']
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'pawn_jor6_report',
                'datas': data,
            }

pawn_jor6_wizard()
