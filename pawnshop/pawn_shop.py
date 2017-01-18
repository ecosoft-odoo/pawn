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


class pawn_shop(osv.osv):
    _name = "pawn.shop"
    _description = "Pawn Shop"

    def _get_ratio(self, cr, uid, ids, field, arg, context=None):
        res = dict.fromkeys(ids, False)
        for shop in self.browse(cr, uid, ids, context=context):
            res[shop.id] = {
                'last_period_ratio': 0.0,
                'overall_ratio': 0.0,
            }
            amount_pawned_1 = 0.0
            amount_pawned_2 = 0.0
            first_line = True
            for period_line in shop.pawn_amount_by_period:
                if first_line:
                    res[shop.id]['last_period_ratio'] = period_line.ratio_1_2
                    first_line = False
                amount_pawned_1 += period_line.amount_pawned_1
                amount_pawned_2 += period_line.amount_pawned_2
            res[shop.id]['overall_ratio'] = amount_pawned_2 > 0 and (amount_pawned_1/amount_pawned_2) * 100 or 100
        return res

    _columns = {
        'name': fields.char('Name', size=128, required=True, select=True),
        'code': fields.char('Pawn Order', size=10, required=True, select=True),
        'tr_code': fields.char('Cash & Bank Transfer', size=10, required=True, select=True),
        'pc_code': fields.char('Cash Register', size=10, required=True, select=True),
        'srec_code': fields.char('Sales Receipt', size=10, required=True, select=True),
        'sref_code': fields.char('Sales Refund', size=10, required=True, select=True),
        'secret_key': fields.char('Secret Key 1', size=4, help=("Secret key is the key requred for cancelling cases of Pawn Ticket")),
        'secret_key2': fields.char('Secret Key 2', size=4, help=("Secret key is the key requred for cancelling cases of Pawn Ticket")),
        'target_ratio': fields.float('1:2 Target Ratio'),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=True),
        'user_ids':fields.many2many('res.users', 'shop_user_rel', 'pawn_shop_id', 'user_id', 'Users'),
        'pawn_amount_by_period': fields.one2many('pawn.amount.by.period', 'pawn_shop_id', 'Pawn Amount by Period', readonly=True,),
        'last_period_ratio': fields.function(_get_ratio, string='Last Period Ratio', multi='ratio'),
        'overall_ratio': fields.function(_get_ratio, string='Overall Ratio', multi='ratio'),
        'reg_book': fields.char('Book', size=64),
        'reg_number': fields.char('Number', size=64),
        'full_address': fields.text('Address'),
        # Implementing new sequences
        'sequence_ids': fields.one2many('pawn.shop.sequence', 'pawn_shop_id', 'Sequences')
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory', context=c),
        'code': '--',
        'tr_code': '--',
        'pc_code': '--',
        'srec_code': '--',
        'sref_code': '--',
    }

pawn_shop()


# Implementing new sequence

class pawn_shop_sequence(osv.osv):
    _name = "pawn.shop.sequence"

    _columns = {
        'type': fields.selection(
            [('pawn_order', 'Pawn Order')],
            'Type',
            required=True,
        ),
        'pawn_shop_id': fields.many2one(
            'pawn.shop', 'Shop',
            required=True,
        ),
        'book': fields.integer(
            'Book',
        ),
        'sequence_id': fields.many2one(
            'ir.sequence',
            'Sequence',
        )
    }


pawn_shop_sequence()

# End implementing new sequence


class pawn_amount_by_period(osv.osv):
    _name = "pawn.amount.by.period"
    _description = "Pawn Amount by Period"
    _auto = False

    _columns = {
        'pawn_shop_id': fields.many2one('pawn.shop', 'Shop', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month': fields.selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
            ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'), ('09', 'September'),
            ('10', 'October'), ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'amount_pawned': fields.float('Pawned Amount', readonly=True),
        'amount_pawned_1': fields.float('Stock 1', readonly=True),
        'amount_pawned_2': fields.float('Stock 2', readonly=True),
        'ratio_1_2': fields.float('% Ratio 1:2', readonly=True),
    }
    _order = 'year, month desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'pawn_amount_by_period')
        cr.execute("""
            create or replace view pawn_amount_by_period as (
                select min(id) id, pawn_shop_id, year, month, sum(amount_pawned) amount_pawned, sum(amount_pawned_1) amount_pawned_1, sum(amount_pawned_2) amount_pawned_2,
                    case when sum(amount_pawned_2) > 0 then (sum(amount_pawned_1)/sum(amount_pawned_2) * 100) else 100 end ratio_1_2
                from pawn_report where state in ('pawn', 'redeem', 'expire')
                group by pawn_shop_id, year, month
            )
        """)

pawn_amount_by_period()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
