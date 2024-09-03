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
from openerp import netsvc
from openerp.tools.translate import _
from openerp.tools import float_compare


class pawn_order_redeem(osv.osv_memory):

    def _get_pawn_amount(self, cr, uid, context=None):
        """ Get pawn amount from pawn order """
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            if pawn:
                return round(pawn.amount_pawned, 2)
        return False

    def _get_interest_amount(self, cr, uid, context=None):
        """ Calculate interest amount from pawn order """
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        pawn_obj = self.pool.get('pawn.order')
        date_redeem = context.get('date_redeem', fields.date.context_today(self, cr, uid, context=context))
        if active_id and date_redeem:
            amount_interest = pawn_obj.calculate_interest_remain(cr, uid, active_id, date_redeem, context=context)
            return round(amount_interest, 2)
        return False

    def _get_redeem_amount(self, cr, uid, context=None):
        """ Compute redeem amount which redeem amount will equal to pawn amount + interest amount """
        return self._get_pawn_amount(cr, uid, context=context) + self._get_interest_amount(cr, uid, context=context)

    def _get_bank_journal_id(self, cr, uid, context=None):
        """ Default bank journal """
        bank_journal_ids = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'bank'), ('pawn_journal', '=', True)], context=context)
        return bank_journal_ids[0] if len(bank_journal_ids) == 1 else False

    def _get_journal(self, cr, uid, context=None):
        """ Default cash journal from pawn order """
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            return pawn.journal_id and pawn.journal_id.id or False
        return False

    def _check_amount(self, cr, uid, ids, context=None):
        """ Check transfer amount / cash amount must greater than zero """
        for wizard in self.browse(cr, uid, ids, context=context):
            # Transfer Amount + Cash Amount must equal to Final Redeeem
            if wizard.transfer_amount + wizard.cash_amount != wizard.redeem_amount:
                return False
            # Transfer Amount / Cash Amount must greater than zero
            if wizard.transfer_amount < 0 or wizard.cash_amount < 0:
                return False
        return True

    _name = "pawn.order.redeem"
    _description = "Redeem"
    _columns = {
        'date_redeem': fields.date('Date', readonly=True),
        'pawn_amount': fields.float('Initial', readonly=True),
        'interest_amount': fields.float('Computed Interest', readonly=True),
        'discount': fields.float('Discount'),
        'addition': fields.float('Addition'),
        'pay_interest_amount': fields.float('Pay Interest', required=True),
        'redeem_amount': fields.float('Final Redeem', required=True),
        'delegation_of_authority': fields.boolean('Delegation of Authority'),
        'delegate_id': fields.many2one('res.partner', 'Delegate'),
        'bank_journal_id': fields.many2one('account.journal', 'Bank Journal', domain="[('type', '=', 'bank'), ('pawn_journal', '=', True)]", required=True),
        'transfer_amount': fields.float('Transfer Amount'),
        'journal_id': fields.many2one('account.journal', 'Cash Journal', domain="[('type','=','cash'), ('pawn_journal', '=', True)]", required=True, readonly=True),
        'cash_amount': fields.float('Cash Amount'),
    }
    _defaults = {
        'date_redeem': fields.date.context_today,
        'pawn_amount': _get_pawn_amount,
        'interest_amount': _get_interest_amount,
        'discount': 0.0,
        'addition': 0.0,
        'pay_interest_amount': _get_interest_amount,
        'redeem_amount': _get_redeem_amount,
        'delegation_of_authority': False,
        'delegate_id': False,
        'bank_journal_id': _get_bank_journal_id,
        'journal_id': _get_journal,
        'cash_amount': _get_redeem_amount,
        'transfer_amount': 0.0,
    }
    _constraints = [
        (_check_amount, 'The transfer or cash amount is incorrect !!', ['transfer_amount', 'cash_amount']),
    ]

    def onchange_date_redeem(self, cr, uid, ids, date_redeem, context=None):
        res = {'value': {}}
        if context is None:
            context = {}
        context['date_redeem'] = date_redeem
        res['value']['interest_amount'] = self._get_interest_amount(cr, uid, context=context)
        res['value']['pay_interest_amount'] = self._get_interest_amount(cr, uid, context=context)
        res['value']['redeem_amount'] = self._get_redeem_amount(cr, uid, context=context)
        res['value']['cash_amount'] = self._get_redeem_amount(cr, uid, context=context)
        res['value']['transfer_amount'] = 0.0
        res['value']['discount'] = 0.0
        res['value']['addition'] = 0.0
        return res

    def onchange_amount(self, cr, uid, ids, field, pawn_amount, interest_amount, pay_interest_amount, redeem_amount, transfer_amount, cash_amount, context=None):
        res = {'value': {}}
        if field == 'pay_interest_amount':
            redeem_amount = (pawn_amount or 0.0) + (pay_interest_amount or 0.0)
            addition_interest = (pay_interest_amount or 0.0) - (interest_amount or 0.0)
            res['value'].update({
                'redeem_amount': round(redeem_amount, 2),
                'cash_amount': round(redeem_amount, 2),
                'transfer_amount': 0.0,
                'discount': round(abs(addition_interest), 2) if addition_interest < 0 else 0.0,
                'addition': round(addition_interest, 2) if addition_interest > 0 else 0.0,
            })
        elif field == 'redeem_amount':
            pay_interest_amount = (redeem_amount or 0.0) - (pawn_amount or 0.0)
            res['value'].update({
                'pay_interest_amount': round(pay_interest_amount, 2)
            })
        elif field == 'transfer_amount':
            res['value']['cash_amount'] = redeem_amount - transfer_amount
        elif field == 'cash_amount':
            res['value']['transfer_amount'] = redeem_amount - cash_amount
        return res

    def onchange_delegation_of_authority(self, cr, uid, ids, context=None):
        return {'value': {'delegate_id': False}}

    def action_redeem(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pawn_id = context.get('active_id')
        pawn_obj = self.pool.get('pawn.order')
        wizard = self.browse(cr, uid, ids[0], context=context)
        pawn = pawn_obj.browse(cr, uid, pawn_id, context=context)
        state_bf_redeem = pawn.state
        date = wizard.date_redeem
        # Check status
        if pawn.state not in ('pawn', 'expire'):
            raise osv.except_osv(_('Error!'),
                                 _('Ticket need refresh before proceeding!'))
        # Check final redeem
        total_redeem_amount = wizard.pawn_amount + wizard.interest_amount - wizard.discount + wizard.addition
        if float_compare(total_redeem_amount, wizard.redeem_amount, precision_digits=2) != 0:
            raise osv.except_osv(_('Error!'),
                                 _('Initial + Interest Amount - Discount + Addition (%s) must be equal to Final Redeem (%s) !!') % (
                '{:,.2f}'.format(total_redeem_amount), '{:,.2f}'.format(wizard.redeem_amount)))
        # Update some data on pawn ticket before redeem it
        pawn_obj.write(cr, uid, [pawn_id], {
            'delegation_of_authority': wizard.delegation_of_authority,
            'delegate_id': wizard.delegate_id.id
        }, context=context)
        # Trigger workflow, reverse of pawn
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'pawn.order', pawn_id, 'order_redeem', cr)
        # Normal case, redeem after pawned
        if state_bf_redeem != 'expire':
            discount = wizard.discount
            addition = wizard.addition
            interest_amount = wizard.interest_amount - discount + addition
            # Register Actual Interest
            pawn_obj.register_interest_paid(cr, uid, pawn_id, date, discount, addition, interest_amount, context=context)
            # Reverse Accrued Interest
            pawn_obj.action_move_reversed_accrued_interest_create(cr, uid, [pawn_id], context=context)
            # Inactive Accrued Interest that has not been posted yet.
            pawn_obj.update_active_accrued_interest(cr, uid, [pawn_id], False, context=context)
            # Create dr, cr for bank move
            sign = -1 if wizard.pawn_amount < 0 else 1
            pawn = pawn_obj.browse(cr, uid, pawn_id, context=context)
            pawn_obj.action_move_bank_create(cr, uid, pawn_id, pawn.redeem_move_id.id, wizard.bank_journal_id.id, sign * wizard.transfer_amount, wizard.journal_id.id, context=context)
        else:  # Case redeem after expired. No register interest, just full amount as sales receipt.
            pawn_obj.action_move_expired_redeem_create(cr, uid, pawn.id, wizard.redeem_amount, context=context)
        # Update Redeem Date too.
        pawn_obj.write(cr, uid, [pawn_id], {'date_redeem': date})
        return True


pawn_order_redeem()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
