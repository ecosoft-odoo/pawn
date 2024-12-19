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
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import float_compare


class pawn_order_renew(osv.osv_memory):

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
        date_redeem = context.get('date_renew', fields.date.context_today(self, cr, uid, context=context))
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
    
    def _prepare_renew_lines(self, cr, uid, line, context=None):
        """ Prepare pawn line """
        return {
            'order_line_id': line.id,
            'name': line.name,
            'categ_id': line.categ_id.id,
            'product_qty': line.product_qty,
            'product_uom': line.product_uom.id,
            'carat': line.carat,
            'gram': line.gram,
            'price_unit': line.price_unit,
            'price_subtotal': line.price_subtotal,
            'pawn_price_unit': line.pawn_price_unit,
            'pawn_price_subtotal': line.pawn_price_subtotal,
        }

    def _get_renew_line_ids(self, cr, uid, context=None):
        """ Get pawn line from pawn order """
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            return [(0, 0, self._prepare_renew_lines(cr, uid, line, context=context)) for line in pawn.order_line]
        return False

    _name = "pawn.order.renew"
    _description = "Renew"
    _columns = {
        'date_renew': fields.date('Date'),
        'pawn_amount': fields.float('Initial', readonly=True),
        'interest_amount': fields.float('Computed Interest', readonly=True),
        'discount': fields.float('Discount'),
        'addition': fields.float('Addition'),
        'pay_interest_amount': fields.float('Pay Interest', required=True),
        'increase_pawn_amount': fields.float('Increase Pawn Amount', readonly=True),
        'new_pawn_amount': fields.float('New Pawn Amount', required=True, readonly=True),
        'delegation_of_authority': fields.boolean('Delegation of Authority'),
        'delegate_id': fields.many2one('res.partner', 'Delegate'),
        'renewal_transfer': fields.boolean('Renewal Transfer'), 
        'secret_key': fields.char('Secret Key'),
        'renew_line_ids': fields.one2many('pawn.order.renew.line', 'renew_id', 'Renew Line'),
        'monthly_interest': fields.float('Monthly Interest', readonly=True),
        'pawn_duration': fields.float('Pawn Duration (Months)', readonly=True),
    }
    _defaults = {
        'date_renew': fields.date.context_today,
        'pawn_amount': _get_pawn_amount,
        'interest_amount': _get_interest_amount,
        'discount': 0.0,
        'addition': 0.0,
        'pay_interest_amount': _get_interest_amount,
        'increase_pawn_amount': 0.0,
        'new_pawn_amount': _get_pawn_amount,
        'renewal_transfer': False,
        'delegation_of_authority': False,
        'delegate_id': False,
        'renew_line_ids': _get_renew_line_ids,
        'monthly_interest': _get_monthly_interest,
        'pawn_duration': _get_months,
    }

    def onchange_date_renew(self, cr, uid, ids, date_renew, context=None):
        res = {'value': {}}
        if context is None:
            context = {}
        context['date_renew'] = date_renew
        res['value']['interest_amount'] = self._get_interest_amount(cr, uid, context=context)
        res['value']['pay_interest_amount'] = self._get_interest_amount(cr, uid, context=context)
        res['value']['discount'] = 0.0
        res['value']['addition'] = 0.0
        return res

    def onchange_amount(self, cr, uid, ids, field, pawn_amount, interest_amount, pay_interest_amount, increase_pawn_amount, new_pawn_amount, context=None):
        res = {'value': {}}
        if field == 'pay_interest_amount':
            addition_interest = (pay_interest_amount or 0.0) - (interest_amount or 0.0)
            res['value'].update({
                'discount': round(abs(addition_interest), 2) if addition_interest < 0 else 0.0,
                'addition': round(addition_interest, 2) if addition_interest > 0 else 0.0,
            })
        elif field in ('increase_pawn_amount'):
            new_pawn_amount = (pawn_amount or 0.0) + (increase_pawn_amount or 0.0)
            res['value'].update({
                'new_pawn_amount': round(new_pawn_amount, 2),
            })
        elif field == 'new_pawn_amount':
            increase_pawn_amount = (new_pawn_amount or 0.0) - (pawn_amount or 0.0)
            res['value'].update({
                'increase_pawn_amount': round(increase_pawn_amount, 2),
            })
        return res

    def onchange_renew_ids(self, cr, uid, ids, renew_line_ids, context=None):
        renew_line_obj = self.pool.get('pawn.order.renew.line')
        new_pawn_amount = 0
        for line in renew_line_ids:
            if line[0] == 0:
                # Condition for create line
                new_pawn_amount += line[2]['pawn_price_subtotal']
            elif line[0] == 1:
                # Condition for update line
                if 'pawn_price_subtotal' in line[2]:
                    new_pawn_amount += line[2]['pawn_price_subtotal']
                else:
                    new_pawn_amount += renew_line_obj.browse(cr, uid, line[1], context=context).pawn_price_subtotal
            elif line[0] == 4:
                # Condition for link line
                new_pawn_amount += renew_line_obj.browse(cr, uid, line[1], context=context).pawn_price_subtotal
        return {'value': {'new_pawn_amount': new_pawn_amount}}

    def onchange_delegation_of_authority(self, cr, uid, ids, context=None):
        return {'value': {'delegate_id': False}}

    def onchange_renewal_transfer(self, cr, uid, ids, context=None):
        return {'value': {'secret_key': False}}

    def _validate_secret_key(self, cr, uid, renewal_transfer, secret_key, context=None):
        """This function used for validate secret key renewal transfer"""
        if renewal_transfer:
            valid_secret_key = self.pool.get('ir.config_parameter').get_param(cr, uid, 'pawnshop.renew_secret_key', '')
            if secret_key != valid_secret_key:
                raise osv.except_osv(_('Error!'), _('The secret key is invalid.'))
        return True

    def remove_move_accrued_interest(self, cr, uid, pawn_id, redeem_date, context=None):
        accrued_obj = self.pool.get('pawn.accrued.interest')
        move_obj = self.pool.get('account.move')
        accrued_interest_ids = accrued_obj.search(cr, uid, [('pawn_id', '=', pawn_id), ('interest_date', '>', redeem_date)], context=context)
        accrued_interests = accrued_obj.browse(cr, uid, accrued_interest_ids, context=context)
        for accrued_interest in accrued_interests:
            if accrued_interest.reverse_move_id:
                move_obj.button_cancel(cr, uid, [accrued_interest.reverse_move_id.id], context=context)
                move_obj.unlink(cr, uid, [accrued_interest.reverse_move_id.id], context=context)
            if accrued_interest.move_id:
                move_obj.button_cancel(cr, uid, [accrued_interest.move_id.id], context=context)
                move_obj.unlink(cr, uid, [accrued_interest.move_id.id], context=context)
            # Inactive accrued interest line
            accrued_obj.write(cr, uid, [accrued_interest.id], {'active': False}, context=context)
        return True

    def action_renew(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pawn_id = context.get('active_id')
        pawn_obj = self.pool.get('pawn.order')
        pawn_line_obj = self.pool.get('pawn.order.line')
        wizard = self.browse(cr, uid, ids[0], context=context)
        pawn = pawn_obj.browse(cr, uid, pawn_id, context=context)
        state_bf_redeem = pawn.state
        date = wizard.date_renew
        # Check new pawn amount must equal to sum of pawned subtotal
        if wizard.new_pawn_amount != sum([line.pawn_price_subtotal for line in wizard.renew_line_ids]):
            raise osv.except_osv(_('Error!'), _('New pawn amount must equal to sum of pawned subtotal'))
        # Check Secret Key (Renewal Transfer Only)
        self._validate_secret_key(cr, uid, wizard.renewal_transfer, wizard.secret_key, context=context)
        # Renewal Transfer and Delegation of Authority not allowed to select both
        if wizard.delegation_of_authority and wizard.renewal_transfer:
            raise osv.except_osv(_('Error!'), _('Selecting both delegation of authority and renewal transfer is not permitted.'))
        # Check pay interest amount
        total_pay_interest_amount = wizard.interest_amount - wizard.discount + wizard.addition
        if float_compare(total_pay_interest_amount, wizard.pay_interest_amount, precision_digits=2) != 0:
            raise osv.except_osv(_('Error!'),
                                 _('Interest Amount - Discount + Addition (%s) must be equal to Pay Interest Amount (%s) !!') % (
                '{:,.2f}'.format(total_pay_interest_amount), '{:,.2f}'.format(wizard.pay_interest_amount)))
        # Update data on old ticket
        pawn_obj.write(cr, uid, [pawn_id], {
            'renewal_transfer_redeem': wizard.renewal_transfer,
            'delegation_of_authority': wizard.delegation_of_authority,
            'delegate_id': wizard.delegate_id.id,
            'bypass_fingerprint_redeem': True if (wizard.renewal_transfer and not pawn.fingerprint_pawn) else False,
            'date_redeem': date,  # Update Redeem Date
        }, context=context)
        # Trigger workflow
        # Redeem the current one
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
            pawn_obj.action_move_reversed_accrued_interest_create(cr, uid, [pawn_id], context=dict(context, **{'force_date': date}))
            # Inactive Accrued Interest that has not been posted yet.
            pawn_obj.update_active_accrued_interest(cr, uid, [pawn_id], False, context=context)
            # Remove Accrued Interest Move (Case Redeem Date < Today)
            self.remove_move_accrued_interest(cr, uid, pawn_id, date, context=context)
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
        # Create the new Pawn by copying the existing one.
        default_pawn = {
            'parent_id': pawn_id,
            'date_order': date,
            'order_line': False,
        }
        new_pawn_id = pawn_obj.copy(cr, uid, pawn_id, default_pawn, context=context)
        for line in wizard.renew_line_ids:
            default_pawn_line = {
                'order_id': new_pawn_id,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'pawn_price_unit': line.pawn_price_unit,
                'pawn_price_subtotal': line.pawn_price_subtotal,
            }
            pawn_line_obj.copy(cr, uid, line.order_line_id.id, default_pawn_line, context=context)
        amount_net = wizard.increase_pawn_amount - wizard.pay_interest_amount
        # Update data in new ticket
        vals = {
            'parent_id': pawn_id,
            'amount_pawned': wizard.new_pawn_amount,
            'amount_net': amount_net,
            'renewal_transfer_pawn': wizard.renewal_transfer,
            'bypass_fingerprint_pawn': False,
        }
        for i in ['first', 'second', 'third', 'fourth', 'fifth']:
            vals.update({
                'pawn_item_image_%s' % i: pawn['pawn_item_image_%s' % i],
                'pawn_item_image_date_%s' % i: pawn['pawn_item_image_date_%s' % i],
            })
        pawn_obj.write(cr, uid, [new_pawn_id], vals, context=context)
        # Change partner to delegate for the new ticket
        if wizard.delegation_of_authority:
            pawn_obj.write(cr, uid, [new_pawn_id], {'partner_id': wizard.delegate_id.id}, context=context)
        # Write new pawn back to the original
        pawn_obj.write(cr, uid, [pawn_id], {'child_id': new_pawn_id}, context=context)
        return self.open_pawn_order(cr, uid, new_pawn_id, context=context)

    def open_pawn_order(self, cr, uid, pawn_id, context=None):
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

    def _update_field(self, cr, uid, vals, context=None):
        if 'renew_line_ids' in vals and vals['renew_line_ids']:
            pawn_amount = self._get_pawn_amount(cr, uid, context=context)
            new_pawn_amount = self.onchange_renew_ids(cr, uid, [], vals['renew_line_ids'], context=context)['value']['new_pawn_amount']
            increase_pawn_amount = self.onchange_amount(cr, uid, [], 'new_pawn_amount', pawn_amount, False, False, False, new_pawn_amount, context=context)['value']['increase_pawn_amount']
            if not ('increase_pawn_amount' in vals) and not ('new_pawn_amount' in vals):
                vals.update({
                    'increase_pawn_amount': increase_pawn_amount,
                    'new_pawn_amount': new_pawn_amount,
                })
        # Update interest_amount (onchange method not store value for readonly field)
        if vals.get('date_renew') and not vals.get('interest_amount'):
            vals['interest_amount'] = self.onchange_date_renew(cr, uid, [], vals['date_renew'], context=context)['value']['interest_amount']
        return vals

    def create(self, cr, uid, vals, context=None):
        vals = self._update_field(cr, uid, vals, context=context)
        return super(pawn_order_renew, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        vals = self._update_field(cr, uid, vals, context=context)
        return super(pawn_order_renew, self).write(cr, uid, ids, vals, context=context)


pawn_order_renew()


class pawn_order_renew_line(osv.osv_memory):
    _name = "pawn.order.renew.line"
    _description = "renew line"

    _columns = {
        'order_line_id': fields.many2one('pawn.order.line', string='Pawn Order Line'),
        'renew_id': fields.many2one('pawn.order.renew', string='Renew'),
        'name': fields.text('Description', readonly=True),
        'categ_id': fields.many2one('product.category', string='Category', readonly=True),
        'product_qty': fields.float('Quantity', readonly=True, digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_uom': fields.many2one('product.uom', string='Product Unit of Measure', readonly=True),
        'carat': fields.float('Carat', readonly=True),
        'gram': fields.float('Gram', readonly=True),
        'price_unit': fields.float('Estimated Price / Unit', required=True, digits_compute=dp.get_precision('Product Price')),
        'price_subtotal': fields.float('Estimated Subtotal', required=True, digits_compute=dp.get_precision('Account')),
        'pawn_price_unit': fields.float('Pawned Price / Unit', required=False, digits_compute=dp.get_precision('Product Price'), readonly=True),
        'pawn_price_subtotal': fields.float('Pawned Subtotal', required=True, digits_compute=dp.get_precision('Account')),
    }

    def onchange_price(self, cr, uid, ids, field, product_qty, price_unit, price_subtotal, pawn_price_unit, pawn_price_subtotal):
        res = {'value': {}}
        precision = self.pool.get('decimal.precision').precision_get
        product_qty = float(product_qty)
        # if field == 'price_unit':
        #     res['value'].update({
        #         'price_subtotal': round(product_qty * price_unit, precision(cr, uid, 'Account')),
        #     })
        # elif field == 'pawn_price_unit':
        #     res['value'].update({
        #         'pawn_price_subtotal': round(product_qty * pawn_price_unit, precision(cr, uid, 'Account')),
        #     })
        if field == 'price_subtotal':
            res['value'].update({
                'price_unit': round(price_subtotal / product_qty, precision(cr, uid, 'Product Price'))
            })
        elif field == 'pawn_price_subtotal':
            res['value'].update({
                'pawn_price_unit': round(pawn_price_subtotal / product_qty, precision(cr, uid, 'Product Price'))
            })
            # Not used estimated price now so we define estimated price = pawned price
            res['value']['price_subtotal'] = pawn_price_subtotal
        return res

    def create(self, cr, uid, vals, context=None):
        renew_line_id = super(pawn_order_renew_line, self).create(cr, uid, vals, context=context)
        # pawn_price_unit field is readonly, it not store in database if we call onchange function and effect with this field
        # So, we need to update it
        if vals.get('pawn_price_subtotal'):
            renew_line = self.browse(cr, uid, renew_line_id, context=context)
            pawn_price_unit = self.onchange_price(cr, uid, [renew_line.id], 'pawn_price_subtotal', renew_line.product_qty, renew_line.price_unit, renew_line.price_subtotal, renew_line.pawn_price_unit, renew_line.pawn_price_subtotal)['value']['pawn_price_unit']
            self.write(cr, uid, [renew_line.id], {'pawn_price_unit': pawn_price_unit}, context=context)
        return renew_line_id

    def write(self, cr, uid, ids, vals, context=None):
        res = super(pawn_order_renew_line, self).write(cr, uid, ids, vals, context=context)
        # pawn_price_unit field is readonly, it not store in database if we call onchange function and effect with this field
        # So, we need to update it
        if vals.get('pawn_price_subtotal'):
            renew_lines = self.browse(cr, uid, ids, context=context)
            for renew_line in renew_lines:
                pawn_price_unit = self.onchange_price(cr, uid, [renew_line.id], 'pawn_price_subtotal', renew_line.product_qty, renew_line.price_unit, renew_line.price_subtotal, renew_line.pawn_price_unit, renew_line.pawn_price_subtotal)['value']['pawn_price_unit']
                self.write(cr, uid, [renew_line.id], {'pawn_price_unit': pawn_price_unit}, context=context)
        return res


pawn_order_renew_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
