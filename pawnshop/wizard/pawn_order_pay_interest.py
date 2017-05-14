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


class pawn_order_pay_interest(osv.osv_memory):

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
        date_pay_interest = fields.date.context_today(self, cr, uid, context=context)
        if active_id:
            amount_interest = pawn_obj.calculate_interest_remain(cr, uid, active_id, date_pay_interest, context=context)
            return round(amount_interest, 2)
        return False

    _name = "pawn.order.pay.interest"
    _description = "Redeem"
    _columns = {
        'date_pay_interest': fields.date('Date', readonly=True),
        'pawn_amount': fields.float('Initial Amount', readonly=True),
        'interest_amount': fields.float('Interest', readonly=True),
        'discount': fields.float('Discount'),
        'addition': fields.float('Addition'),
        'pay_interest_amount': fields.float('Pay Interest Amount'),
    }
    _defaults = {
        'date_pay_interest': fields.date.context_today,
        'pawn_amount': _get_pawn_amount,
        'interest_amount': _get_interest_amount,
        'discount': 0.0,
        'addition': 0.0,
        'pay_interest_amount': _get_interest_amount,
    }

    def onchange_amount(self, cr, uid, ids, field, interest_amount, discount, addition, pay_interest_amount, context=None):
        res = {'value': {}}
        if field == 'discount':
            pay_interest_amount = (interest_amount or 0.0) - (discount or 0.0)
            res['value']['addition'] = 0.0
            res['value']['pay_interest_amount'] = round(pay_interest_amount, 2)
        if field == 'addition':
            pay_interest_amount = (interest_amount or 0.0) + (addition or 0.0)
            res['value']['discount'] = 0.0
            res['value']['pay_interest_amount'] = round(pay_interest_amount, 2)
        elif field == 'pay_interest_amount':
            diff = (interest_amount or 0.0) - (pay_interest_amount or 0.0)
            if diff >= 0:
                res['value']['discount'] = round(diff, 2)
            else:
                res['value']['addition'] = - round(diff, 2)
        return res

    def action_pay_interest(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        # cr = pooler.get_db(cr.dbname).cursor()
        pawn_obj = self.pool.get('pawn.order')
        wizard = self.browse(cr, uid, ids[0], context)
        active_id = context.get('active_id', False)
        date = wizard.date_pay_interest
        interest_amount = wizard.pay_interest_amount
        discount = wizard.discount
        addition = wizard.addition
        # Register Actual Interest
        pawn_obj.register_interest_paid(cr, uid, active_id, date, discount, addition, interest_amount, context=context)
        # Reverse Accrued Interest
        pawn_obj.action_move_reversed_accrued_interest_create(cr, uid, [active_id], context=context)
        # cr.commit()
        # cr.close()
        return True

pawn_order_pay_interest()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
