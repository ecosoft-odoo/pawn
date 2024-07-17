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


class validate_sale_receipt(osv.osv_memory):
    _name = 'validate.sale.receipt'
    _description = 'Validate Sale Receipt'

    def _get_amount(self, cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            voucher = self.pool.get('account.voucher').browse(cr, uid, active_id, context=context)
            return voucher.amount
        return False

    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            voucher = self.pool.get('account.voucher').browse(cr, uid, active_id, context=context)
            return voucher.product_journal_id and voucher.product_journal_id.id or False
        return False

    def _check_amount(self, cr, uid, ids, context=None):
        for wizard in self.browse(cr, uid, ids, context=context):
            # Transfer Amount + Cash Amount must equal to Total Pawn Amount
            if wizard.transfer_amount + wizard.cash_amount != wizard.amount:
                return False
            # Transfer Amount / Cash Amount must greater than zero
            if wizard.transfer_amount < 0 or wizard.cash_amount < 0:
                return False
        return True

    _columns = {
        'amount': fields.float('Amount', readonly=True),
        'bank_journal_id': fields.many2one('account.journal', 'Bank Journal', domain="[('type', '=', 'bank')]", required=True),
        'transfer_amount': fields.float('Transfer Amount'),
        'journal_id': fields.many2one('account.journal', 'Cash Journal', domain="[('type','=','cash'), ('pawn_journal', '=', True)]", required=True, readonly=True),
        'cash_amount': fields.float('Cash Amount'),
    }
    _defaults = {
        'amount': _get_amount,
        'journal_id': _get_journal,
    }
    _constraints = [
        (_check_amount, 'The transfer or cash amount is incorrect !!', ['transfer_amount', 'cash_amount']),
    ]

    def onchange_amount(self, cr, uid, ids, field, transfer_amount, cash_amount, total_amount, context=None):
        res = {'value': {}}
        if field == 'transfer':
            res['value']['cash_amount'] = total_amount - transfer_amount
        elif field == 'cash':
            res['value']['transfer_amount'] = total_amount - cash_amount
        return res

    def action_confirm(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        voucher_obj = self.pool.get('account.voucher')
        if active_id:
            wizard = self.browse(cr, uid, ids[0], context=context)
            context.update({
                'bank_account_id': wizard.bank_journal_id.default_debit_account_id.id,
                'transfer_amount': wizard.transfer_amount,
                'cash_account_id': wizard.journal_id.default_credit_account_id.id,
                'cash_amount': wizard.cash_amount,
            })
            voucher_obj.proforma_voucher(cr, uid, [active_id], context=context)
        return True
