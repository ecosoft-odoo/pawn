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

    # SAMPLE ONLY
    def _set_date_id(self, cr, uid, id, field, value, arg, context=None):
        if value:
            date = self.pool.get('pawn.jor6.wizard.date').browse(cr, uid, value).date_order
            self.write(cr, uid, [id], {'date': date}, context=context)

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
    # END SAMPLE
    
    _columns = {
        'pawn_shop_id': fields.many2one('pawn.shop', 'Pawnshop', required=True),
        'journal_id': fields.many2one('account.journal', 'Journal', domain=[('type', '=', 'cash'), ('pawn_journal', '=', True)], required=True),
        'pawn_rule_id': fields.many2one('pawn.rule', 'Pawn Rule', required=True),
        'report_from_date': fields.date('Date From', required=True),
        'report_to_date': fields.date('Date To', required=True),
        'announce_date': fields.date('Announce Date', required=True),
        'reposessed_date': fields.date('Reposessed Date', required=True),
        # SAMPLE ONLY
        'date_id': fields.function(_get_date_id, fnct_inv=_set_date_id, fnct_search=_search_date_id,
                                   string='Date', type='many2one', relation='pawn.jor6.wizard.date',),
        'date': fields.date(string='Date')
        # END SAMPLE
    }
    _defaults = {
        'pawn_shop_id': _get_pawn_shop_id,
        'pawn_rule_id': _get_pawn_rule_id,
        'report_from_date': lambda self,c,u,ctx={}: (datetime.strptime(fields.date.context_today(self,c,u,context=ctx), '%Y-%m-%d') - relativedelta(days=10)).strftime('%Y-%m-%d'),
        'report_to_date': lambda self,c,u,ctx={}: (datetime.strptime(fields.date.context_today(self,c,u,context=ctx), '%Y-%m-%d') - relativedelta(days=1)).strftime('%Y-%m-%d'),
        'announce_date': fields.date.context_today,
        'reposessed_date': lambda self,c,u,ctx={}: (datetime.strptime(fields.date.context_today(self,c,u,context=ctx), '%Y-%m-%d') + relativedelta(months=1)).strftime('%Y-%m-%d'),        
    }
    
    # SAMPLE ONLY
    def onchange_journal_id(self, cr, uid, ids, journal_id, context=None):
        return {'domain': {'date_id': [('journal_id', '=', journal_id)]}}
    # --

    def start_report(self, cr, uid, ids, data, context=None):
        for wiz_obj in self.read(cr, uid, ids):
            if 'form' not in data:
                data['form'] = {}
            data['form']['pawn_shop_id'] = wiz_obj['pawn_shop_id'][0]
            data['form']['journal_id'] = wiz_obj['journal_id'][0]
            data['form']['pawn_rule_id'] = wiz_obj['pawn_rule_id'][0]
            data['form']['report_from_date'] = wiz_obj['report_from_date']
            data['form']['report_to_date'] = wiz_obj['report_to_date']
            # SAMPLE ONLY
            print 'Getting the Date form Wizard'
            print wiz_obj['date']
            # END SAMPLE
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'pawn_jor6_report',
                'datas': data,
            }

pawn_jor6_wizard()


#### SAMPLE ONLY ####

class pawn_jor6_wizard_date(osv.osv):
    _name = "pawn.jor6.wizard.date"
    _description = "Date for Jor6"
    _auto = False
    _rec_name = 'date_order'

    _columns = {
        'journal_id': fields.many2one('account.journal', 'Journal'),
        'date_order': fields.date('Date'),
    }
    _order = 'date_order'

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            select row_number() over (order by date_order asc) id, *
            from
            (select distinct journal_id, date_order from pawn_order) a
        )"""% (self._table,))

pawn_jor6_wizard_date()

# END SAMPLE