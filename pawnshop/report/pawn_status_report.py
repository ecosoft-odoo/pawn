# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import tools
from openerp.osv import fields, osv

class pawn_status_report(osv.osv):
    _name = "pawn.status.report"
    _description = "Pawn Status Statistics"
    _auto = False
    
    def _compute_balance(self, cr, uid, ids, name, args, context=None):
        res = dict.fromkeys(ids, {'begin_balance': 0.0, 'end_balance': 0.0})
        order_period_id = False
        for record in self.browse(cr, uid, ids, context=context):
            if order_period_id != record.order_period_id.id: # Begin new order_period_id
                begin_balance = record.amount
                end_balance = record.amount
                order_period_id = record.order_period_id.id
            end_balance = begin_balance - (record.redeem_amount or 0.0) - (record.expire_amount or 0.0)
            res[record.id] = {
                'begin_balance': begin_balance,
                'end_balance': end_balance,
            }
            begin_balance = end_balance
        return res
    
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True),
        'pawn_shop_id': fields.many2one('pawn.shop', 'Shop', readonly=True),
        'order_period_id': fields.many2one('account.period', 'Pawn Period', readonly=True),
        'history_period_id': fields.many2one('account.period', 'History Period', readonly=True),
        'amount': fields.float('Amount', readonly=True),
        'begin_balance': fields.function(_compute_balance, string='Begin Balance', readonly=True, multi="balance"),
        'end_balance': fields.function(_compute_balance, string='End Balance', readonly=True, multi="balance"),
        'redeem_amount': fields.float('Redeem Amount', readonly=True),    
        'expire_amount': fields.float('Expire Amount', readonly=True),
    }
    _order = 'journal_id, pawn_shop_id, order_period_id, history_period_id'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'pawn_status_report')
        cr.execute("""
            create or replace view pawn_status_report as (
                select (period.journal_id::varchar || period.pawn_shop_id::varchar || period.order_period_id::varchar || period.history_period_id::varchar)::int id,
                    period.journal_id, period.pawn_shop_id, period.order_period_id, period.history_period_id,
                    pawn.amount amount, 
                    redeem.amount redeem_amount, expire.amount expire_amount
                from
                    (select distinct journal_id, pawn_shop_id, pw.period_id order_period_id, psh.period_id history_period_id
                    from pawn_order pw
                    join pawn_status_history psh on psh.order_id = pw.id) period
                left outer join --
                    (select journal_id, pawn_shop_id, period_id order_period_id, sum(amount_pawned) amount
                    from pawn_order where state not in ('draft', 'cancel')
                    group by journal_id, pawn_shop_id, period_id) pawn
                    on period.journal_id = pawn.journal_id and period.pawn_shop_id = pawn.pawn_shop_id and pawn.order_period_id = pawn.order_period_id
                left outer join
                    (select journal_id, pawn_shop_id, period_id, sum(amount_pawned) amount
                    from (select journal_id, pawn_shop_id, psh.period_id, psh.state, pw.amount_pawned
                    from pawn_order pw
                    left outer join pawn_status_history psh on psh.order_id = pw.id and psh.id in
                        (select max(id) from pawn_status_history group by period_id, order_id)
                    where pw.state not in ('draft', 'cancel')
                    order by order_id, psh.period_id) a
                    where a.state = 'redeem'
                    group by journal_id, pawn_shop_id, period_id) redeem 
                    on period.journal_id = redeem.journal_id and period.pawn_shop_id = redeem.pawn_shop_id and period.history_period_id = redeem.period_id
                left outer join
                    (select journal_id, pawn_shop_id, period_id, sum(amount_pawned) amount
                    from (select journal_id, pawn_shop_id, psh.period_id, psh.state, pw.amount_pawned
                    from pawn_order pw
                    left outer join pawn_status_history psh on psh.order_id = pw.id and psh.id in
                        (select max(id) from pawn_status_history group by period_id, order_id)
                    where pw.state not in ('draft', 'cancel')
                    order by order_id, psh.period_id) a
                    where a.state = 'expire'
                    group by journal_id, pawn_shop_id, period_id) expire 
                    on period.journal_id = expire.journal_id and period.pawn_shop_id = expire.pawn_shop_id and period.history_period_id = expire.period_id
            )
        """)
pawn_status_report()
#                 select psh.id, 
#                     pw.id as order_id,
#                     pw.pawn_shop_id,
#                     pw.amount_pawned as pawn_amount,
#                     pw.journal_id, 
#                     pw.date_order, 
#                     pw.period_id, 
#                     psh.write_date as history_date, 
#                     psh.period_id as history_period_id,     
#                     case when coalesce((select state from pawn_status_history where order_id = pw.id 
#                 and psh.write_date < write_date order by id desc limit 1) 
#                 in ('redeem','expire'), false) then 0.0 
#             else pw.amount_pawned end as begin_amount,
#                     psh.state as history_state
#                 from pawn_order pw
#                 left outer join pawn_status_history psh on psh.order_id = pw.id and psh.id in
#                     (select max(id) from pawn_status_history group by period_id, order_id)
#                 where pw.state not in ('draft', 'cancel')
#                 order by order_id, history_period_id 
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
