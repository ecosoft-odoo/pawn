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

from openerp.osv import fields, osv


class account_move_line(osv.osv):

    _inherit = 'account.move.line'

    def _get_profit_center(self, cr, uid, context=None):
        if context is None:
            context = {}
        journal_id = context.get('journal_id', False)
        if journal_id:
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
            return journal.profit_center
        return False

    _columns = {
        'pawn_order_id': fields.many2one('pawn.order', 'Pawn Ticket', required=False, select=True),
        'pawn_shop_id': fields.many2one('pawn.shop', 'Pawn Shop', required=True),
        'profit_center': fields.selection([(1, '1'), (2, '2')], 'Profit Center', required=False, help="Profit Center will be posted in account move line"),
    }
    _defaults = {
        'profit_center': _get_profit_center
    }

    # On create of account move line add special fields, if not yet assigned.
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals.get('product_id', False):
            product_obj = self.pool.get('product.product')
            pawn_order = product_obj.browse(cr, uid, vals.get('product_id'), context=context).order_id
            vals.update({
                'pawn_order_id': pawn_order and pawn_order.id or False,
                'pawn_shop_id': pawn_order.pawn_shop_id and pawn_order.pawn_shop_id.id or False,
                'profit_center': pawn_order.journal_id and pawn_order.journal_id.profit_center or False,
            })
        # For cash register case, get pawn_shop_id and profit center from Cash Register
        if context.get('is_cash_register', False):
            statement_obj = self.pool.get('account.bank.statement')
            statement = statement_obj.browse(cr, uid, vals.get('statement_id'), context=context)
            vals.update({
                'pawn_order_id': False,
                'pawn_shop_id': statement.pawn_shop_id.id,
                'profit_center': statement.journal_id.profit_center,
            })
        # For cash register case, get pawn_shop_id and profit center from Accunt Transfer
        if context.get('is_account_transfer', False):
            voucher_obj = self.pool.get('account.voucher')
            transfer_obj = self.pool.get('account.transfer')
            voucher = voucher_obj.browse(cr, uid, context.get('voucher_id'), context=context)
            transfer = transfer_obj.browse(cr, uid, context.get('transfer_id'), context=context)
            vals.update({
                'pawn_order_id': False,
                'pawn_shop_id': transfer.pawn_shop_id.id,
                'profit_center': voucher.journal_id.profit_center,
            })
        res = super(account_move_line, self).create(cr, uid, vals, context=context)
        return res

account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
