# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#     Copyright (C) 2012 Cubic ERP - Teradata SAC (<http://cubicerp.com>).
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
import time
from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class account_transfer(osv.osv):

    _inherit = 'account.transfer'
    
    def _get_default_shop_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company_id = context.get('company_id', user.company_id.id)
        shop_ids = self.pool.get('pawn.shop').search(cr, uid, [('company_id', '=', company_id), ('user_ids', 'in', uid)], context=context)
        return shop_ids and shop_ids[0] or False

    def _get_balance_by_shop(self, cr, src_journal, dst_journal, company, pawn_shop_id):
        # Source
        sql = """select coalesce(sum(debit),0) - coalesce(sum(credit), 0)
            from account_move_line where account_id=%s and pawn_shop_id=%s"""
        params = (src_journal.default_debit_account_id.id, pawn_shop_id)
        if src_journal.profit_center:
            sql += " and profit_center=%s"
            params += (src_journal.profit_center,)
        cr.execute(sql, params)
        src_balance = cr.fetchone()[0] or 0.0
        # Destination        
        sql = """select coalesce(sum(debit),0) - coalesce(sum(credit), 0)
            from account_move_line where account_id=%s and pawn_shop_id=%s"""
        params = (dst_journal.default_debit_account_id.id, pawn_shop_id)
        if dst_journal.profit_center:
            sql += " and profit_center=%s"
            params += (dst_journal.profit_center,)
        cr.execute(sql, params)
        dst_balance = cr.fetchone()[0] or 0.0
        return (src_balance, dst_balance)

    # Overwrite
    def _balance(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for trans in self.browse(cr, uid, ids, context=context):
            if trans.pawn_shop_id: # Additional Method
                src_balance, dst_balance = self._get_balance_by_shop(cr, trans.src_journal_id, trans.dst_journal_id, trans.company_id, trans.pawn_shop_id.id)
            else:
                src_balance, dst_balance = self._get_balance(trans.src_journal_id, trans.dst_journal_id, trans.company_id)
            exchange = False
            if trans.dst_journal_id.currency.id != trans.src_journal_id.currency.id:
                exchange = True
            res[trans.id] = {
                    'src_balance': src_balance,
                    'dst_balance': dst_balance,
                    'exchange': exchange,
                    'exchange_inv': (trans.exchange_rate and 1.0 / trans.exchange_rate or 0.0)
                }
        return res

    _columns = {
        # docnumber
        'number': fields.integer('Number', select=True, readonly=True),
        # --
        'pawn_shop_id': fields.many2one('pawn.shop', 'Shop', domain="[('company_id','=',company_id)]", readonly=True, required=True, states={'draft': [('readonly', False)]}),
        # Overwrite
        'src_balance': fields.function(_balance, digits_compute=dp.get_precision('Account'), string='Current Source Balance', type='float', readonly=True, multi='balance', help="Include all account moves in draft and confirmed state"),
        'dst_balance': fields.function(_balance, digits_compute=dp.get_precision('Account'), string='Current Destinity Balance', type='float', readonly=True, multi='balance', help="Include all account moves in draft and confirmed state"),
        'exchange': fields.function(_balance, string='Have Exchange', type='boolean', readonly=True, multi='balance'),
        'exchange_inv': fields.function(_balance, string='1 / Exchange Rate', type='float', digits_compute=dp.get_precision('Exchange'), readonly=True, multi='balance'),
        # --
    }
    _defaults = {
        #'pawn_shop_id': _get_default_shop_id
    }
    _order = 'id desc'
    
    def _get_next_name(self, cr, uid, date, pawn_shop_id, context=None):
        year = date and date[:4] or time.strftime('%Y-%m-%d')[:4]
        # Get year from date
        cr.execute("""select coalesce(max(number), 0) from account_transfer
            where to_char(date, 'YYYY') = %s and pawn_shop_id = %s""", 
            (year, pawn_shop_id))
        number = cr.fetchone()[0] or 0
        number += 1
        shop_code = self.pool.get('pawn.shop').browse(cr, uid, pawn_shop_id).tr_code or '--'
        next_name = shop_code + '/' + year + '/' + str(number).zfill(3)     
        return next_name, number

    def create(self, cr, uid, vals, context=None):
        if vals.get('name', '/') == '/':
            name, number = self._get_next_name(cr, uid, vals.get('date', False), vals.get('pawn_shop_id', False), context=context)
            vals.update({'name': name, 'number': number})
        return super(account_transfer, self).create(cr, uid, vals, context=context)

    def copy(self, cr, uid, id, defaults, context=None):
        raise osv.except_osv(_('User Error!'), _('Duplication is not allowed!'))
    
    def action_confirm(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # Do not allow transfer between pawn shop and Bank
        for transfer in self.browse(cr, uid, ids, context=context):
#             if (transfer.src_journal_id.pawn_journal or transfer.dst_journal_id.pawn_journal) and \
#                 (transfer.src_journal_id.type == 'bank' or transfer.dst_journal_id.type == 'bank'):
#                 raise osv.except_osv(_('Transfer Error!'), _("You can not transfer between Pawnshop's Cash Operation and Bank"))
            if (transfer.src_journal_id.profit_center and transfer.dst_journal_id.profit_center) and \
                (transfer.src_journal_id.profit_center != transfer.dst_journal_id.profit_center):
                raise osv.except_osv(_('Transfer Error!'), _("You can not transfer between different profit center"))
        return super(account_transfer, self).action_confirm(cr, uid, ids, context=context)

    def action_done(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context.update({'is_account_transfer': True,
                        'transfer_id': ids[0]})
        return super(account_transfer, self).action_done(cr, uid, ids, context=context)

    def onchange_journal_shop(self, cr, uid, ids, src_journal_id, dst_journal_id, date, exchange_rate, src_amount, pawn_shop_id):
        res = {'value': {}}
        if not(src_journal_id and dst_journal_id):
            return res
        src_journal = self.pool.get('account.journal').browse(cr, uid, src_journal_id)
        dst_journal = self.pool.get('account.journal').browse(cr, uid, dst_journal_id)
        if not pawn_shop_id:
            res['value']['src_balance'], res['value']['dst_balance'] = self._get_balance(src_journal, dst_journal, src_journal.company_id)
        else:
            res['value']['src_balance'], res['value']['dst_balance'] = self._get_balance_by_shop(cr, src_journal, dst_journal, src_journal.company_id,pawn_shop_id)
        res['value']['exchange'] = (src_journal.currency.id != dst_journal.currency.id)
        res['value']['src_have_partner'], res['value']['dst_have_partner'] = src_journal.have_partner, dst_journal.have_partner
        res['value']['exchange_rate'] = exchange_rate
        if res['value']['exchange']:
            res['value']['exchange_rate'] = (src_journal.currency and src_journal.currency.rate or src_journal.company_id.currency_id.rate) and ((dst_journal.currency and dst_journal.currency.rate or dst_journal.company_id.currency_id.rate) / (src_journal.currency and src_journal.currency.rate or src_journal.company_id.currency_id.rate)) or 0.0
        else:
            res['value']['exchange_rate'] = 1.0
        res['value']['exchange_inv'] = res['value']['exchange_rate'] and (1.0 / res['value']['exchange_rate']) or 0.0
        res['value']['dst_amount'] = res['value']['exchange_rate'] * src_amount
        return res

account_transfer()
