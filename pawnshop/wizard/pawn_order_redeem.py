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
        date_redeem = fields.date.context_today(self, cr, uid, context=context)
        if active_id:
            amount_interest = pawn_obj.calculate_interest_remain(cr, uid, active_id, date_redeem, context=context)
            return round(amount_interest, 2)
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
    }
    _defaults = {
        'date_redeem': fields.date.context_today,
        'pawn_amount': _get_pawn_amount,
        'interest_amount': _get_interest_amount,
        'discount': 0.0,
        'addition': 0.0,
        'redeem_amount': _get_redeem_amount,
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

    def action_redeem(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        cr = pooler.get_db(cr.dbname).cursor()
        pawn_id = context.get('active_id')
        # Trigger workflow, reverse of pawn
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'pawn.order', pawn_id, 'order_redeem', cr)
        pawn_obj = self.pool.get('pawn.order')
        pawn = pawn_obj.browse(cr, uid, pawn_id, context=context)
        wizard = self.browse(cr, uid, ids[0], context)
        date = wizard.date_redeem
        # Normal case, redeem after pawned
        if not pawn.extended:
            discount = wizard.discount
            addition = wizard.addition
            interest_amount = wizard.interest_amount - discount + addition
            # Register Actual Interest
            pawn_obj.register_interest_paid(cr, uid, pawn_id, date, discount, addition, interest_amount, context=context)
            # Reverse Accrued Interest
            pawn_obj.action_move_reversed_accrued_interest_create(cr, uid, [pawn_id], context=context)
            # Inactive Accrued Interest that has not been posted yet.
            pawn_obj.update_active_accrued_interest(cr, uid, [pawn_id], False, context=context)
        else: # Case redeem after extended. No register interest, just full amount as sales receipt.
            pawn_obj.action_move_expired_redeem_create(cr, uid, pawn.id, wizard.redeem_amount, context=context)
        # Update Redeem Date too.
        pawn_obj.write(cr, uid, [pawn_id], {'date_redeem': date})
        cr.commit()
        cr.close()
        return True

pawn_order_redeem()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
