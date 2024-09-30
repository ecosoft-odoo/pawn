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

from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.osv import fields, osv
from openerp import netsvc
from openerp.tools.translate import _


class pawn_order_pawn(osv.osv_memory):

    def _get_amount(self, cr, uid, context=None):
        """
            This function show default net amount
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

    def _get_date_due_ticket(self, cr, uid, context=None):
        """ Due Date Ticket = Pawn Date + 5 Months """
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            return str(datetime.strptime(pawn.date_order, '%Y-%m-%d').date() + relativedelta(months=pawn.rule_id.length_month + 1 or 0.0))
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
        'bank_journal_id': fields.many2one('account.journal', 'Bank Journal', domain="[('type', '=', 'bank'), ('pawn_journal', '=', True)]", required=True),
        'transfer_amount': fields.float('Transfer Amount'),
        'journal_id': fields.many2one('account.journal', 'Cash Journal', domain="[('type','=','cash'), ('pawn_journal', '=', True)]", required=True, readonly=True),
        'cash_amount': fields.float('Cash Amount'),
        'bypass_fingerprint': fields.boolean('Bypass Fingerprint Pawn'),
        'secret_key': fields.char('Secret Key'),
    }
    _defaults = {
        'amount': _get_amount,
        'date_due_ticket': _get_date_due_ticket,
        'parent_id': _get_parent_id,
        'bank_journal_id': _get_bank_journal_id,
        'journal_id': _get_journal,
        'cash_amount': lambda self, cr, uid, context=None: abs(self._get_amount(cr, uid, context=context)),
        'transfer_amount': 0.0,
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

    def onchange_bypass_fingerprint(self, cr, uid, ids, context=None):
        return {'value': {'secret_key': False}}

    def _validate_secret_key(self, cr, uid, bypass_fingerprint, secret_key, context=None):
        """This function used for validate secret key bypass fingerprint check"""
        if bypass_fingerprint:
            valid_secret_key = self.pool.get('ir.config_parameter').get_param(cr, uid, 'pawnshop.pawn_secret_key', '')
            if secret_key != valid_secret_key:
                raise osv.except_osv(_('Error!'), _('The secret key is invalid.'))

    def _check_pawn_item_image_first(self, cr, uid, pawn, context=None):
        if not pawn.pawn_item_image_first:
            raise osv.except_osv(_('Error!'), _('Please provide an image of the item before pawning it.'))

    def action_pawn(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id')
        pawn_obj = self.pool.get('pawn.order')
        wizard = self.browse(cr, uid, ids[0], context)
        # Check status
        pawn = pawn_obj.browse(cr, uid, active_id)
        if pawn.state != 'draft':
            raise osv.except_osv(_('Error!'),
                                 _('Ticket need refresh before proceeding!'))
        # Check pawned amount
        if pawn.amount_pawned != sum([line.pawn_price_subtotal for line in pawn.order_line]):
            raise osv.except_osv(_('Error!'), _('Pawned amount must equal to sum of pawned subtotal'))
        # Fingerprint not found, must check bypass fingerprint
        if pawn.renewal_transfer_pawn and pawn.parent_id and not pawn.parent_id.fingerprint_redeem and not wizard.bypass_fingerprint:
            raise osv.except_osv(_('Error!'), _('Please check bypass fingerprint.'))
        # Check pawn item image
        self._check_pawn_item_image_first(cr, uid, pawn, context=context)
        # Check Secret Key
        self._validate_secret_key(cr, uid, wizard.bypass_fingerprint, wizard.secret_key, context=context)
        # Write journal_id back to order
        pawn_obj.write(cr, uid, [active_id], {
            'journal_id': wizard.journal_id.id,
            'date_due_ticket': wizard.date_due_ticket,
            'bypass_fingerprint_pawn': wizard.bypass_fingerprint,
        }, context=context)
        # Trigger workflow
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'pawn.order', active_id, 'order_pawn', cr)
        # Create dr, cr for bank move
        sign = -1 if wizard.amount < 0 else 1
        pawn = pawn_obj.browse(cr, uid, active_id, context=context)
        pawn_obj.action_move_bank_create(cr, uid, pawn.parent_id.id if (pawn.parent_id and wizard.amount > 0) else active_id, pawn.pawn_move_id.id, wizard.bank_journal_id.id, sign * wizard.transfer_amount, wizard.journal_id.id, context=context)
        return True


pawn_order_pawn()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
