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


class item_sold_report(osv.osv):
    _name = 'item.sold.report'
    _auto = False

    _columns = {
        'product_id': fields.many2one('product.product', 'Product'),
        'description': fields.char('Description'),
        'partner_id': fields.many2one('res.partner', 'Customer'),
        'sale_receipt_number': fields.char('Sale Receipt Number'),
        'date_sold': fields.date('Date Sold'),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""
            create or replace view {} as (
                select avl.id as id, avl.product_id, avl.name as description, av.partner_id, av.number as sale_receipt_number, av.date as date_sold
                from account_voucher_line avl
                left join account_voucher av on avl.voucher_id = av.id
                left join account_journal aj on av.journal_id = aj.id
                where aj.type in ('sale', 'sale_refund') and av.type = 'sale' and av.state = 'posted'
                order by av.date desc, av.id asc
            )
        """.format(self._table))
