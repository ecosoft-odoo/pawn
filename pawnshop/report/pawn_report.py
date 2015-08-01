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

STATE_SELECTION = [
        ('draft', 'Draft Pawn Ticket'),
        ('pawn', 'Pawned'),
        ('redeem', 'Redeemed'),
        ('expire', 'Expired'),
        ('cancel', 'Cancelled')
    ]

class pawn_report(osv.osv):
    _name = "pawn.report"
    _description = "Pawn Ticket Statistics"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'extended': fields.boolean('Extended', readonly=True),
        'date': fields.date('Pawn Date', readonly=True),
        'date_expired': fields.date('Expired Date', readonly=True),
        'date_redeem': fields.date('Redeem Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month': fields.selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
            ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'), ('09', 'September'),
            ('10', 'October'), ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure', readonly=True),
        'product_uom_qty': fields.float('# of Qty', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Customer', readonly=True),
        'pawn_shop_id': fields.many2one('pawn.shop', 'Shop', readonly=True),
        'amount_estimated': fields.float('Estimated Amount', readonly=True),
        'amount_pawned': fields.float('Pawned Amount', readonly=True),
        'amount_pawned_1': fields.float('Pawned (1)', readonly=True),
        'amount_pawned_2': fields.float('Pawned (2)', readonly=True),
        'categ_id': fields.many2one('product.category','Category of Product', readonly=True),
        'nbr': fields.integer('# of Lines', readonly=True),
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True),
        'profit_center': fields.integer('Profit Center', readonly=True),
    }
    _order = 'date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'pawn_report')
        cr.execute("""
            create or replace view pawn_report as (
                select id, product_uom, product_uom_qty, amount_estimated, amount_pawned, nbr, 
                   case when profit_center = 1 then amount_pawned else 0.0 end as amount_pawned_1,
                   case when profit_center = 2 then amount_pawned else 0.0 end as amount_pawned_2,
                   extended, date, date_expired, date_redeem, year, month, day, partner_id, pawn_shop_id, state, categ_id, profit_center
                   from (
                        select
                            min(l.id) as id,
                            t.uom_id as product_uom,
                            sum(p.product_qty / u.factor * u2.factor) as product_uom_qty,
                            sum(p.product_qty * p.price_estimated) as amount_estimated,
                            sum(p.product_qty * p.price_pawned) as amount_pawned,
                            count(*) as nbr,
                            po.extended as extended,
                            po.date_order as date,
                            po.date_expired as date_expired,
                            po.date_redeem as date_redeem,
                            to_char(po.date_order, 'YYYY') as year,
                            to_char(po.date_order, 'MM') as month,
                            to_char(po.date_order, 'YYYY-MM-DD') as day,
                            po.partner_id as partner_id,
                            po.pawn_shop_id as pawn_shop_id,
                            po.state,
                            t.categ_id as categ_id,
                            j.profit_center as profit_center
                        from
                            pawn_order_line l
                            join pawn_order po on (l.order_id=po.id)
                            join account_journal j on (j.id = po.journal_id)
                            left join product_product p on (l.id=p.order_line_id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                            left join product_uom u on (u.id=l.product_uom)
                            left join product_uom u2 on (u2.id=t.uom_id)
                        group by
                            l.order_id,
                            t.uom_id,
                            t.categ_id,
                            po.extended,
                            po.date_order,
                            po.date_expired,
                            po.date_redeem,
                            po.partner_id,
                            po.pawn_shop_id,
                            po.state,
                            j.profit_center) a
            )
        """)
pawn_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
