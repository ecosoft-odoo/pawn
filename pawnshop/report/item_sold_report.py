##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import fields, osv
from openerp import tools
import openerp.addons.decimal_precision as dp


class item_sold_report(osv.osv):
    _name = 'item.sold.report'
    _order = 'voucher_id desc,id asc'
    _auto = False

    def _get_extended(self, cr, uid, ids, name, args, context=None):
        res = {}
        for report in self.browse(cr, uid, ids, context=context):
            if report.extended:
                res[report.id] = 'x'
            else:
                res[report.id] = ''
        return res

    _columns = {
        'product_id': fields.many2one('product.product', 'Item'),
        'partner_id': fields.many2one('res.partner', 'Customer'),
        'description': fields.char('Description'),
        'date_order': fields.date('Pawn Date'),
        'voucher_id': fields.many2one('account.voucher', 'Sale Receipt'),
        'quantity': fields.float('Item Quantity', digits_compute= dp.get_precision('Product Unit of Measure')),
        'carat': fields.float('Carat'),
        'gram': fields.float('Gram'),
        'total_price_pawned': fields.float('Total Pawned Price', digits_compute=dp.get_precision('Account')),
        'total_price_sold': fields.float('Total Sold Price', digits_compute=dp.get_precision('Account')),
        'total_profit': fields.float('Total Profit', digits_compute=dp.get_precision('Account')),
        'date_sold': fields.date('Date Sold'),
        'extended': fields.boolean('Extended'),
        'extended_x': fields.function(_get_extended, method=True, string='Extended', type='char'),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""
            create or replace view {} as (
                select
                    avl.id as id, avl.product_id, av.partner_id, avl.name as description,
                    pp.date_order, av.id as voucher_id, avl.quantity, avl.carat, avl.gram,
                    coalesce(avl.total_price_pawned, 0) as total_price_pawned, coalesce(avl.amount, 0) as total_price_sold, coalesce(avl.amount, 0) - coalesce(avl.total_price_pawned, 0) as total_profit,
                    av.date as date_sold, pp.extended
                from account_voucher_line avl
                left join account_voucher av on avl.voucher_id = av.id
                left join account_journal aj on av.journal_id = aj.id
                left join product_product pp on avl.product_id = pp.id
                where aj.type in ('sale', 'sale_refund') and av.type = 'sale' and av.state = 'posted'
            )
        """.format(self._table))


item_sold_report()
