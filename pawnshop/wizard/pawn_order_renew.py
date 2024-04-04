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


class pawn_order_renew(osv.osv_memory):

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

    _name = "pawn.order.renew"
    _description = "renew"
    _columns = {
        'date_renew': fields.date('Date', readonly=True),
        'pawn_amount': fields.float('Initial Amount', readonly=True),
        'interest_amount': fields.float('Interest', readonly=True),
        'discount': fields.float('Discount', readonly=False),
        'addition': fields.float('Addition'),
        'pay_interest_amount': fields.float('Pay Interest Amount', readonly=False),
        'increase_pawn_amount': fields.float('Increase Pawn Amount', readonly=False),
        'new_pawn_amount': fields.float('New Pawn Amount', readonly=False),
        'use_same_fingerprint': fields.boolean('Use Same Fingerprint'),
    }
    _defaults = {
        'date_renew': fields.date.context_today,
        'pawn_amount': _get_pawn_amount,
        'interest_amount': _get_interest_amount,
        'discount': 0.0,
        'addition': 0.0,
        'pay_interest_amount': _get_interest_amount,
        'increase_pawn_amount': 0.0,
        'use_same_fingerprint': False,
    }

    def onchange_amount(self, cr, uid, ids, field, pawn_amount, interest_amount, discount, addition, pay_interest_amount, increase_pawn_amount, new_pawn_amount, context=None):
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
        elif field in ('increase_pawn_amount'):
            new_pawn_amount = (pawn_amount or 0.0) + (increase_pawn_amount or 0.0)
            res['value']['new_pawn_amount'] = round(new_pawn_amount, 2)
        elif field == 'new_pawn_amount':
            increase_pawn_amount = (new_pawn_amount or 0.0) - (pawn_amount or 0.0)
            res['value']['increase_pawn_amount'] = round(increase_pawn_amount, 2)
        return res

    def action_renew(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        # cr = pooler.get_db(cr.dbname).cursor()
        pawn_id = context.get('active_id')
        pawn_obj = self.pool.get('pawn.order')
        pawn = pawn_obj.browse(cr, uid, pawn_id, context=context)
        state_bf_redeem = pawn.state
        wizard = self.browse(cr, uid, ids[0], context)
        # Update use same fingerprint
        pawn_obj.write(cr, uid, [pawn_id], {'use_same_fingerprint_redeem': wizard.use_same_fingerprint}, context=context)
        # Trigger workflow
        # Redeem the current one
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'pawn.order', pawn_id, 'order_redeem', cr)
        # Interest
        date = wizard.date_renew
        # Check pay interest amount
        total_pay_interest_amount = wizard.interest_amount - wizard.discount + wizard.addition
        if float_compare(total_pay_interest_amount, wizard.pay_interest_amount, precision_digits=2) != 0:
            raise osv.except_osv(_('Error!'),
                                 _('Interest Amount - Discount + Addition (%s) must be equal to Pay Interest Amount (%s) !!') % (
                '{:,.2f}'.format(total_pay_interest_amount), '{:,.2f}'.format(wizard.pay_interest_amount)))
        # Warning if today > date_due
#         if pawn.date_due and pawn.date_due < time.strftime('%Y-%m-%d'):
#             raise osv.except_osv(
#                 _('Cannot renew!'),
#                 _('Today is over grace period end date.\n'
#                   'Please use normal sales process for expired items.'))
        # Normal case, redeem after pawned
        if state_bf_redeem != 'expire':
            interest_amount = wizard.pay_interest_amount
            discount = wizard.discount
            addition = wizard.addition
            # Register Actual Interest
            pawn_obj.register_interest_paid(cr, uid, pawn_id, date, discount, addition, interest_amount, context=context)
            # Reverse Accrued Interest
            pawn_obj.action_move_reversed_accrued_interest_create(cr, uid, [pawn_id], context=context)
            # Inactive Accrued Interest that has not been posted yet.
            pawn_obj.update_active_accrued_interest(cr, uid, [pawn_id], False, context=context)
        else:
            # Special Case redeem after expired.
            # No register interest, just full amount as sales receipt.
            redeem_amount = wizard.pawn_amount + wizard.pay_interest_amount
            pawn_obj.action_move_expired_redeem_create(cr, uid, pawn.id, redeem_amount, context=context)
            # Overwrite state to 'expire' (Very special case0
            pawn_obj.write(cr, uid, [pawn.id], {'state': 'expire'}, context=context)
            pawn_obj._update_order_pawn_asset(cr, uid, [pawn.id], {'state': 'expire'}, context=context)
            # Immediately set to for sales
            item_obj = self.pool.get('product.product')
            asset_ids = item_obj.search(cr, uid, [('order_id', 'in', [pawn.id]), ('parent_id', '=', False)], context=context)
            context.update({'allow_for_sale': True})
            item_obj.action_asset_sale(cr, uid, asset_ids, context=context)
            # Create Sales receipt
            item_ids = item_obj.search(cr, uid, [('parent_id', '=', asset_ids[0])], context=context)
            wizard_obj = self.pool.get('pawn.item.create.receipt')
            wizard_id = wizard_obj.create(cr, uid, {'partner_id': pawn.partner_id.id, 'item_ids': [(6, 0, item_ids)]}, context=context)
            res = wizard_obj.pawn_item_create_receipt(cr, uid, [wizard_id], context=context)
            # Update amount
            voucher_id = res['res_id']
            self.pool.get('account.voucher').write(cr, uid, [voucher_id], {'amount': redeem_amount})
            # Validate Receipt
            wf_service.trg_validate(uid, 'account.voucher', voucher_id, 'proforma_voucher', cr)

        # Update Redeem Date too.
        pawn_obj.write(cr, uid, [pawn_id], {'date_redeem': date})
        # Create the new Pawn by copying the existing one.
        wizard = self.browse(cr, uid, ids[0], context)
        default = {
            'parent_id': pawn_id,
            'date_order': wizard.date_renew,
        }
        new_pawn_id = pawn_obj.copy(cr, uid, pawn_id, default, context=context)
        amount_net = wizard.increase_pawn_amount - wizard.pay_interest_amount
        pawn_obj.write(cr, uid, [new_pawn_id], {'parent_id': pawn_id,
                                                'amount_pawned': wizard.new_pawn_amount,
                                                'amount_net': amount_net,
                                                'use_same_fingerprint_pawn': wizard.use_same_fingerprint}, context=context)
        # Write new pawn back to the original
        pawn_obj.write(cr, uid, [pawn_id], {'child_id': new_pawn_id}, context=context)
        # Commit
        # cr.commit()
        # cr.close()
        # Redirection
        return self.open_pawn_order(cr, uid, new_pawn_id, context=context)

    def open_pawn_order(self, cr, uid, pawn_id, context=None):
        # cr = pooler.get_db(cr.dbname).cursor()
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'pawnshop', 'pawn_order_form')
        form_id = form_res and form_res[1] or False
        tree_res = ir_model_data.get_object_reference(cr, uid, 'pawnshop', 'pawn_order_tree')
        tree_id = tree_res and tree_res[1] or False
        return {
            'name': _('Pawn Tickets'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'pawn.order',
            'res_id': pawn_id,
            'view_id': False,
            'views': [(form_id, 'form'), (tree_id, 'tree')],
            'context': "{}",
            'type': 'ir.actions.act_window',
        }

pawn_order_renew()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
