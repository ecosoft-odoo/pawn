# -*- encoding: utf-8 -*-
from openerp.osv import fields, osv
from dateutil.relativedelta import relativedelta
from datetime import datetime
import time
from openerp import tools


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

    def _set_date_id(self, cr, uid, id, field, value, arg, context=None):
        if value:
            date = self.pool.get('pawn.jor6.wizard.date').browse(cr, uid, value).date_jor6
            self.write(cr, uid, [id], {'date': date}, context=context)
            if field == 'jor6_to_submit_date_id':
                self.write(cr, uid, [id], {'jor6_submitted': False}, context=context)
            else:
                self.write(cr, uid, [id], {'jor6_submitted': True}, context=context)

    def _get_date_id(self, cr, uid, ids, field_names, arg=None, context=None):
        res =  dict.fromkeys(ids, False)
        return res

    def _search_date_id(self, cr, uid, obj, name, args, domain=None, context=None):
        if not len(args):
            return []
        ids = []
        for arg in args:
            if arg[1] == '=':
                if arg[2]:
                    cr.execute("""
                        select id from pawn_jor6_wizard_date
                        where journal_id = %s
                    """, (arg[2],))
                ids = map(lambda x: x[0], cr.fetchall())
        return [('id', 'in', [id for id in ids])]

    _columns = {
        'pawn_shop_id': fields.many2one('pawn.shop', 'Pawnshop', required=True),
        'journal_id': fields.many2one('account.journal', 'Journal', domain=[('type', '=', 'cash'), ('pawn_journal', '=', True)], required=True),
        'pawn_rule_id': fields.many2one('pawn.rule', 'Pawn Rule', required=True),
        'jor6_to_submit_date_id': fields.function(_get_date_id, fnct_inv=_set_date_id, fnct_search=_search_date_id,
                                   string='Jor6 To-Submit Date', type='many2one', relation='pawn.jor6.wizard.date',),
        'jor6_submitted_date_id': fields.function(_get_date_id, fnct_inv=_set_date_id, fnct_search=_search_date_id,
                                   string='Jor6 Submitted Date', type='many2one', relation='pawn.jor6.wizard.date',),
        'jor6_submitted': fields.boolean('Jor6 Submitted?'),
        'date': fields.date(string='Date')
    }
    _defaults = {
        'pawn_shop_id': _get_pawn_shop_id,
        'pawn_rule_id': _get_pawn_rule_id,
    }

    def onchange_parameter(self, cr, uid, ids, journal_id, pawn_shop_id, pawn_rule_id, context=None):
        return {'domain': {
                    'jor6_to_submit_date_id': [('journal_id', '=', journal_id),('pawn_shop_id', '=', pawn_shop_id),('pawn_rule_id', '=', pawn_rule_id),('jor6_submitted','=', False)],
                    'jor6_submitted_date_id': [('journal_id', '=', journal_id),('pawn_shop_id', '=', pawn_shop_id),('pawn_rule_id', '=', pawn_rule_id),('jor6_submitted','=', True)]
                    }
                }

    def start_report(self, cr, uid, ids, data, context=None):
        for wiz_obj in self.read(cr, uid, ids):
            if 'form' not in data:
                data['form'] = {}
            data['form']['pawn_shop_id'] = wiz_obj['pawn_shop_id'][0]
            data['form']['journal_id'] = wiz_obj['journal_id'][0]
            data['form']['pawn_rule_id'] = wiz_obj['pawn_rule_id'][0]
            data['form']['report_date'] = wiz_obj['date']
            if not wiz_obj['jor6_submitted']:
                cr.execute("""
                    update pawn_order set jor6_submitted = true
                    where pawn_shop_id = %s
                    and journal_id = %s
                    and rule_id = %s
                    and date_jor6 = %s """, (wiz_obj['pawn_shop_id'][0], wiz_obj['journal_id'][0], wiz_obj['pawn_rule_id'][0], wiz_obj['date']))
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'pawn_jor6_report_xls' if data.get('xls_export') else 'pawn_jor6_report',
                'datas': data,
            }

pawn_jor6_wizard()

class pawn_jor6_wizard_date(osv.osv):
    _name = "pawn.jor6.wizard.date"
    _description = "Date for Jor6"
    _auto = False
    _rec_name = 'date_jor6'

    _columns = {
        'pawn_shop_id': fields.many2one('pawn.shop', 'Pawnshop'),
        'journal_id': fields.many2one('account.journal', 'Journal'),
        'pawn_rule_id': fields.many2one('pawn.rule', 'Pawn Rule'),
        'jor6_submitted': fields.boolean('Jor6 submitted'),
        'date_jor6': fields.date('Date'),
    }
    _order = 'date_jor6'

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            select row_number() over (order by date_jor6 asc) id, *
            from
            (select distinct pawn_shop_id, journal_id, rule_id as pawn_rule_id, coalesce(jor6_submitted, false) as jor6_submitted, date_jor6
                from pawn_order where date_jor6 is not null) a
        )"""% (self._table,))

pawn_jor6_wizard_date()
