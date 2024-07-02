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
import time
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import float_compare

LOCATION_STATUS_MAP = {'draft': 'item_sold',
                       'posted': 'item_sold',
                       'proforma': 'item_sold',
                       'cancel': 'item_for_sale',
                       # Refund cases, the opposite
                       'draft_refund': 'item_for_sale',
                       'posted_refund': 'item_for_sale',
                       'proforma_refund': 'item_for_sale',
                       'cancel_refund': 'item_sold',}

class account_voucher(osv.osv):

    _inherit = 'account.voucher'
    _rec_name = 'number'

    def _update_items_location_status(self, cr, uid, ids, voucher_state, context=None):
        if context == None:
            context = {}
        if voucher_state and (voucher_state in LOCATION_STATUS_MAP):
            loc_status_obj = self.pool.get('product.location.status')
            for voucher in self.pool.get('account.voucher').browse(cr, uid, ids, context=context):
                item_ids = []
                for line in voucher.line_cr_ids:
                    # products for sales not update location status
                    if line.product_id.for_sale:
                        continue
                    # --
                    if line.product_id:
                        item_ids.append(line.product_id.id)
                if voucher.is_refund:
                    voucher_state += '_refund'
                to_loc_status = loc_status_obj.search(cr, uid, [('code', '=', LOCATION_STATUS_MAP[voucher_state])])[0]
                self.pool.get('product.product').write(cr, uid, item_ids, {'location_status': to_loc_status})
            return True

    def _estimated_total(self, cr, uid, voucher_id):
        cr.execute("""
            select sum(pp.price_estimated * avl.quantity) estimated_total from account_voucher_line avl
            join product_product pp on pp.id = avl.product_id
            where avl.voucher_id = %s
        """, (voucher_id,))
        return cr.fetchone()[0] or 0.0

    def _update_voucher_line_price_unit(self, cr, uid, ids, price_total, context=None):
        voucher_line_obj = self.pool.get('account.voucher.line')
        # Get estimated_total
        for voucher in self.browse(cr, uid, ids, context=context):
            total_estimated = self._estimated_total(cr, uid, voucher.id)
            if not total_estimated:
                raise osv.except_osv(_('Error!'), _('Sum of estimated price is zero.\nDivided by Zero Error.'))
            num_item = len(voucher.line_cr_ids)
            i = 0
            total_amount = 0.0
            for line in voucher.line_cr_ids:
                if not line.product_id.order_id:
                    raise osv.except_osv(_('Error!'), _('Not allowed update amount in sale receipt lines because of there is some product not pawn item.'))
                i += 1
                if i == num_item:  # Last line
                    line_amount = round(voucher.amount - total_amount, 2)
                    line_price_unit = line.quantity and line_amount / line.quantity or 0.0
                else:
                    line_estimated = line.product_id.price_estimated * line.quantity
                    line_ratio = float(line_estimated / total_estimated)
                    line_amount = round(line_ratio * price_total, 2)
                    line_price_unit = line.quantity and line_amount / line.quantity or 0.0
                    total_amount += line_amount
                voucher_line_obj.write(cr, uid, [line.id], {'price_unit': line_price_unit,
                                                                'amount': line_amount})
        return True

    def _check_duplicate_item(self, cr, uid, ids, context=None):
        voucher_line_obj = self.pool.get('account.voucher.line')
        for voucher in self.browse(cr, uid, ids, context=context):
            item_ids = []
            for line in voucher.line_cr_ids:
                # products for sales can duplicate
                if line.product_id.for_sale:
                    continue
                # --
                if line.product_id:
                    item_ids.append(line.product_id.id)
            for item_id in list(set(item_ids)):
                voucher_line_ids = voucher_line_obj.search(cr, uid, [('voucher_id.state', '!=', 'cancel'), ('product_id', '=', item_id)])
                if len(voucher_line_ids) > 1:
                    return False
        return True

    def _check_different_journal(self, cr, uid, ids, context=None):
        for voucher in self.browse(cr, uid, ids, context=context):
            journal_ids = list(set([line.product_id.journal_id.id for line in voucher.line_cr_ids if line.product_id.journal_id]))
            if len(journal_ids) > 1:
                return False
        return True

    def _check_different_shop(self, cr, uid, ids, context=None):
        for voucher in self.browse(cr, uid, ids, context=context):
            shop_ids = list(set([line.product_id.pawn_shop_id.id for line in voucher.line_cr_ids if line.product_id.pawn_shop_id]))
            if len(shop_ids) > 1:
                return False
        return True

    def _compute_product_journal_id(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            # Default product journal
            journal_ids = self.pool.get('account.journal').search(cr, uid, [('company_id', '=', voucher.company_id.id), ('type', '=', 'cash'), ('pawn_journal', '=', True)], limit=1)
            res[voucher.id] = journal_ids and journal_ids[0] or False
            # Update journal from product
            journal_ids = list(set([line.product_id.journal_id.id for line in voucher.line_ids if line.product_id.journal_id]))
            if journal_ids:
                res[voucher.id] = journal_ids and journal_ids[0] or False
        return res

    _columns = {
        'docnumber': fields.integer('DocNumber', select=True, readonly=True),
        'pawn_shop_id': fields.many2one('pawn.shop', 'Shop', domain="[('company_id','=',company_id)]", readonly=True, states={'draft': [('readonly', False)]}),
        'pawnshop': fields.boolean('Pawnshop', help="By checking this flag, the journal entry from this document will be different from normal Sales Receipt"),
        'ref_voucher_id': fields.many2one('account.voucher', 'Ref Sales Receipt', readonly=True),
        'is_refund': fields.boolean('Refund', readonly=True),
        'product_journal_id': fields.function(_compute_product_journal_id, type='many2one', relation='account.journal', string='Product Journal', store=True, readonly=True),
        'address': fields.related('partner_id', 'address_full', type='char', string='Address'),
    }

    _constraints = [
        (_check_duplicate_item, 'Items must be unique on the sales receipt', ['line_cr_ids']),
        (_check_different_journal, 'Item from different journal is not allowed', ['line_cr_ids']),
        (_check_different_shop, 'Item from different shop is not allowed', ['line_cr_ids']),
    ]

    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        if not company_id:
            return {}
        # Find shop
        shop_ids = self.pool.get('pawn.shop').search(cr, uid, [('company_id', '=', company_id), ('user_ids', 'in', uid)], context=context)
        shop_id = shop_ids and shop_ids[0] or False
        # Find journal
        journal_ids = self.pool.get('account.journal').search(cr, uid,
            [('type', '=', 'sale'), ('company_id', '=', company_id)])
        journal_id = journal_ids and journal_ids[0] or False
        return {'value': {'pawn_shop_id': shop_id, 'journal_id': journal_id}}

    def _get_next_name(self, cr, uid, date, pawn_shop_id, is_refund, context=None):
        year = date and date[:4] or time.strftime('%Y-%m-%d')[:4]
        # Get year from date
        cr.execute("""select coalesce(max(docnumber), 0) from account_voucher
            where to_char(date, 'YYYY') = %s and pawn_shop_id = %s and is_refund = %s""",
            (year, pawn_shop_id, is_refund))
        number = cr.fetchone()[0] or 0
        number += 1
        shop_code = '--'
        if is_refund:
            shop_code = self.pool.get('pawn.shop').browse(cr, uid, pawn_shop_id).sref_code
        else:
            shop_code = self.pool.get('pawn.shop').browse(cr, uid, pawn_shop_id).srec_code
        next_name = shop_code + '/' + year + '/' + str(number).zfill(3)
        return next_name, number

    def write(self, cr, uid, ids, vals, context=None):
        # Reset location status before update voucher lines
        if vals.get('line_cr_ids', False):
            for voucher in self.browse(cr, uid, ids, context=context):
                voucher_state = 'cancel'
                self._update_items_location_status(cr, uid, [voucher.id], voucher_state, context=context)
        # --
        res = super(account_voucher, self).write(cr, uid, ids, vals, context=context)
        # If Price Total is set, calculate the appropriate price.
        if vals.get('amount', False) and not vals.get('line_cr_ids', False):
            self._update_voucher_line_price_unit(cr, uid, ids, vals.get('amount'), context=context)
        # update item's location status by voucher state
        if vals.get('line_cr_ids', False) or vals.get('state', False):
            for voucher in self.browse(cr, uid, ids, context=context):
                voucher_state = voucher.state
                self._update_items_location_status(cr, uid, [voucher.id], voucher_state, context=context)
        return res

    def create(self, cr, uid, data, context=None):
        # Only for Sales Receipt have its own number
        if (data.get('number', '/') == '/' or data.get('number') == False) and data.get('pawnshop', False) and data.get('type', False) == 'sale':
            number, docnumber = self._get_next_name(cr, uid, data.get('date', False), data.get('pawn_shop_id', False), data.get('is_refund', False), context=context)
            data.update({'number': number, 'docnumber': docnumber})
        # --
        voucher_id = super(account_voucher, self).create(cr, uid, data, context=context)
        voucher_state = 'draft'  # Assume voucher draft, so we update the location_status
        self._update_items_location_status(cr, uid, [voucher_id], voucher_state, context=context)
        return voucher_id

    def action_move_line_create(self, cr, uid, ids, context=None):
        for voucher in self.browse(cr, uid, ids, context=context):
            if voucher.pawnshop:
                self.action_pawn_move_line_create(cr, uid, [voucher.id], context=context)
            else:
                super(account_voucher, self).action_move_line_create(cr, uid, [voucher.id], context=context)
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        raise osv.except_osv(_('Forbbiden to duplicate'), _('Is not possible to duplicate the record, please create a new one.'))

    def action_pawn_move_line_create(self, cr, uid, ids, context=None):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        for voucher in self.browse(cr, uid, ids, context=context):
            local_context = dict(context, force_company=voucher.journal_id.company_id.id)
            if voucher.move_id:
                continue
            company_currency = self._get_company_currency(cr, uid, voucher.id, context)
            current_currency = self._get_current_currency(cr, uid, voucher.id, context)
            # we select the context to use accordingly if it's a multicurrency case or not
            context = self._sel_context(cr, uid, voucher.id, context)
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = context.copy()
            ctx.update({'date': voucher.date})
            # Create the account move record.
            move_id = move_pool.create(cr, uid, self.account_move_get(cr, uid, voucher.id, context=context), context=context)
            # Get the name of the account_move just created
            name = move_pool.browse(cr, uid, move_id, context=context).name
            # Create the first line of the voucher
#             move_line_id = move_line_pool.create(cr, uid, self.first_move_line_get(cr,uid,voucher.id, move_id, company_currency, current_currency, local_context), local_context)
#             move_line_brw = move_line_pool.browse(cr, uid, move_line_id, context=context)
#             line_total = move_line_brw.debit - move_line_brw.credit
            # rec_list_ids = []
            # Create one move line per voucher line where amount is not 0.0
            self.voucher_pawn_move_line_create(cr, uid, voucher.id, move_id, company_currency, current_currency, context)

            # Create the writeoff line if needed
#             ml_writeoff = self.writeoff_move_line_get(cr, uid, voucher.id, line_total, move_id, name, company_currency, current_currency, local_context)
#             if ml_writeoff:
#                 move_line_pool.create(cr, uid, ml_writeoff, local_context)
            # We post the voucher.
            self.write(cr, uid, [voucher.id], {
                'move_id': move_id,
                'state': 'posted',
                'number': name,
            })
            if voucher.journal_id.entry_posted:
                move_pool.post(cr, uid, [move_id], context={})
            # We automatically reconcile the account move lines.
            # reconcile = False
            # for rec_ids in rec_list_ids:
            #     if len(rec_ids) >= 2:
            #         reconcile = move_line_pool.reconcile_partial(cr, uid, rec_ids, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id)
        return True


    def voucher_pawn_move_line_create(self, cr, uid, voucher_id, move_id, company_currency, current_currency, context=None):
        '''
            ขายทรัพย์หลุด (เล้า)
            ราคาประเมิน 900,000 บาท
            ราคารับจำนำ 850,000 บาท
            ราคาขายทรัพย์หลุด 910,000 บาท

            Income from Sale of Reposessed Goods
            CODE    DESCRIPTION    DR.    CR.
            1111-00    เงินสด     910,000.00
            4100-02    รายได้จากการขายทรัพย์หลุด         910,000.00

            Cost of goods sold
            CODE    DESCRIPTION    DR.    CR.
            5110-00    ต้นทุนขายทรัพย์หลุด     850,000.00
            1150-00    ทรัพย์หลุดเป็นสิทธิ         850,000.00
        '''
        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        rec_lst_ids = []

        date = self.read(cr, uid, voucher_id, ['date'], context=context)['date']
        ctx = context.copy()
        ctx.update({'date': date})
        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=ctx)
        voucher_currency = voucher.journal_id.currency or voucher.company_id.currency_id
        ctx.update({
            'voucher_special_currency_rate': voucher_currency.rate * voucher.payment_rate ,
            'voucher_special_currency': voucher.payment_rate_currency_id and voucher.payment_rate_currency_id.id or False,})
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        all_move_lines = []
        for line in voucher.line_ids:
            #create one move line per voucher line where amount is not 0.0
            # AND (second part of the clause) only if the original move line was not having debit = credit = 0 (which is a legal value)
            if not line.amount and not (line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit, precision_digits=prec) and not float_compare(line.move_line_id.debit, 0.0, precision_digits=prec)):
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_curreny.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            amount = self._convert_amount(cr, uid, line.amount, voucher.id, context=ctx)
            # if the amount encoded in voucher is equal to the amount unreconciled, we need to compute the
            # currency rate difference
            if line.amount == line.amount_unreconciled:
                if not line.move_line_id:
                    raise osv.except_osv(_('Wrong voucher line'),_("The invoice you are willing to pay is not valid anymore."))
                sign = voucher.type in ('payment', 'purchase') and -1 or 1
                currency_rate_difference = sign * (line.move_line_id.amount_residual - amount)
            else:
                currency_rate_difference = 0.0

            # Get pawn info
            pawn_order = pawn_shop = profit_center = product = debit_account = False
            product = line.product_id
            if product:
                pawn_order = product.order_id
                if pawn_order:
                    pawn_shop = pawn_order.pawn_shop_id
                    profit_center = pawn_order.journal_id.profit_center
                    debit_account = pawn_order.journal_id.default_debit_account_id

            # Products For Sales
            if line.product_id.for_sale:
                pawn_shop = voucher.pawn_shop_id
                profit_center = voucher.product_journal_id.profit_center
                debit_account = voucher.product_journal_id.default_debit_account_id

            move_line = {
                # For Pawn
                'product_id': product and product.id or False,
                'pawn_order_id': pawn_order and pawn_order.id or False,
                'pawn_shop_id': pawn_shop and pawn_shop.id or False,
                'profit_center': profit_center,
                # --
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': voucher.date
            }
            if amount < 0:
                amount = -amount
                if line.type == 'dr':
                    line.type = 'cr'
                else:
                    line.type = 'dr'
            if (line.type=='dr'):
                move_line['debit'] = amount
            else:
                move_line['credit'] = amount

            # compute the amount in foreign currency
            foreign_currency_diff = 0.0
            amount_currency = False
            if line.move_line_id:
                # We want to set it on the account move line as soon as the original line had a foreign currency
                if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency:
                    # we compute the amount in that foreign currency.
                    if line.move_line_id.currency_id.id == current_currency:
                        # if the voucher and the voucher line share the same currency, there is no computation to do
                        sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                        amount_currency = sign * (line.amount)
                    else:
                        # if the rate is specified on the voucher, it will be used thanks to the special keys in the context
                        # otherwise we use the rates of the system
                        amount_currency = currency_obj.compute(cr, uid, company_currency, line.move_line_id.currency_id.id, move_line['debit']-move_line['credit'], context=ctx)
                if line.amount == line.amount_unreconciled:
                    sign = voucher.type in ('payment', 'purchase') and -1 or 1
                    foreign_currency_diff = sign * line.move_line_id.amount_residual_currency + amount_currency

            move_line['amount_currency'] = amount_currency
            # voucher_line = move_line_obj.create(cr, uid, move_line)
            # rec_ids = [voucher_line, line.move_line_id.id]

            # PAWN: Create reverse line, for the same amount but different account
            move_line_cash = move_line.copy()
            debit = move_line_cash['debit']
            credit = move_line_cash['credit']
            move_line_cash['debit'] = credit
            move_line_cash['credit'] = debit
            move_line_cash['account_id'] = debit_account.id
            move_line_cash['name'] = '/'
            move_line_cash['product_id'] = False
            # rec_ids.append(move_line_obj.create(cr, uid, move_line_cash))

            move_lines = [
                (0, 0, move_line),
                (0, 0, move_line_cash),
            ]

            # products for sales not create cost move lines
            if not line.product_id.for_sale:
                # PAWN: Create Cost Move Lines
                prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
                move_line_cost = move_line.copy()
                move_line_cost['account_id'] = product.property_account_cost_reposessed_asset.id
                amount = round(product.price_pawned * line.quantity, prec)
                amount = amount < 0 and - amount or amount
                # Reverse it for cost
                if move_line_cost['debit']:
                    move_line_cost['credit'] = amount
                    move_line_cost['debit'] = False
                elif move_line_cost['credit']:
                    move_line_cost['debit'] = amount
                    move_line_cost['credit'] = False
                # rec_ids.append(move_line_obj.create(cr, uid, move_line_cost))
                # Reverse it!
                move_line_cost_reverse = move_line_cost.copy()
                move_line_cost_reverse['debit'] = move_line_cost['credit']
                move_line_cost_reverse['credit'] = move_line_cost['debit']
                move_line_cost_reverse['account_id'] = product.property_account_expire_asset.id
                # rec_ids.append(move_line_obj.create(cr, uid, move_line_cost))

                move_lines.extend([
                    (0, 0, move_line_cost),
                    (0, 0, move_line_cost_reverse),
                ])

            all_move_lines += move_lines

        # Write all records at once after looping
        self.pool.get('account.move').write(cr, uid, [move_id], {'line_id': all_move_lines})

        return True

    def refund_voucher(self, cr, uid, ids, context):
        if context == None:
            context = {}
        if len(ids) > 1:
            raise osv.except_osv(_('Error!'), _("Please select only 1 receipt to refund!"))
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale_refund'),
                                                                        ('company_id', '=', company.id)], limit=1)
        voucher_id = self.copy(cr, uid, ids[0], {'journal_id': journal_ids[0],
                                                 'is_refund': True,
                                                 'ref_voucher_id': ids[0]}, context=context)
        self.write(cr, uid, ids, {'ref_voucher_id': voucher_id})
        # Reverse amount
        cr.execute('update account_voucher_line set quantity = -quantity, amount = -amount where voucher_id = %s', (voucher_id,))
        cr.execute('update account_voucher set amount = -amount where id = %s', (voucher_id,))
        # Update account
        voucher_line = self.pool.get('account.voucher.line')
        for line in self.browse(cr, uid, voucher_id).line_cr_ids:
            voucher_line.write(cr, uid, [line.id], {'account_id': line.product_id.property_account_refund_reposessed_asset.id}, context=context)
        return self.open_vouchers(cr, uid, ids, voucher_id, context=context)

    def open_vouchers(self, cr, uid, ids, voucher_id, context=None):
        """ open a view on one of the given voucher_ids """
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'account_voucher', 'view_sale_receipt_form')
        form_id = form_res and form_res[1] or False
        tree_res = ir_model_data.get_object_reference(cr, uid, 'account_voucher', 'view_voucher_tree')
        tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Sales Refund Receipt'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'account.voucher',
            'res_id': voucher_id,
            'view_id': False,
            'views': [(form_id, 'form'), (tree_id, 'tree')],
            'context': "{'default_type': 'sale', 'type': 'sale'}",
            'type': 'ir.actions.act_window',
        }

    def proforma_voucher(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if context.get('is_account_transfer', False):
            context.update({'voucher_id': ids[0]})
        voucher = self.browse(cr, uid, ids[0], context=context)
        if not voucher.amount:
            raise osv.except_osv(_('Warning'),
                                 _("Please verify that the total amount of this Sales Receipt is not zero!"))
        if 0 in [v.amount or 0.0 for v in voucher.line_ids]:
            raise osv.except_osv(_('Warning'),
                                 _("Please verify that every line amount of this Sales Receipt is not zero!"))

        product_ids = list(set([x.product_id.id for x in voucher.line_ids if x.product_id and not x.product_id.for_sale]))
        if len(product_ids) > 0:
            self.pool.get('product.product').write(cr, uid, product_ids, {'date_sold': voucher.date}, context=context)
        return super(account_voucher, self).proforma_voucher(cr, uid, ids, context=context)

    # THIS IS A COMPLETE OVERWRITE METHOD
    # Just to pass context to create account_move_line
    def voucher_move_line_create(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency, context=None):
        '''
        Create one account move line, on the given account move, per voucher line where amount is not 0.0.
        It returns Tuple with tot_line what is total of difference between debit and credit and
        a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).

        :param voucher_id: Voucher id what we are working with
        :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
        :param move_id: Account move wher those lines will be joined.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
        :rtype: tuple(float, list of int)
        '''
        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        tot_line = line_total
        rec_lst_ids = []

        date = self.read(cr, uid, voucher_id, ['date'], context=context)['date']
        ctx = context.copy()
        ctx.update({'date': date})
        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=ctx)
        voucher_currency = voucher.journal_id.currency or voucher.company_id.currency_id
        ctx.update({
            'voucher_special_currency_rate': voucher_currency.rate * voucher.payment_rate ,
            'voucher_special_currency': voucher.payment_rate_currency_id and voucher.payment_rate_currency_id.id or False,})
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        for line in voucher.line_ids:
            #create one move line per voucher line where amount is not 0.0
            # AND (second part of the clause) only if the original move line was not having debit = credit = 0 (which is a legal value)
            if not line.amount and not (line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit, precision_digits=prec) and not float_compare(line.move_line_id.debit, 0.0, precision_digits=prec)):
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_curreny.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            amount = self._convert_amount(cr, uid, line.untax_amount or line.amount, voucher.id, context=ctx)
            # if the amount encoded in voucher is equal to the amount unreconciled, we need to compute the
            # currency rate difference
            if line.amount == line.amount_unreconciled:
                if not line.move_line_id:
                    raise osv.except_osv(_('Wrong voucher line'),_("The invoice you are willing to pay is not valid anymore."))
                sign = voucher.type in ('payment', 'purchase') and -1 or 1
                currency_rate_difference = sign * (line.move_line_id.amount_residual - amount)
            else:
                currency_rate_difference = 0.0
            move_line = {
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'currency_id': line.move_line_id and (company_currency <> line.move_line_id.currency_id.id and line.move_line_id.currency_id.id) or False,
                'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': voucher.date
            }
            if amount < 0:
                amount = -amount
                if line.type == 'dr':
                    line.type = 'cr'
                else:
                    line.type = 'dr'

            if (line.type=='dr'):
                tot_line += amount
                move_line['debit'] = amount
            else:
                tot_line -= amount
                move_line['credit'] = amount

            if voucher.tax_id and voucher.type in ('sale', 'purchase'):
                move_line.update({
                    'account_tax_id': voucher.tax_id.id,
                })

            if move_line.get('account_tax_id', False):
                tax_data = tax_obj.browse(cr, uid, [move_line['account_tax_id']], context=context)[0]
                if not (tax_data.base_code_id and tax_data.tax_code_id):
                    raise osv.except_osv(_('No Account Base Code and Account Tax Code!'),_("You have to configure account base code and account tax code on the '%s' tax!") % (tax_data.name))

            # compute the amount in foreign currency
            foreign_currency_diff = 0.0
            amount_currency = False
            if line.move_line_id:
                # We want to set it on the account move line as soon as the original line had a foreign currency
                if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency:
                    # we compute the amount in that foreign currency.
                    if line.move_line_id.currency_id.id == current_currency:
                        # if the voucher and the voucher line share the same currency, there is no computation to do
                        sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                        amount_currency = sign * (line.amount)
                    else:
                        # if the rate is specified on the voucher, it will be used thanks to the special keys in the context
                        # otherwise we use the rates of the system
                        amount_currency = currency_obj.compute(cr, uid, company_currency, line.move_line_id.currency_id.id, move_line['debit']-move_line['credit'], context=ctx)
                if line.amount == line.amount_unreconciled:
                    sign = voucher.type in ('payment', 'purchase') and -1 or 1
                    foreign_currency_diff = sign * line.move_line_id.amount_residual_currency + amount_currency

            move_line['amount_currency'] = amount_currency
            # kittiu: Pass context
            #voucher_line = move_line_obj.create(cr, uid, move_line)
            voucher_line = move_line_obj.create(cr, uid, move_line, context=context)
            # --
            rec_ids = [voucher_line, line.move_line_id.id]

            if not currency_obj.is_zero(cr, uid, voucher.company_id.currency_id, currency_rate_difference):
                # Change difference entry in company currency
                exch_lines = self._get_exchange_lines(cr, uid, line, move_id, currency_rate_difference, company_currency, current_currency, context=context)
                new_id = move_line_obj.create(cr, uid, exch_lines[0],context)
                move_line_obj.create(cr, uid, exch_lines[1], context)
                rec_ids.append(new_id)

            if line.move_line_id and line.move_line_id.currency_id and not currency_obj.is_zero(cr, uid, line.move_line_id.currency_id, foreign_currency_diff):
                # Change difference entry in voucher currency
                move_line_foreign_currency = {
                    'journal_id': line.voucher_id.journal_id.id,
                    'period_id': line.voucher_id.period_id.id,
                    'name': _('change')+': '+(line.name or '/'),
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': line.voucher_id.partner_id.id,
                    'currency_id': line.move_line_id.currency_id.id,
                    'amount_currency': -1 * foreign_currency_diff,
                    'quantity': 1,
                    'credit': 0.0,
                    'debit': 0.0,
                    'date': line.voucher_id.date,
                }
                new_id = move_line_obj.create(cr, uid, move_line_foreign_currency, context=context)
                rec_ids.append(new_id)
            if line.move_line_id.id:
                rec_lst_ids.append(rec_ids)
        return (tot_line, rec_lst_ids)

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for voucher in self.browse(cr, uid, ids, context=context):
            res.append((voucher.id, voucher.number))
        return res


