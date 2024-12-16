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
import time
from openerp import pooler
from openerp.tools.translate import _
from openerp.tools import float_compare


class pawn_order_redeem(osv.osv_memory):

    def _get_pawn_amount(self, cr, uid, context=None):
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            if pawn:
                return round(pawn.amount_pawned, 2)
        return False

    def _get_interest_amount(self, cr, uid, context=None):
        active_id = context.get('active_id', False)
        pawn_obj = self.pool.get('pawn.order')
        date_redeem = context.get('date_redeem', fields.date.context_today(self, cr, uid, context=context))
        if active_id and date_redeem:
            amount_interest = pawn_obj.calculate_interest_remain(cr, uid, active_id, date_redeem, context=context)
            return round(amount_interest, 2)
        return False

    def _get_monthly_interest(self, cr, uid, context=None):
        """ Get pawn monthly interest from pawn order """
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            if pawn:
                return round(pawn.monthly_interest, 2)
        return False

    def _get_months(self, cr, uid, context=None):
        """ Get pawn months from pawn order """
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        pawn_obj = self.pool.get('pawn.order')
        pawn = pawn_obj.browse(cr, uid, active_id, context=context)
        date_redeem = context.get('date_redeem', fields.date.context_today(self, cr, uid, context=context))
        if active_id and date_redeem:
            months = pawn_obj._calculate_months(cr, uid, pawn.date_order, date_redeem, context=context)
            return months
        return False

    def _get_redeem_amount(self, cr, uid, context=None):
        return self._get_pawn_amount(cr, uid, context=context) + self._get_interest_amount(cr, uid, context=context)

    _name = "pawn.order.redeem"
    _description = "Redeem"
    _columns = {
        'date_redeem': fields.date('Date', readonly=True),
        'pawn_amount': fields.float('Initial Amount', readonly=True),
        'interest_amount': fields.float('Interest', readonly=True),
        'discount': fields.float('Discount', readonly=False),
        'addition': fields.float('Addition'),
        'redeem_amount': fields.float('Final Redeem', readonly=False),
        'delegation_of_authority': fields.boolean('Delegation of Authority'),
        'delegate_id': fields.many2one('res.partner', 'Delegate'),
        'bypass_fingerprint': fields.boolean('Bypass Fingerprint Redeem'),
        'secret_key': fields.char('Secret Key'),
        'monthly_interest': fields.float('Monthly Interest', readonly=True),
        'pawn_duration': fields.float('Pawn Duration (Months)', readonly=True),
    }
    _defaults = {
        'date_redeem': fields.date.context_today,
        'pawn_amount': _get_pawn_amount,
        'interest_amount': _get_interest_amount,
        'discount': 0.0,
        'addition': 0.0,
        'redeem_amount': _get_redeem_amount,
        'delegation_of_authority': False,
        'delegate_id': False,
        'monthly_interest': _get_monthly_interest,
        'pawn_duration': _get_months,
    }

    def onchange_amount(self, cr, uid, ids, field, pawn_amount, interest_amount, discount, addition, redeem_amount, context=None):
        res = {'value': {}}
        if field == 'discount':
            redeem_amount = (pawn_amount or 0.0) + (interest_amount or 0.0)  - (discount or 0.0)
            res['value']['addition'] = 0.0
            res['value']['redeem_amount'] = round(redeem_amount, 2)
        if field == 'addition':
            redeem_amount = (pawn_amount or 0.0) + (interest_amount or 0.0)  + (addition or 0.0)
            res['value']['discount'] = 0.0
            res['value']['redeem_amount'] = round(redeem_amount, 2)
        elif field == 'redeem_amount':
            diff = (pawn_amount or 0.0) + (interest_amount or 0.0)  - (redeem_amount or 0.0)
            if diff > 0:
                res['value']['discount'] = round(diff, 2)
            else:
                res['value']['addition'] = - round(diff, 2)
        return res

    def onchange_date_redeem(self, cr, uid, ids, date_redeem, context=None):
        res = {'value': {}}
        if context is None:
            context = {}
        context['date_redeem'] = date_redeem
        res['value']['interest_amount'] = self._get_interest_amount(cr, uid, context=context)
        res['value']['redeem_amount'] = self._get_redeem_amount(cr, uid, context=context)
        res['value']['discount'] = 0.0
        res['value']['addition'] = 0.0
        return res

    def onchange_delegation_of_authority(self, cr, uid, ids, context=None):
        return {'value': {'delegate_id': False}}
    
    def onchange_bypass_fingerprint(self, cr, uid, ids, context=None):
        return {'value': {'secret_key': False}}

    def _validate_secret_key(self, cr, uid, bypass_fingerprint, secret_key, context=None):
        """This function used for validate secret key bypass fingerprint check"""
        if bypass_fingerprint:
            valid_secret_key = self.pool.get('ir.config_parameter').get_param(cr, uid, 'pawnshop.redeem_secret_key', '')
            if secret_key != valid_secret_key:
                raise osv.except_osv(_('Error!'), _('The secret key is invalid.'))

    def action_redeem(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # TEST REMOVE CURSOR
        # cr = pooler.get_db(cr.dbname).cursor()
        # --
        pawn_id = context.get('active_id')
        pawn_obj = self.pool.get('pawn.order')
        # Check status
        pawn = pawn_obj.browse(cr, uid, pawn_id)
        if pawn.state not in ('pawn', 'expire'):
            raise osv.except_osv(_('Error!'),
                                 _('Ticket need refresh before proceeding!'))
        pawn = pawn_obj.browse(cr, uid, pawn_id, context=context)
        state_bf_redeem = pawn.state
        # Update some data on pawn ticket before redeem it
        wizard = self.browse(cr, uid, ids[0], context)
        pawn_obj.write(cr, uid, [pawn_id], {
            'delegation_of_authority': wizard.delegation_of_authority,
            'delegate_id': wizard.delegate_id.id,
            'bypass_fingerprint_redeem': wizard.bypass_fingerprint,
        }, context=context)
        # Trigger workflow, reverse of pawn
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'pawn.order', pawn_id, 'order_redeem', cr)
        date = wizard.date_redeem
        # Check final redeem
        total_redeem_amount = wizard.pawn_amount + wizard.interest_amount - wizard.discount + wizard.addition
        if float_compare(total_redeem_amount, wizard.redeem_amount, precision_digits=2) != 0:
            raise osv.except_osv(_('Error!'),
                                 _('Initial + Interest Amount - Discount + Addition (%s) must be equal to Final Redeem (%s) !!') % (
                '{:,.2f}'.format(total_redeem_amount), '{:,.2f}'.format(wizard.redeem_amount)))
        # Check Secret Key
        self._validate_secret_key(cr, uid, wizard.bypass_fingerprint, wizard.secret_key, context=context)
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
        else: # Case redeem after expired. No register interest, just full amount as sales receipt.
            pawn_obj.action_move_expired_redeem_create(cr, uid, pawn.id, wizard.redeem_amount, context=context)
        # Update Redeem Date too.
        pawn_obj.write(cr, uid, [pawn_id], {'date_redeem': date})
        # TEST REMOVE CURSOR
        # cr.commit()
        # cr.close()
        # --
        return True

pawn_order_redeem()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
