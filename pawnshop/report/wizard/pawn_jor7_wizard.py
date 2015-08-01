# -*- encoding: utf-8 -*-
from openerp.osv import fields, osv
from dateutil.relativedelta import relativedelta
from datetime import datetime
import time


class pawn_jor7_wizard(osv.osv_memory):

    _name = 'pawn.jor7.wizard'

    def _get_pawn_shop_id(self, cr, uid, context=None):
        shop_obj = self.pool.get('pawn.shop')
        shop_ids = shop_obj.search(cr, uid, [])
        return shop_ids and shop_ids[0] or False
    
    def _get_period(self, cr, uid, context=None):
        """Return default period value"""
        ctx = dict(context or {}, account_period_prefer_normal=True)
        period_ids = self.pool.get('account.period').find(cr, uid, context=ctx)
        return period_ids and period_ids[0] or False

    _columns = {
        'report_type': fields.selection([('pawn_jor71_report', 'Page 1'), ('pawn_jor72_report', 'Page 2')], 'Report Type', required=True),
        'journal_id': fields.many2one('account.journal', 'Journal', domain=[('type', '=', 'cash'), ('pawn_journal', '=', True)], required=True),
        'pawn_shop_id': fields.many2one('pawn.shop', 'Pawnshop', required=True),
        'period_id': fields.many2one('account.period', 'Period', required=True),
    }
    _defaults = {
        'pawn_shop_id': _get_pawn_shop_id,
        'period_id': _get_period
    }

    def start_report(self, cr, uid, ids, data, context=None):
        for wiz_obj in self.read(cr, uid, ids):
            if 'form' not in data:
                data['form'] = {}
            data['form']['journal_id'] = wiz_obj['journal_id'][0]
            data['form']['pawn_shop_id'] = wiz_obj['pawn_shop_id'][0]
            data['form']['period_id'] = wiz_obj['period_id'][0]
            return {
                'type': 'ir.actions.report.xml',
                'report_name': wiz_obj['report_type'],
                'datas': data,
            }

pawn_jor7_wizard()
