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

class pawn_interest_report(osv.osv):
    _name = "pawn.interest.report"
    _description = "Pawn Interest Statistics"
    _auto = False
    _columns = {
        'name': fields.char('Pawn Ticket', readonly=True),
        'date_order': fields.date('Pawn Date', readonly=True),
        'date_expire': fields.date('Expired Date', readonly=True),
        'date_due': fields.date('Grace Period End Date', readonly=True),
        'date_redeem': fields.date('Redeem Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month': fields.selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
            ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'), ('09', 'September'),
            ('10', 'October'), ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True),
        'pawn_shop_id': fields.many2one('pawn.shop', 'Shop', readonly=True),
        'user_id': fields.many2one('res.users', 'Responsible', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Customer', readonly=True),
        'amount_estimated': fields.float('Estimated Amount', readonly=True),
        'amount_pawned': fields.float('Pawned Amount', readonly=True),
        'original_interest': fields.float('Interest Before Discount', readonly=True),
        'amount_interest': fields.float('Net Interest Amount', readonly=True),
        'percent_interest': fields.char('Net Interest (%)', readonly=True),  # Make it char field to not displayed as sum in group by
        'description': fields.char('Description', readonly=True),
        'quantity': fields.float('Quantity', readonly=True),
    }
    _order = 'name'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'pawn_interest_report')
        cr.execute("""
            create or replace view pawn_interest_report as (
                select pawn.*,
                    to_char(pawn.date_order, 'YYYY') as year,
                    to_char(pawn.date_order, 'MM') as month,
                    to_char(pawn.date_order, 'YYYY-MM-DD') as day,
                    product_template.description,
                    pawn_line.quantity,
                    round((case when pawn.amount_pawned is null then 100.0 else (pawn.amount_interest / pawn.amount_pawned) * 100.0 end)::numeric, 2)::varchar as percent_interest
                from
                (select po.id,
                    po.name,
                    po.journal_id,
                    po.pawn_shop_id,
                    po.user_id,
                    po.partner_id,
                    po.date_order,
                    po.date_redeem,
                    po.date_expired,
                    po.date_due,
                    po.amount_total as amount_estimated,
                    po.amount_pawned,
                    sum(coalesce(pai.interest_amount, 0.0) + coalesce(pai.discount, 0.0) - coalesce(pai.addition, 0.0)) as original_interest,
                    sum(coalesce(pai.interest_amount, 0.0)) as amount_interest
                from pawn_order po
                left outer join pawn_actual_interest pai on pai.pawn_id = po.id
                where po.state = 'redeem'
                group by po.id,
                    po.name,
                    po.journal_id,
                    po.pawn_shop_id,
                    po.user_id,
                    po.partner_id,
                    po.date_order,
                    po.date_redeem,
                    po.date_expired,
                    po.date_due,
                    po.amount_pawned) pawn
                left outer join
                (select pt.order_id, pp.item_description as description
                from product_template pt
                join product_product pp on pp.product_tmpl_id = pt.id
                where pt.type = 'pawn_asset') product_template
                    on product_template.order_id = pawn.id
                left outer join
                (select order_id, sum(product_qty) as quantity
                from pawn_order_line
                group by order_id) pawn_line on pawn.id = pawn_line.order_id
            )
        """)
pawn_interest_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