account_voucher()


class account_voucher_line(osv.osv):

    _inherit = 'account.voucher.line'

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', ondelete='set null', select=True),
        'quantity': fields.float('Quantity', digits_compute= dp.get_precision('Product Unit of Measure')),
        'uos_id': fields.many2one('product.uom', 'Unit of Measure', ondelete='set null', select=True),
        'price_unit': fields.float('Unit Price', digits_compute= dp.get_precision('Product Price')),
        'is_jewelry': fields.boolean('Carat/Gram', readonly=True),
        'carat': fields.float('Carat', readonly=True),
        'gram': fields.float('Gram', readonly=True),
        'price_estimated': fields.float('Estimated Price', digits_compute=dp.get_precision('Account'), readonly=True),
        'total_price_pawned': fields.float('Total Pawned Price', digits_compute=dp.get_precision('Account'), readonly=True),
        'for_sale': fields.boolean('For Sale'),
    }

    def onchange_price(self, cr, uid, ids, field, quantity, price_unit, amount, context=None):
        res = {'value': {}}
        quantity = float(quantity)
        if field in ('quantity', 'price_unit'):
            prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
            amount = quantity * price_unit
            res['value']['amount'] = round(amount, prec)
        elif field == 'amount':
            prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price')
            if not quantity:
                res['value']['quantity'] = quantity = 1.0
            price_unit = amount / quantity
            res['value']['price_unit'] = round(price_unit, prec)
        return res

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        res = {'value': {}}
        if product_id:
            item = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            account_id = item.property_account_revenue_reposessed_asset.id
            # products for sales
            if item.for_sale:
                account_id = item.property_account_income.id
            # --
            res['value'].update({
                'name': item.description or item.name,
                'account_id': account_id,
                'price_unit': item.standard_price,
                'quantity': item.product_qty or 1.0,
                'uos_id': item.uom_id.id,
                'is_jewelry': item.is_jewelry,
                'carat': item.carat,
                'gram': item.gram,
                'price_estimated': item.price_estimated,
                'total_price_pawned': item.total_price_pawned,
                'for_sale': item.for_sale,
            })
        return res

    def _update_field(self, cr, uid, vals, context=None):
        if 'product_id' in vals and vals['product_id']:
            voucher_line_dict = self.onchange_product_id(cr, uid, [], vals['product_id'][0] if type(vals['product_id']) is tuple else vals['product_id'], context=context)['value']
            for key in voucher_line_dict.keys():
                if key not in vals:
                    vals[key] = voucher_line_dict[key]
        return vals

    def create(self, cr, uid, vals, context=None):
        vals = self._update_field(cr, uid, vals, context=context)
        return super(account_voucher_line, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        vals = self._update_field(cr, uid, vals, context=context)
        return super(account_voucher_line, self).write(cr, uid, ids, vals, context=context)

account_voucher_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
