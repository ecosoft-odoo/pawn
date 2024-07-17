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


class pawn_order_pawn(osv.osv_memory):

    def _get_amount(self, cr, uid, context=None):
        """
            This function show default net amount for 'customer pays money to pawn shop' or 'pawn shop pays money to customer'
            - If net amount < 0, pawn shop pays money to customer
            - If net amount > 0, customer pays money to pawn shop
        """
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            if pawn.parent_id:
                return -pawn.amount_net
            else:
                return -pawn.amount_pawned
        return False

    def _get_parent_id(self, cr, uid, context=None):
        """ Default parent from pawn order """
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            return pawn.parent_id and pawn.parent_id.id or False
        return False

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
            # Transfer Amount + Cash Amount must equal to Total Amount
            if wizard.transfer_amount + wizard.cash_amount != abs(wizard.amount):
                return False
            # Transfer Amount / Cash Amount must greater than zero
            if wizard.transfer_amount < 0 or wizard.cash_amount < 0:
                return False
        return True

    _name = "pawn.order.pawn"
    _description = "Pawn"
    _columns = {
        'amount': fields.float('Net Amount', readonly=True),
        'date_due_ticket': fields.date(string='Due Date', required=True),
        'parent_id': fields.many2one('pawn.order', 'Previous Pawn Ticket'),
        'bank_journal_id': fields.many2one('account.journal', 'Bank Journal', domain="[('type', '=', 'bank')]", required=True),
        'transfer_amount': fields.float('Transfer Amount'),
        'journal_id': fields.many2one('account.journal', 'Cash Journal', domain="[('type','=','cash'), ('pawn_journal', '=', True)]", required=True, readonly=True),
        'cash_amount': fields.float('Cash Amount'),
    }
    _defaults = {
        'amount': _get_amount,
        'parent_id': _get_parent_id,
        'journal_id': _get_journal,
    }
    _constraints = [
        (_check_amount, 'The transfer or cash amount is incorrect !!', ['transfer_amount', 'cash_amount']),
    ]

    def onchange_amount(self, cr, uid, ids, field, transfer_amount, cash_amount, total_amount, context=None):
        res = {'value': {}}
        if field == 'transfer':
            res['value']['cash_amount'] = abs(total_amount) - transfer_amount
        elif field == 'cash':
            res['value']['transfer_amount'] = abs(total_amount) - cash_amount
        return res

    def _check_pawn_item_image_first(self, cr, uid, pawn, context=None):
        if not pawn.pawn_item_image_first:
            raise osv.except_osv(_('Error!'), _('Please provide an image of the item before pawning it.'))

    def action_pawn(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id')
        pawn_obj = self.pool.get('pawn.order')
        # Check status
        pawn = pawn_obj.browse(cr, uid, active_id)
        if pawn.state != 'draft':
            raise osv.except_osv(_('Error!'),
                                 _('Ticket need refresh before proceeding!'))
        # Check pawned amount
        if pawn.amount_pawned != sum([line.pawn_price_subtotal for line in pawn.order_line]):
            raise osv.except_osv(_('Error!'), _('Pawned amount must equal to sum of pawned subtotal'))
        # Check pawn item image
        self._check_pawn_item_image_first(cr, uid, pawn, context=context)
        # Write journal_id back to order
        wizard = self.browse(cr, uid, ids[0], context)
        pawn_obj.write(cr, uid, [active_id], {
            'journal_id': wizard.journal_id.id,
            'date_due_ticket': wizard.date_due_ticket,
        }, context=context)
        # Trigger workflow
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'pawn.order', active_id, 'order_pawn', cr)
        # Create dr, cr for bank move
        sign = -1 if wizard.amount < 0 else 1
        pawn = pawn_obj.browse(cr, uid, active_id, context=context)
        pawn_obj.action_move_bank_create(cr, uid, active_id, pawn.pawn_move_id.id, wizard.bank_journal_id.id, sign * wizard.transfer_amount, wizard.journal_id.id, context=context)
        # For renew, reverse bank move actual interest
        if pawn.parent_id:
            for line in pawn.parent_id.actual_interest_ids:
                sign = -1 if line.interest_amount > 0 else 1
                pawn_obj.action_move_bank_create(cr, uid, active_id, pawn.pawn_move_id.id, line.bank_journal_id.id, sign * line.transfer_interest_amount, line.pawn_id.journal_id.id, context=context)
        return True


pawn_order_pawn()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
