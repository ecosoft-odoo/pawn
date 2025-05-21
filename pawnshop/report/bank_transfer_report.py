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


class bank_transfer_report(osv.osv):
    _name = "bank.transfer.report"
    _description = "Bank Transfer Report"
    _auto = False

    _columns = {
        "date": fields.date(
            string="Date",
            readonly=True,
        ),
        "reference": fields.char(
            string="Reference",
            readonly=True,
        ),
        "account_id": fields.many2one(
            "account.account",
            string="Account",
        ),
        "type": fields.selection(
            selection=[
                ("pawn", "Pawn"),
                ("redeem", "Redeem"),
                ("sale", "Sale"),
            ],
            string="Type",
            readonly=True,
        ),
        "amount": fields.float(
            string="Amount",
            readonly=True,
        ),
        "amount_pawned": fields.float(
            string="Amount Pawned",
            readonly=True,
        ),
        "actual_interest": fields.float(
            string="Actual Interest",
            readonly=True,
        )
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""
            create or replace view {} as (
                select row_number() over(order by rp.date, rp.reference, rp.type, rp.account_id) as id, rp.*
                from (
                    -- pawn
                    (
                        select 
                            m.date, 
                            pw.name as reference, 
                            l.account_id,
                            'pawn' as type, 
                            coalesce(sum(l.debit),0) - coalesce(sum(l.credit),0) as amount, 
                            max(pw.amount_pawned) as amount_pawned,
                            NULL::numeric as actual_interest
                        from account_move_line l
                        join account_move m on l.move_id = m.id
                        join pawn_order pw on l.pawn_order_id = pw.id
                        where l.pawn_order_id is not null and (m.id = pw.pawn_move_id or m.adjustment = 'pawn')
                            and l.account_id in (select aa.id from account_account aa join account_account_type aat on aa.user_type = aat.id where aat.code = 'bank')
                        group by m.date, pw.name, l.account_id
                    )
                    union all
                    -- redeem
                    (
                        select 
                            m.date, 
                            pw.name as reference, 
                            l.account_id, 'redeem' as type,
                            coalesce(sum(l.debit),0) - coalesce(sum(l.credit),0) as amount, 
                            max(pw.amount_pawned) as amount_pawned,
                            COALESCE(MAX(pai.interest_total), 0) as actual_interest
                        from account_move_line l
                        join account_move m on l.move_id = m.id
                        join pawn_order pw on l.pawn_order_id = pw.id
                        left join pawn_order child on pw.child_id = child.id
                        left join (
                            select pawn_id, sum(interest_amount) as interest_total
                            from pawn_actual_interest pai
                            group by pawn_id
                        ) pai on pai.pawn_id = pw.id
                        where l.pawn_order_id is not null and pw.state = 'redeem' and (m.id in (pw.redeem_move_id, child.pawn_move_id) or m.adjustment = 'redeem')
                            and l.account_id in (select aa.id from account_account aa join account_account_type aat on aa.user_type = aat.id where aat.code = 'bank')
                        group by m.date, pw.name, l.account_id
                    )
                    union all
                    -- sale
                    (
                        select 
                            m.date, 
                            av.number as reference, 
                            l.account_id, 'sale' as type, 
                            coalesce(sum(l.debit),0) - coalesce(sum(l.credit),0) as amount, 
                            NULL::numeric as amount_pawned,
                            NULL::numeric as actual_interest
                        from account_move_line l
                        join account_move m on l.move_id = m.id
                        left join account_voucher av on m.id = av.move_id or m.sale_receipt_id = av.id
                        left join account_journal aj on av.journal_id = aj.id
                        where ((aj.type in ('sale', 'sale_refund') and av.type = 'sale') or m.adjustment = 'sale_receipt')
                            and l.account_id in (select aa.id from account_account aa join account_account_type aat on aa.user_type = aat.id where aat.code = 'bank')
                        group by m.date, av.number, l.account_id
                   )
                ) rp
                order by rp.date, rp.reference, rp.type, rp.account_id
            )""".format(self._table))
