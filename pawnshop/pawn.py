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
import logging
import time
import res_partner
import res_config
from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp import netsvc, tools
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)
from dateutil.relativedelta import relativedelta
NUMBER_PER_BOOK = 100

STATE_SELECTION = [
        ('draft', 'Draft Pawn Ticket'),
        ('pawn', 'Pawned'),
        ('redeem', 'Redeemed'),
        ('expire', 'Expired'),
        ('cancel', 'Cancelled')
    ]

MAX_LINE = 8
# def months_between(start_date, end_date):
#     #Add 1 day to end date to solve different last days of month
#     s1, e1 = start_date, end_date + timedelta(days=1)
#     #Convert to 360 days
#     s360 = (s1.year * 12 + s1.month) * 30 + s1.day
#     e360 = (e1.year * 12 + e1.month) * 30 + e1.day
#     #Count days between the two 360 dates and return tuple (months, days)
#     return divmod(e360 - s360, 30)


def last_day_of_month(date):
    if date.month == 12:
        return date.replace(day=31)
    return date.replace(month=date.month + 1, day=1) - timedelta(days=1)


class pawn_order(osv.osv):

    _name = 'pawn.order'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Pawn Ticket'
    _track = {
        'state': {
            'pawn.mt_ticket_pawn': lambda self, cr, uid, obj, ctx=None: obj['state'] in ['pawn'],
            'pawn.mt_ticket_redeem': lambda self, cr, uid, obj, ctx=None: obj['state'] in ['redeem']
        },
    }

    def _get_item_description(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for pawn in self.browse(cr, uid, ids, context=context):
            item_description = ''
            if pawn.order_line:
                for order_line in pawn.order_line:
                    jewelry_desc = ''
                    if order_line and order_line.is_jewelry:
                        if order_line.carat and order_line.gram:
                            jewelry_desc = ' [' + str(order_line.carat) + ' ' + _('กะรัต') + ', ' + str(order_line.gram) + ' ' + _('กรัม') + ']'
                        elif order_line.carat and not order_line.gram:
                            jewelry_desc = ' [' + str(order_line.carat) + ' ' + _('กะรัต') + ']'
                        elif not order_line.carat and order_line.gram:
                            jewelry_desc = ' [' + str(order_line.gram) + ' ' + _('กรัม') + ']'
                    item_description += order_line.name + jewelry_desc + u' (' + str(order_line.product_qty or 0.0) + '), '
                item_description = item_description[:-2]
#             elif item.description:
#                 item_description = item.description
            res[pawn.id] = item_description
        return res

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        cur_obj = self.pool.get('res.currency')
        for pawn in self.browse(cr, uid, ids, context=context):
            res[pawn.id] = {
                'amount_total': 0.0,
            }
            val = 0.0
            cur = pawn.pricelist_id.currency_id
            for line in pawn.order_line:
                val += line.price_subtotal
            res[pawn.id]['amount_total'] = cur_obj.round(cr, uid, cur, val)
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('pawn.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    def _calculate_pawn_interest(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, False)
        rule_obj = self.pool.get('pawn.rule')
        for pawn in self.browse(cr, uid, ids, context=context):
            res[pawn.id] = {
                'date_expired': False,
                'monthly_interest': False,
                'daily_interest': False,
            }
            rule = rule_obj.browse(cr, uid, pawn.rule_id.id, context=context)
            # Expired Date (i.e., 30 days after expired date)
            res[pawn.id]['date_expired'] = rule_obj._get_date_expired(cr, uid, pawn.rule_id.id, pawn.date_order, context=context)
            # Date Due (i.e., 30 days after expired date)
            #date_due = res[pawn.id]['date_expired'] + relativedelta(days=rule.length_day or 0.0)
            #res[pawn.id]['date_due'] = date_due
            # Monthly Interest
            res[pawn.id]['monthly_interest'] = rule_obj.calculate_monthly_interest(cr, uid, pawn.rule_id.id, pawn.amount_pawned, context=context)
            # Daily Interest (calculate from month only, i.e., 4 months + 1
            total_interest = (rule.length_month) * res[pawn.id]['monthly_interest']
            start_date = datetime.strptime(pawn.date_order[:10], '%Y-%m-%d')
            total_days = (res[pawn.id]['date_expired'] - start_date).days
            res[pawn.id]['daily_interest'] = total_interest / total_days
        return res

    def _get_interest_todate(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for pawn in self.browse(cr, uid, ids, context=context):
            res[pawn.id] = {
                'amount_interest_todate': 0.0,
                'last_interest_date': False,
                'is_interest_updated': False,
            }
            # Get sum of accrued intererst (debit account of interest journal of this pawn_order
            acct_id = pawn.property_journal_accrued_interest.default_debit_account_id.id
            cr.execute("""
                select sum(debit) - sum(credit) as amount from account_move_line
                where pawn_order_id = %s and account_id = %s
                """, (pawn.id, acct_id))
            interest_todate = cr.fetchone()[0] or 0.0
            res[pawn.id]['amount_interest_todate'] = interest_todate
            # Get last calculation date
            cr.execute("""
                select max(date) as date from account_move_line
                where pawn_order_id = %s and account_id = %s
                """, (pawn.id, acct_id))
            last_interest_date = cr.fetchone()[0] or False
            res[pawn.id]['last_interest_date'] = last_interest_date
            res[pawn.id]['is_interest_updated'] = last_interest_date and last_interest_date == fields.date.context_today(self, cr, uid, context=context) and True or False
        return res

#     def _get_address(self, cr, uid, ids, field_name, arg, context=None):
#         res = dict.fromkeys(ids, False)
#         for pawn in self.browse(cr, uid, ids, context=context):
#             address = pawn.partner_id.street
#             if pawn.partner_id.street2:
#                 address += address and ' ' + str(pawn.partner_id.street2)
#             if pawn.partner_id.city:
#                 address += address and ', ' + str(pawn.partner_id.city)
#             if pawn.partner_id.zip:
#                 address += address and ', ' + str(pawn.partner_id.zip)
#             res[pawn.id] = address
#         return res

    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company_id = context.get('company_id', user.company_id.id)
        journal_obj = self.pool.get('account.journal')
        domain = [('company_id', '=', company_id), ('type', '=', 'cash'), ('pawn_journal', '=', True)]
        res = journal_obj.search(cr, uid, domain, limit=1)
        return res and res[0] or False

    def _get_period(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('period_id', False):
            return context.get('period_id')
        ctx = dict(context, account_period_prefer_normal=True)
        periods = self.pool.get('account.period').find(cr, uid, context=ctx)
        return periods and periods[0] or False

    def _check_product(self, cr, uid, ids, context=None):
        all_prod = []
        boms = self.browse(cr, uid, ids, context=context)
        # kittiu
        parent_bom = boms[0]
        is_one_time_use = parent_bom.product_id.is_one_time_use
        # -- kittiu
        def check_bom(boms):
            res = True
            for bom in boms:
                # kittiu
                #if bom.product_id.id in all_prod:
                if ((bom.bom_id and not bom.bom_id.is_bom_template and not is_one_time_use) or not bom.bom_id) and bom.product_id.id in all_prod:
                    res = res and False
                #-- kittiu
                all_prod.append(bom.product_id.id)
                lines = bom.bom_lines
                if lines:
                    res = res and check_bom([bom_id for bom_id in lines if bom_id not in boms])
            return res
        return check_bom(boms)

    def _get_previous_pawn_ids(self, cr, uid, ids, field_names, arg=None, context=None):
        result = {}
        if not ids:
            return result
        for id in ids:
            result.setdefault(id, [])

        def previous_pawn_ids(pawn_id, result, pawn):
            if pawn.parent_id:
                result[pawn_id].append(pawn.parent_id.id)
                if pawn.parent_id.parent_id:
                    previous_pawn_ids(pawn_id, result, pawn.parent_id)

        for pawn in self.browse(cr, uid, ids, context=context):
            previous_pawn_ids(pawn.id, result, pawn)

        return result

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image, avoid_resize_medium=True)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    def _get_extended(self, cr, uid, ids, name, args, context=None):
        res = {}
        for pawn in self.browse( cr, uid, ids, context=context):
            if pawn.extended:
                res[pawn.id] = 'x'
            else:
                res[pawn.id] = ''
        return res
#
#     def _order_day(self, cr, uid, ids, field_name, arg, context=None):
#         res = dict.fromkeys(ids, False)
#         for pawn in self.browse(cr, uid, ids, context=context):
#             res[pawn.id] = pawn.date_order
#             val = 0.0
#             cur = pawn.pricelist_id.currency_id
#             for line in pawn.order_line:
#                 val += line.price_subtotal
#             res[pawn.id]['amount_total'] = cur_obj.round(cr, uid, cur, val)
#         return res

    _columns = {
        'name': fields.char('Pawn Reference', size=64, required=True, select=True, help="Unique number of the pawn ticket, computed automatically when the ticket is created."),
        'book': fields.integer('Book', select=True, readonly=True),
        'number': fields.integer('Number', select=True, readonly=True),
        'name': fields.char('Internal Number', size=64, required=True, select=True, help="Cross shop reference number"),
        'date_order': fields.date('Pawn Date', required=True, readonly=True, select=True, help="Date on which this document has been pawned."),
        'day_order': fields.related('date_order', type="char", string="Pawn Day", required=False, readonly=True, store=True),
        'buddha_year': fields.char('Buddha Year', size=4, readonly=True),
        'buddha_year_temp': fields.char('Buddha Year Temp', size=4),
        'date_redeem': fields.date('Redeem Date', required=False, readonly=True, help="Date on which this document has been redeemed."),
        'date_extend': fields.date('Extend Date', required=False, readonly=True, help="Date on which this document has been extended."),
        'date_extend_last': fields.date('Last Extend Date', required=False, readonly=True, help="Latest Date on which this document has been extended."),
        'date_unextend_last': fields.date('Last Unextend Date', required=False, readonly=True, help="Latest Date on which this document has been unextended."),
        'partner_id': fields.many2one('res.partner', 'Customer', required=True, readonly=True, domain=[('supplier', '=', True), ('pawnshop', '=', True)], states={'draft': [('readonly', False)]}, change_default=True),
        'address': fields.related('partner_id', 'address_full', type='char', string='Address'),
        'card_type': fields.related('partner_id', 'card_type', type="selection", selection=res_partner.CARD_TYPE_SELECTION, string="Card Type", readonly=True),
        'card_number': fields.related('partner_id', 'card_number', type="char", string="Card Number", readonly=True),
        'age': fields.related('partner_id', 'age', type="integer", string="Age", readonly=True),
        'pawn_shop_id': fields.many2one('pawn.shop', 'Shop', domain="[('company_id','=',company_id)]", readonly=True, required=True, states={'draft': [('readonly', False)]}),
        #'location_id': fields.many2one('stock.location', 'Destination', required=True, domain=[('usage', '<>', 'view')], states={'draft': [('readonly', False)]},),
        'rule_id': fields.many2one('pawn.rule', 'Pawn Rule', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', required=True, readonly=True, states={'draft': [('readonly', False)]}, help="The pricelist sets the currency used for this pawn ticket. It also computes the price for the selected products/quantities."),
        'currency_id': fields.related('pricelist_id', 'currency_id', type="many2one", relation="res.currency", string="Currency", readonly=True, required=True),
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True, help="The status of the pawn ticket", select=True, track_visibility='onchange'),
        'order_line': fields.one2many('pawn.order.line', 'order_id', 'Order Lines', readonly=True, states={'draft': [('readonly', False)]},),
        'user_id': fields.many2one('res.users', 'Officer', readonly=True, help="The status of the pawn ticket", select=True, track_visibility='onchange'),
        'notes': fields.text('Terms and Conditions'),
        #'picking_ids': fields.one2many('stock.picking', 'pawn_id', 'Picking List', readonly=True, help="This is the list of pickings that have been generated for this pawn ticket."),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Estimated Amount',
            store={
                'pawn.order.line': (_get_order, None, 10),
            }, multi="sums", help="The total amount"),
        'amount_pawned': fields.float('Pawned Amount', readonly=True, states={'draft': [('readonly', False)]}, help="Pawned Amount is the amount that will be used for interest calculation."),
        'date_expired': fields.function(_calculate_pawn_interest, type='date', string='Ticket Expiry Date',
            store={
                'pawn.order': (lambda self, cr, uid, ids, c={}: ids, ['date_order', 'rule_id'], 10),
            }, multi='interest_calc1'),
        'monthly_interest': fields.function(_calculate_pawn_interest, type='float', string='Monthly Interest',
            store={
                'pawn.order': (lambda self, cr, uid, ids, c={}: ids, ['date_order', 'rule_id', 'amount_pawned'], 20),
            }, multi='interest_calc1'),
        'daily_interest': fields.function(_calculate_pawn_interest, type='float', string='Daily Interest', digits=(16,12),
            store={
                'pawn.order': (lambda self, cr, uid, ids, c={}: ids, ['date_order', 'rule_id', 'amount_pawned'], 20),
            }, multi='interest_calc1'),
        'date_due_ticket': fields.date(string='Due Date', readonly=True),
        'date_jor6': fields.date(string='Jor6 Submit Date', readonly=True),
        'date_due': fields.date(string='Grace Period End Date', readonly=True),
        'jor6_submitted': fields.boolean('Jor6 Submitted', readonly=True),
        'ready_to_expire': fields.boolean('Ready to Expire', readonly=True),
        'amount_interest_todate': fields.function(_get_interest_todate, multi='interest_calc2', type='float', string='Interest To-Date'),
        'last_interest_date': fields.function(_get_interest_todate, multi='interest_calc2', type='date', string='Last Interest Date'),
        'is_interest_updated': fields.function(_get_interest_todate, multi='interest_calc2', type='boolean', string='Interested Updated'),
        'create_uid': fields.many2one('res.users', 'Responsible'),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=1, states={'draft': [('readonly', False)]},),
        'journal_id': fields.many2one('account.journal', 'Journal', domain="[('type','=','cash'), ('pawn_journal', '=', True), ('company_id','=',company_id)]", required=True, readonly=True, states={'draft': [('readonly', False)]},),
        'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'item_id': fields.many2one('product.product', 'Pawn Ticket', states={'draft': [('readonly', False)]}, domain=[('type', '=', 'pawn_asset')]),
        'property_account_interest_discount': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Discount Account",
            view_load=True,
            required=True,
            readonly=True),
        'property_account_interest_addition': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Addition Account",
            view_load=True,
            required=True,
            readonly=True),
        'property_journal_accrued_interest': fields.property(
            'account.journal',
            type='many2one',
            relation='account.journal',
            string="Accrued Interest Journal",
            view_load=True,
            required=True,
            readonly=True),
        'property_journal_actual_interest': fields.property(
            'account.journal',
            type='many2one',
            relation='account.journal',
            string="Actual Interest Journal",
            view_load=True,
            required=True,
            readonly=True),
        'move_line_ids': fields.one2many('account.move.line', 'pawn_order_id', 'Move Lines', readonly=True),
        'pawn_move_id': fields.many2one('account.move', 'Pawn Move', readonly=True, ondelete='set null'),
        'redeem_move_id': fields.many2one('account.move', 'Redeem Move', readonly=True, ondelete='set null'),
        'accrued_interest_ids': fields.one2many('pawn.accrued.interest', 'pawn_id', 'Pawn Ticket Interest', readonly=True, help="This shows estimated interest to be move_created for this pawn order."),
        'interest_interval': fields.selection(res_config.INTEREST_INTERVAL, 'Calculation Interval', readonly=True, help="Specify how often interest journal will be created."),
        'actual_interest_ids': fields.one2many('pawn.actual.interest', 'pawn_id', 'Paid Interest', readonly=True, help="This shows interest already paid by customer. This amount will deduct the full amount when redeem."),
        'extended': fields.boolean('Extended', readonly=True),
        'extended_x': fields.function(_get_extended, method=True, string='Extended', type='char'),
        'parent_id': fields.many2one('pawn.order', 'Previous Pawn Ticket', readonly=True),
        'child_id': fields.many2one('pawn.order', 'New Pawn Ticket', readonly=True),
        'previous_pawn_ids': fields.function(_get_previous_pawn_ids, method=True, type='one2many', relation='pawn.order', string='Previous Pawn Tickets'),
        'image': fields.binary("Image",
            help="This field holds the image used as image for the product, limited to 1024x1024px."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized image", type="binary", multi="_get_image",
            store={
                'pawn.order': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized image of the product. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved, "\
                 "only when the image exceeds one of those sizes. Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized image", type="binary", multi="_get_image",
            store={
                'pawn.order': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized image of the product. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
         'amount_net': fields.float('Net Amount', help="For renew case only, amount_net represent amount left over from previous order, pawnshop need to pay (or receive) to customer."),
         'is_lost': fields.boolean('Lost Pawn Ticket'),
         # For search
         'item_desc': fields.related('order_line', 'name', type='char', string='Item Description'),
         'item_categ_id': fields.related('order_line', 'categ_id', type='many2one', relation='product.category', string='Item Category'),
         'property_desc': fields.related('order_line', 'property_ids', 'other_property', type='char', string='Property Description'),
         'status_history_ids': fields.one2many('pawn.status.history', 'order_id', 'Status History', readonly=True),
         'create_date': fields.datetime('Create Date', readonly=True),
         'item_description': fields.function(_get_item_description, type='text', string='Description'),
         'date_final_expired': fields.date('Final Expire Date', readonly=True),
         'fingerprint_pawn': fields.binary('Fingerprint Pawn', readonly=True, help="Customer's fingerprint when pawn the ticket"),
         'fingerprint_pawn_date': fields.datetime('Date of Fingerprint Pawn', readonly=True, help="Date of customer's fingerprint when pawn the ticket"),
         'fingerprint_redeem': fields.binary('Fingerprint Redeem', readonly=True, help="Customer's fingerprint when redeem the ticket"),
         'fingerprint_redeem_date': fields.datetime('Date of Fingerprint Redeem', readonly=True, help="Date of customer's fingerprint when redeem the ticket"),
    }
    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid).company_id.id,
        'date_order': fields.date.context_today,
        'period_id': _get_period,
        'state': 'draft',
        'name': lambda obj, cr, uid, context: '/',
        'pricelist_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').browse(cr, uid, context['partner_id']).property_product_pricelist.id,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'pawn.order', context=c),
        'journal_id': _get_journal,
        'jor6_submitted': False,
        'ready_to_expire': False,
        'date_final_expired': False,
    }
    _sql_constraints = [
        ('name_uniq', 'unique(name, pawn_shop_id)', 'Pawn Ticket Reference must be unique per Pawn Shop!'),
    ]
    _order = 'id desc'

    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def _update_order_pawn_asset(self, cr, uid, order_ids, val, context=None):
        pawn_item_obj = self.pool.get('product.product')
        pawn_item_obj.update_asset_status_by_order(cr, uid, order_ids, val, context=context)
        return True

    def _update_fingerprint(self, cr, uid, order_ids, action_type=None, context=None):
        for order in self.browse(cr, uid, order_ids, context=context):
            if action_type and not order['fingerprint_%s' % action_type]:
                fingerprint = order.partner_id.fingerprint
                fingerprint_date = order.partner_id.fingerprint_date
                # Check customer's fingerprint
                now = fields.datetime.now()
                fingerprint_timeout = int(self.pool.get('ir.config_parameter').get_param(cr, uid, 'pawnshop.customer_fingerprint_timeout', '300'))
                if not fingerprint_date or (fingerprint_date and (datetime.strptime(now, "%Y-%m-%d %H:%M:%S") - datetime.strptime(fingerprint_date, "%Y-%m-%d %H:%M:%S")).total_seconds() > fingerprint_timeout):
                    raise osv.except_osv(_('Error!'), _("The customer's fingerprint was not detected. Kindly submit a new fingerprint."))
                self.write(cr, uid, [order.id], {
                    'fingerprint_%s' % action_type: fingerprint,
                    'fingerprint_%s_date' % action_type: fingerprint_date,
                }, context=context)
        return True

    def _reset_fingerprint(self, cr, uid, order_ids, action_type=None, context=None):
        for order in self.browse(cr, uid, order_ids, context=context):
            if action_type and order['fingerprint_%s' % action_type]:
                self.write(cr, uid, [order.id], {
                    'fingerprint_%s' % action_type: False,
                    'fingerprint_%s_date' % action_type: False,
                }, context=context)
        return True

    # Workflow
    def order_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)
        self._update_order_pawn_asset(cr, uid, ids, {'state': 'draft'}, context=context)
        return True

    def order_pawn(self, cr, uid, ids, context=None):
        # Check order_line
        for order in self.browse(cr, uid, ids, context=context):
            if not len(order.order_line):
                raise osv.except_osv(_('Warning!'),
                                     _('Pawn Ticket do not have any line items. It can not be pawned.'))
            if order.state == 'draft':  # case from draft to paen, create action move line, else nothing.
                self.action_move_create(cr, uid, [order.id], context={'direction': 'pawn'})
            #elif order.state == 'redeem':  # case from redeem, do not update status.
            self.write(cr, uid, [order.id], {'state': 'pawn'}, context=context)
            self._update_order_pawn_asset(cr, uid, [order.id], {'state': 'pawn'}, context=context)
            # Fingerprint
            self._update_fingerprint(cr, uid, [order.id], action_type='pawn', context=context)
            self._reset_fingerprint(cr, uid, [order.id], action_type='redeem', context=context)
        return True

    def order_redeem(self, cr, uid, ids, context=None):
        # Create Move (except expired case)
        for pawn in self.browse(cr, uid, ids, context=context):
            if pawn.state != 'expire':
                self.action_move_create(cr, uid, [pawn.id], context={'direction': 'redeem'})
            self.write(cr, uid, [pawn.id], {'state': 'redeem'}, context=context)
            self._update_order_pawn_asset(cr, uid, [pawn.id], {'state': 'redeem'}, context=context)
            # Fingerprint
            self._update_fingerprint(cr, uid, [pawn.id], action_type='redeem', context=context)
        return True

    def order_expire(self, cr, uid, ids, context=None):
        # Extend the ticket don't change state to expire
        for pawn in self.browse(cr, uid, ids, context=context):
            if pawn.extended:
                raise osv.except_osv(_('Error!'),
                        _('Please unextend the ticket before submit the ticket to expire.'))
        # Reverse Accrued Interest
        self.action_move_reversed_accrued_interest_create(cr, uid, ids, context=context)
        # Inactive any left over accrued interest
        self.update_active_accrued_interest(cr, uid, ids, False, context=context)
        # --
        # Create Move (except extended case)
        for pawn in self.browse(cr, uid, ids, context=context):
            if not pawn.extended:
                self.action_move_create(cr, uid, [pawn.id], context={'direction': 'expire'})
        date_expired = fields.date.context_today(self, cr, uid, context=context)
        self.write(cr, uid, ids, {'state': 'expire', 'date_final_expired': date_expired}, context=context)
        self._update_order_pawn_asset(cr, uid, ids, {'state': 'expire'}, context=context)
        return True

    def action_extend(self, cr, uid, ids, context=None):
        date_extend = fields.date.context_today(self, cr, uid, context=context)
        self.write(cr, uid, ids, {
            'extended': True,
            'date_extend': date_extend,
            'date_extend_last': date_extend,
            'date_unextend_last': False,
        }, context=context)
        items = self.read(cr, uid, ids, ['item_id'], context=context)
        self.pool.get('product.product').action_asset_extend(cr, uid, [i['item_id'][0] for i in items], context=context)
        return True

    def action_unextend(self, cr, uid, ids, context=None):
        date_unextend = fields.date.context_today(self, cr, uid, context=context)
        self.write(cr, uid, ids, {
            'extended': False,
            'date_extend': False,
            'date_unextend_last': date_unextend,
        }, context=context)
        items = self.read(cr, uid, ids, ['item_id'], context=context)
        self.pool.get('product.product').action_asset_unextend(cr, uid, [i['item_id'][0] for i in items], context=context)
        return True

    def order_cancel(self, cr, uid, ids, context=None):
        today = fields.date.context_today(self, cr, uid, context=context)
        # Verify Status to Cancel, 1) Must be in Draft or Pawn status 2) No Interest has been Paid 3) Must be today order
        for order in self.browse(cr, uid, ids, context=context):
            if today != order.date_order:
                raise osv.except_osv(_('Invalid Action!'), _("Only today's pawn ticket can be cancelled"))
            if order.state not in ('draft', 'pawn'):
                raise osv.except_osv(_('Invalid Action!'), _('Only pawn ticket in "Draft" or "Pawned" state can be cancelled'))
            if order.actual_interest_ids:
                raise osv.except_osv(_('Invalid Action!'), _('Only pawn ticket without interest paid, can be cancelled'))
            # Delete all pawn_move_id, if any.
            move_obj = self.pool.get('account.move')
            if order.pawn_move_id:
                move_obj.button_cancel(cr, uid, [order.pawn_move_id.id], context=context)
                move_obj.unlink(cr, uid, order.pawn_move_id.id, context=context)
            # Delete accrued interest
            for accrued_interest in order.accrued_interest_ids:
                if accrued_interest.move_id:
                    move_obj.button_cancel(cr, uid, [accrued_interest.move_id.id], context=context)
                    move_obj.unlink(cr, uid, [accrued_interest.move_id.id], context=context)
            # --
            self.write(cr, uid, [order.id], {
                'state': 'cancel',
                'date_due_ticket': False, # Set due date = False
            }, context=context)
            self._update_order_pawn_asset(cr, uid, [order.id], {'state': 'cancel'}, context=context)
            # Fingerprint
            self._reset_fingerprint(cr, uid, [order.id], action_type='pawn', context=context)
            self._reset_fingerprint(cr, uid, [order.id], action_type='redeem', context=context)
        return True

    def action_undo_pay_interest(self, cr, uid, ids, context=None):
        today = fields.date.context_today(self, cr, uid, context=context)
        actual_interest_obj = self.pool.get('pawn.actual.interest')
        move_obj = self.pool.get('account.move')
        # Verify Status to Unpay Interest, 1) Must be in Pawn status 2) Have at least 1 line 3) The deleting line must be of today.
        for order in self.browse(cr, uid, ids, context=context):
            if order.state not in ('pawn'):
                raise osv.except_osv(_('Invalid Action!'), _('Only pawn ticket in "Pawned" state can undo pay interest'))
            if not order.actual_interest_ids:
                raise osv.except_osv(_('Invalid Action!'), _('Only pawn ticket with interest paid, can be unpaid'))
            if today not in [x.interest_date for x in order.actual_interest_ids]:
                raise osv.except_osv(_('Invalid Action!'), _('There are no paid interest of today to undo'))
            # Delete todays' interest
            interest_ids = actual_interest_obj.search(cr, uid, [('pawn_id', '=', order.id), ('interest_date', '=', today)])
            for interest in actual_interest_obj.browse(cr, uid, interest_ids, context=context):
                if interest.move_id:
                    move_obj.button_cancel(cr, uid, [interest.move_id.id], context=context)
                    move_obj.unlink(cr, uid, [interest.move_id.id], context=context)
                actual_interest_obj.unlink(cr, uid, [interest.id], context=context)
            # Delete accrued interest that was previously reversed today
            for accrued_interest in order.accrued_interest_ids:
                if accrued_interest.write_date[:10] == today:
                    if accrued_interest.reverse_move_id:
                        move_obj.button_cancel(cr, uid, [accrued_interest.reverse_move_id.id], context=context)
                        move_obj.unlink(cr, uid, [accrued_interest.reverse_move_id.id], context=context)

    def action_undo_redeem(self, cr, uid, ids, context=None):
        today = fields.date.context_today(self, cr, uid, context=context)
        actual_interest_obj = self.pool.get('pawn.actual.interest')
        move_obj = self.pool.get('account.move')
        # Verify Status to Redeem, 1) Must be in Redeemed status 2) No child 3) Must be today order 4) Must not be Extended
        for order in self.browse(cr, uid, ids, context=context):
            if today != order.date_redeem:
                raise osv.except_osv(_('Invalid Action!'), _("Only pawn ticket redeemed today can be can be undo"))
            if order.state not in ('redeem'):
                raise osv.except_osv(_('Invalid Action!'), _('Only pawn ticket in "Redeemed" state can be undo'))
            if order.child_id:
                raise osv.except_osv(_('Invalid Action!'), _('Only pawn ticket without child can be undo'))
            # Delete all redeem_move_id, if any.
            if order.redeem_move_id:
                move_obj.button_cancel(cr, uid, [order.redeem_move_id.id], context=context)
                move_obj.unlink(cr, uid, order.redeem_move_id.id, context=context)
            # Delete todays' interest
            interest_ids = actual_interest_obj.search(cr, uid, [('pawn_id', '=', order.id), ('interest_date', '=', today)])
            for interest in actual_interest_obj.browse(cr, uid, interest_ids, context=context):
                if interest.move_id:
                    move_obj.button_cancel(cr, uid, [interest.move_id.id], context=context)
                    move_obj.unlink(cr, uid, [interest.move_id.id], context=context)
                actual_interest_obj.unlink(cr, uid, [interest.id], context=context)
            # Activate Accrued Interest that has not been posted yet.
            self.update_active_accrued_interest(cr, uid, [order.id], True, context=context)
            # Delete accrued interest that was previously reversed today
            for accrued_interest in order.accrued_interest_ids:
                if accrued_interest.write_date[:10] == today:
                    if accrued_interest.reverse_move_id:
                        move_obj.button_cancel(cr, uid, [accrued_interest.reverse_move_id.id], context=context)
                        move_obj.unlink(cr, uid, [accrued_interest.reverse_move_id.id], context=context)
            # --
            wf_service = netsvc.LocalService("workflow")  # Trigger back to Pawn stated
            # if order.extended: # case from expired
            #     self._update_order_pawn_asset(cr, uid, [order.id], {'state': 'expire'}, context=context)
            #     wf_service.trg_validate(uid, 'pawn.order', order.id, 'order_redeem_expire', cr)
            # else: # normal case
            #     self._update_order_pawn_asset(cr, uid, [order.id], {'state': 'pawn'}, context=context)
            #     wf_service.trg_validate(uid, 'pawn.order', order.id, 'order_redeem_pawn', cr)
            # Pod: all case change state to pawn
            self._update_order_pawn_asset(cr, uid, [order.id], {'state': 'pawn'}, context=context)
            wf_service.trg_validate(uid, 'pawn.order', order.id, 'order_redeem_pawn', cr)
            self.write(cr, uid, [order.id], {'date_redeem': False}, context=context)
        return True

    def action_cancel_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'draft'})
        wf_service = netsvc.LocalService("workflow")
        for pawn_id in ids:
            wf_service.trg_delete(uid, 'pawn.order', pawn_id, cr)
            wf_service.trg_create(uid, 'pawn.order', pawn_id, cr)
        return True

    # General
    def _prepare_asset(self, order):
        return {
            'name': order.name,
            'order_id': order.id,
            'type': 'pawn_asset',
#             'list_price': order.amount_pawned,
#             'standard_price': order.amount_total,
            'product_qty': 1.0,
            'image': order.image
        }

    def _prepare_item(self, parent, name, line, context=None):
        item_dict = {
            'name': name,
            'type': 'consu',
            'parent_id': parent.id,
            'order_id': parent.order_id and parent.order_id.id or False,
            'description': line.name,
            'categ_id': line.categ_id.id,
            'product_qty': line.product_qty,
            'product_uom': line.product_uom.id,
            'order_line_id': line.id,
#             'list_price': False,
#             'standard_price': line.price_unit,
            'image': line.image
        }
        return item_dict

    def _prepare_item_line(self, parent, item_id, line, context=None):
        print('>>>>>>>>>>>', line.id)
        item_line_dict = {
            'parent_id': parent.id,
            'item_id': item_id,
            'product_qty': line.product_qty,
            'pawn_line_id': line.id,
        }
        print('======', item_line_dict)
        return item_line_dict

    def _create_pawn_asset_item(self, cr, uid, asset_id, order, context=None):
        item_obj = self.pool.get('product.product')
        line_obj = self.pool.get('product.product.line')
        asset = item_obj.browse(cr, uid, asset_id, context=context)
        asset_name = asset.name
        i = 1
        for line in order.order_line:
            if i > MAX_LINE:
                raise osv.except_osv(_('Exceed Max Lines!'), _('Only %s lines are allowed') % (MAX_LINE))
            # Create each line as new item
            new_item_name = asset_name + '-' + chr(ord(str(i)) + 16)  # i.e., PW001-A
            item_dict = self._prepare_item(asset, new_item_name, line, context=context)
            item_id = item_obj.create(cr, uid, item_dict, context=context)
            # Link it to pawn asset
            item_line_dict = self._prepare_item_line(asset, item_id, line, context=context)
            line_obj.create(cr, uid, item_line_dict, context=context)
            i += 1
        return asset_id

    def _update_pawn_asset(self, cr, uid, asset_id, order, vals, context=None):
        item_obj = self.pool.get('product.product')
        line_obj = self.pool.get('product.product.line')
        if vals.get('order_line', False) or vals.get('name', False):
            # Update Ticket's estimated price.
            name = vals.get('name', False) or item_obj.browse(cr, uid, asset_id, context=context).name
            self.pool.get('product.product').write(cr, uid, [asset_id], {'name': name,
                                                                         'standard_price': order.amount_total})
            # Given item_id (asset), search all item lines to unlink them.
            item_line_ids = line_obj.search(cr, uid, [('parent_id', '=', order.item_id.id)])
            line_obj.unlink(cr, uid, item_line_ids)
            # Delete all pawn asset item, as we will re create it
            item_ids = item_obj.search(cr, uid, [('parent_id', '=', order.item_id.id)])
            item_obj.unlink(cr, uid, item_ids)
            # Use line from order to create pawn items that link to pawn asset
            asset_id = self._create_pawn_asset_item(cr, uid, asset_id, order, context=context)
#         if vals.get('amount_pawned', False):
#             item_obj.write(cr, uid, [asset_id], {'list_price': vals.get('amount_pawned')})
        elif vals.get('redeem_move_id', False):
            pawn_line_id_none = line_obj.search(cr, uid, [
                ('parent_id', '=', order.item_id.id),
                ('pawn_line_id', '=', None),
            ])
            # actually pawn_line_id was fill when create but this case for old pawn order.
            if pawn_line_id_none:
                item_line_ids = line_obj.search(cr, uid, [
                    ('parent_id', '=', order.item_id.id),
                ])
                line_obj.unlink(cr, uid, item_line_ids)
                item_ids = item_obj.search(cr, uid, [(
                    'parent_id', '=', order.item_id.id)
                ])
                item_obj.unlink(cr, uid, item_ids)
                asset_id = self._create_pawn_asset_item(
                    cr, uid, asset_id, order, context=context
                )
        if vals.get('image', False):
            item_obj.write(cr, uid, [asset_id], {'image': vals.get('image')})
        return asset_id

    def _create_pawn_asset(self, cr, uid, order, context=None):
        # Create new pawn asset.
        item_obj = self.pool.get('product.product')
        asset_dict = self._prepare_asset(order)
        asset_id = item_obj.create(cr, uid, asset_dict, context=context)
        # Use line from order to create pawn items that link to pawn asset
        asset_id = self._create_pawn_asset_item(cr, uid, asset_id, order, context=context)
        return asset_id

    def _get_next_pawn_name(self, cr, uid, period_id, pawn_shop_id, context=None):
        period = self.pool.get('account.period').browse(cr, uid, period_id, context=context)
        year_period_ids = [x.id for x in period.fiscalyear_id.period_ids]
        # Search for latest Book and Number of this period
        cr.execute('select coalesce(max(book), 0) from pawn_order where period_id in %s and pawn_shop_id = %s', (tuple(year_period_ids), pawn_shop_id))
        #x = cr.fetchone()
        book = cr.fetchone()[0] or 1
        cr.execute('select coalesce(max(number), 0) from pawn_order where period_id in %s and pawn_shop_id = %s and book = %s', (tuple(year_period_ids), pawn_shop_id, book))
        number = cr.fetchone()[0] or 0
        shop_code = self.pool.get('pawn.shop').browse(cr, uid, pawn_shop_id).code or '--'
        if number >= NUMBER_PER_BOOK:
            book += 1
            number = 1
        else:
            number += 1
        next_name = shop_code + period.fiscalyear_id.code + str(book).zfill(3) + str(number).zfill(3)
        return next_name, book, number

    def create(self, cr, uid, vals, context=None):
        # Update buddha year
        if "buddha_year_temp" in vals:
            vals["buddha_year"] = vals["buddha_year_temp"]
        # --
        if vals.get('internal_number', '/') == '/':
            vals['internal_number'] = self.pool.get('ir.sequence').get(cr, uid, 'pawn.order') or '/'
        name, book, number = self._get_next_pawn_name(cr, uid, vals.get('period_id', False), vals.get('pawn_shop_id', False), context=context)
        vals.update({'name': name, 'book': book, 'number': number})
        pawn_id = super(pawn_order, self).create(cr, uid, vals, context=context)
        pawn = self.browse(cr, uid, pawn_id, context=context)
        if not vals.get('amount_pawned', False):
            self.write(cr, uid, [pawn_id], {'amount_pawned': pawn.amount_total})
        else:
            self.write(cr, uid, [pawn_id], {'amount_pawned': vals.get('amount_pawned')})
        return pawn_id

    def _calculate_interest_date(self, cr, uid, interval, start_date, end_date, context=None):
        dates = []
        if interval == 'month_end':
            next_date = datetime.strptime(start_date[:10], '%Y-%m-%d')
            last_date = datetime.strptime(end_date[:10], '%Y-%m-%d') - relativedelta(days=1)
            while next_date < last_date:
                next_date = last_day_of_month(next_date)
                if next_date < last_date:
                    dates.append(next_date)
                next_date += relativedelta(days=1)
            dates.append(last_date)
        return dates

    def _calculate_interest_table(self, cr, uid, pawn_id, context=None):
        if not pawn_id:
            return False
        accrued_interest_table = []
        pawn = self.browse(cr, uid, pawn_id, context=context)
        dates = context.get('date_due', False) \
                    and self._calculate_interest_date(cr, uid, pawn.interest_interval, pawn.date_expired, pawn.date_due, context=context) \
                    or self._calculate_interest_date(cr, uid, pawn.interest_interval, pawn.date_order, pawn.date_expired, context=context)
        base_date = context.get('date_due', False) \
                    and datetime.strptime(pawn.date_expired[:10], '%Y-%m-%d') - relativedelta(days=1) \
                    or datetime.strptime(pawn.date_order[:10], '%Y-%m-%d') - relativedelta(days=1)
        for date in dates:
            num_days = (date - base_date).days
            interest_amount = num_days * pawn.daily_interest
            rec = (0, 0, {'pawn_id': pawn_id, 'interest_date': date, 'num_days': num_days, 'interest_amount': interest_amount})
            accrued_interest_table.append(rec)
            base_date = date
        return accrued_interest_table

    def register_interest_paid(self, cr, uid, pawn_id, date, discount, addition, interest_amount, context=None):
        if not pawn_id:
            return False
        if not discount and not addition and not interest_amount:
            return False
        actual_interest_table = []
        pawn = self.browse(cr, uid, pawn_id, context=context)
        base_date = datetime.strptime(pawn.date_order[:10], '%Y-%m-%d')
        date = datetime.strptime(date, '%Y-%m-%d')
        num_days = (date - base_date).days
        rec = (0, 0, {'pawn_id': pawn_id, 'interest_date': date,
                      'num_days': num_days, 'discount': discount,
                      'addition': addition, 'interest_amount': interest_amount})
        actual_interest_table.append(rec)
        self.write(cr, uid, [pawn.id], {'actual_interest_ids': actual_interest_table})
        return True

    def update_active_accrued_interest(self, cr, uid, ids, active, context=None):
        if not ids:
            return False
        for pawn in self.browse(cr, uid, ids, context=context):
            if pawn:
                query = False
                if active:
                    query = 'update pawn_accrued_interest set active = %s where pawn_id = %s'
                else:
                    query = 'update pawn_accrued_interest set active = %s where pawn_id = %s and move_id is null'
                cr.execute(query, (active, pawn.id))
        return True

    def write(self, cr, uid, ids, vals, context=None):
        if context == None:
            context = {}
        # Update buddha year
        if "buddha_year_temp" in vals:
            vals["buddha_year"] = vals["buddha_year_temp"]
        # Update Number
        for pawn in self.browse(cr, uid, ids, context=context):
            period_id = vals.get('period_id', False)
            pawn_shop_id = vals.get('pawn_shop_id', False)
            if period_id or pawn_shop_id: # Re assign number, if period or shop is changed
                period_id = period_id or pawn.period_id.id
                pawn_shop_id = pawn_shop_id or pawn.pawn_shop_id.id
                name, book, number = self._get_next_pawn_name(cr, uid, period_id, pawn_shop_id, context=context)
                self.write(cr, uid, [pawn.id], {'name': name, 'book': book, 'number': number})
                vals.update({'name': name}) # To update pawn Ticket
            # For renew pawn oder only, if amount_pawned is changed, also update the amount_net
            if vals.get('amount_pawned', False) and pawn.parent_id:
                diff = vals.get('amount_pawned', False) - pawn.amount_pawned
                if diff:
                    vals.update({'amount_net': pawn.amount_net + diff})
        # Update Super
        res = super(pawn_order, self).write(cr, uid, ids, vals, context=context)
        # Update Pawn Ticket
        for pawn in self.browse(cr, uid, ids, context=context):
            if pawn.item_id:  # Update case
                self._update_pawn_asset(cr, uid, pawn.item_id.id, pawn, vals)
            else:  # Create case, no item_id yet
                item_id = self._create_pawn_asset(cr, uid, pawn)
                super(pawn_order, self).write(cr, uid, [pawn.id], {'item_id': item_id}, context=context)
        # Update pawn amount if total is updated
        if [val for val in vals.keys() if val in ['order_line']]:
            for pawn in self.browse(cr, uid, ids, context=context):
                if not vals.get('amount_pawned', False):
                    self.write(cr, uid, [pawn.id], {'amount_pawned': pawn.amount_total})
        # Interest table, if update in the following 4 fields
        if [val for val in vals.keys() if val in ['amount_pawned', 'rule_id', 'date_order']]:
            for pawn in self.browse(cr, uid, ids, context=context):
                pawn_interest = self.pool.get('pawn.accrued.interest')
                pawn_interest.unlink(cr, uid, pawn_interest.search(cr, uid, [('pawn_id', '=', pawn.id)]))
                interest_table = self._calculate_interest_table(cr, uid, pawn.id, context=context)
                self.write(cr, uid, [pawn.id], {'accrued_interest_ids': interest_table})
        # Adding records in Interest table, if date_due is updated
        if [val for val in vals.keys() if val in ['date_due']]:
            for pawn in self.browse(cr, uid, ids, context=context):
                pawn_interest = self.pool.get('pawn.accrued.interest')
                context.update({'date_due': vals.get('date_due')})
                interest_table = self._calculate_interest_table(cr, uid, pawn.id, context=context)
                self.write(cr, uid, [pawn.id], {'accrued_interest_ids': interest_table})
        # End, update state history
        if vals.get('state', False):
            ctx = dict(account_period_prefer_normal=True)
            periods = self.pool.get('account.period').find(cr, uid, context=ctx)
            for pawn in self.browse(cr, uid, ids, context=context):
                status_history = {'order_id': pawn.id,
                                  'state': vals.get('state'),
                                  'period_id': periods and periods[0] or False}
                self.pool.get('pawn.status.history').create(cr, uid, status_history, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        pawn_orders = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for s in pawn_orders:
            if s['state'] in ['draft', 'cancel']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('Invalid Action!'), _('In order to delete a pawn ticket, you must cancel it first.'))
        wf_service = netsvc.LocalService("workflow")
        for id in unlink_ids:
            wf_service.trg_validate(uid, 'pawn.order', id, 'act_cancel', cr)
        return super(pawn_order, self).unlink(cr, uid, unlink_ids, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'period_id': self._get_period(cr, uid),
            'state': 'draft',
            'date_order': fields.date.context_today(self, cr, uid, context=context),
            'date_redeem': False,
            'date_extend': False,
            'date_extend_last': False,
            'date_unextend_last': False,
            'date_jor6': False,
            'date_due': False,
            'date_due_ticket': False,
            'jor6_submitted': False,
            'parent_id': False,
            'child_id': False,
            'extended': False,
            'item_id': False,
            'picking_ids': [],
            'partner_ref': False,
            'pawn_move_id': False,
            'move_line_ids': [],
            'accrued_interest_ids': [],
            'actual_interest_ids': [],
            #'name': self.pool.get('ir.sequence').get(cr, uid, 'pawn.order'),
            'amount_net': False,
            'is_lost': False,
            'notes': False,
            'status_history_ids': [],
            'ready_to_expire': False,
            'date_final_expired': False,
        })
        pawn_id = super(pawn_order, self).copy(cr, uid, id, default, context)
        # Fingerprint
        self._reset_fingerprint(cr, uid, [pawn_id], action_type='pawn', context=context)
        self._reset_fingerprint(cr, uid, [pawn_id], action_type='redeem', context=context)
        return pawn_id

    # Onchange
    def onchange_pricelist(self, cr, uid, ids, pricelist_id, context=None):
        if not pricelist_id:
            return {}
        return {'value': {'currency_id': self.pool.get('product.pricelist').browse(cr, uid, pricelist_id, context=context).currency_id.id}}

    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        if not company_id:
            return {}
        shop_ids = self.pool.get('pawn.shop').search(cr, uid, [('company_id', '=', company_id), ('user_ids', 'in', uid)], context=context)
        shop_id = shop_ids and shop_ids[0] or False
        return shop_ids and {'value': {'pawn_shop_id': shop_id}}

    def onchange_partner_id(self, cr, uid, ids, partner_id):
        partner_obj = self.pool.get('res.partner')
        if not partner_id:
            return False
        partner = partner_obj.browse(cr, uid, partner_id)
        return {'value': {
            'pricelist_id': partner.property_product_pricelist.id,
            }}

    def onchange_date(self, cr, uid, ids, date_order, currency_id, company_id, context=None):
        if context is None:
            context = {}
        res = {'value': {}}
        #set the period of the voucher
        period_pool = self.pool.get('account.period')
        ctx = context.copy()
        ctx.update({'company_id': company_id, 'account_period_prefer_normal': True})
        pids = period_pool.find(cr, uid, date_order, context=ctx)
        # Get buddha year from date_order
        buddha_year = False
        if date_order:
            date_order = datetime.strptime(date_order, '%Y-%m-%d')
            buddha_year = str(date_order.year + 543)
        if pids:
            res['value'].update({'period_id': pids[0],
                                 'buddha_year': buddha_year,
                                 'buddha_year_temp': buddha_year})
        return res

    def _get_company_currency(self, cr, uid, pawn_id, context=None):
        return self.pool.get('pawn.order').browse(cr, uid, pawn_id, context).journal_id.company_id.currency_id.id

    def _get_current_currency(self, cr, uid, pawn_id, context=None):
        pawn = self.pool.get('pawn.order').browse(cr, uid, pawn_id, context)
        return pawn.currency_id.id or self._get_company_currency(cr, uid, pawn.id, context)

    def _sel_context(self, cr, uid, voucher_id, context=None):
        company_currency = self._get_company_currency(cr, uid, voucher_id, context)
        current_currency = self._get_current_currency(cr, uid, voucher_id, context)
        if current_currency != company_currency:
            context_multi_currency = context.copy()
            pawn = self.pool.get('pawn.order').browse(cr, uid, voucher_id, context)
            context_multi_currency.update({'date': pawn.date_order})
            return context_multi_currency
        return context

    def account_move_get(self, cr, uid, pawn, journal, account_date, context=None):
        seq_obj = self.pool.get('ir.sequence')
        #set the period of the voucher
        period_pool = self.pool.get('account.period')
        ctx = context.copy()
        ctx.update({'company_id': pawn.company_id.id, 'account_period_prefer_normal': True})
        pids = period_pool.find(cr, uid, account_date, context=ctx)
        period_id = pids and pids[0]
        if journal.sequence_id:
            if not journal.sequence_id.active:
                raise osv.except_osv(_('Configuration Error !'),
                    _('Please activate the sequence of selected journal !'))
            c = dict(context)
            c.update({'fiscalyear_id': self.pool.get('account.period').browse(cr, uid, period_id).fiscalyear_id.id})
            name = seq_obj.next_by_id(cr, uid, journal.sequence_id.id, context=c)
        else:
            raise osv.except_osv(_('Error!'),
                        _('Please define a sequence on the journal.'))
        move = {
            'name': name,
            'journal_id': journal.id,
            'narration': False,
            'date': account_date,
            'ref': pawn.name,
            'period_id': period_id,
        }
        return move

    def move_line_get(self, cr, uid, pawn_id, direction, context=None):
        #res = []
        if context is None:
            context = {}
        pawn = self.browse(cr, uid, pawn_id, context=context)
        mres = self.move_line_get_item(cr, uid, pawn, direction, context)
        return mres and [mres] or []

    def move_line_get_item(self, cr, uid, pawn, direction, context=None):
        # Search for item
        if not pawn.item_id:
            raise osv.except_osv(_('Error!'), _('No pawn ticket associated with pawn ticket %s') % (pawn.name))
        item = pawn.item_id
        acc = item.property_account_pawn_asset
        sign = direction == 'pawn' and 1 or -1
        if not acc:
            raise osv.except_osv(_('Error!'), _('No pawn ticket account found for the item %s') % (item.name))
        return {
            'pawn_order_id': pawn.id,
            'pawn_shop_id': pawn.pawn_shop_id.id,
            'profit_center': pawn.journal_id.profit_center,
            'type': 'src',
            'name': pawn.name.split('\n')[0][:64],
            'price_unit': sign * pawn.amount_pawned,
            'quantity': 1.0,
            'price': sign * pawn.amount_pawned,
            'account_id': acc.id,
            'product_id': item.id,
            'uos_id': item.uom_id.id,
            'account_analytic_id': False,
        }

    def move_accrued_interest_get(self, cr, uid, pawn_id, amount_interest, context=None):
        res = []
        if context is None:
            context = {}
        pawn = self.browse(cr, uid, pawn_id, context=context)
        # Credit Interest Income
        if amount_interest:
            account = pawn.property_journal_accrued_interest.default_credit_account_id
            mres = self.move_interest_get_item(cr, uid, pawn, 'dest', 'Accrued Interest', amount_interest, account, context=context)
            res.append(mres)
            # Debit Accrued Interest Income
            account = pawn.property_journal_accrued_interest.default_debit_account_id
            mres = self.move_interest_get_item(cr, uid, pawn, 'src', 'Accrued Interest', amount_interest, account, context=context)
            res.append(mres)
        return res

    def move_actual_interest_get(self, cr, uid, pawn_id, discount, addition, amount_interest, context=None):
        res = []
        if context is None:
            context = {}
        pawn = self.browse(cr, uid, pawn_id, context=context)
        # Credit Interest Income
        interest_income = amount_interest + discount - addition
        if interest_income:
            account = pawn.property_journal_actual_interest.default_credit_account_id
            mres = self.move_interest_get_item(cr, uid, pawn, 'dest', 'Actual Interest 1', interest_income, account, context=context)
            res.append(mres)
        # Debit Interest Discount
        if discount:
            account = pawn.property_account_interest_discount
            mres = self.move_interest_get_item(cr, uid, pawn, 'src', 'Actual Interest 2', discount, account, context=context)
            res.append(mres)
        # Credit Interest Addition
        if addition:
            account = pawn.property_account_interest_addition
            mres = self.move_interest_get_item(cr, uid, pawn, 'dest', 'Actual Interest 3', addition, account, context=context)
            res.append(mres)
        # Debit Cash
        if amount_interest:
            account = pawn.property_journal_actual_interest.default_debit_account_id
            mres = self.move_interest_get_item(cr, uid, pawn, 'src', 'Actual Interest 4', amount_interest, account, context=context)
            res.append(mres)
        return res

    def move_interest_get_item(self, cr, uid, pawn, type, name, amount, account, context=None):
        if not account:
            raise osv.except_osv(_('Accounting Error!'), _('Accounting is not set for %s') % (name,))
        return {
            'pawn_order_id': pawn.id,
            'pawn_shop_id': pawn.pawn_shop_id.id,
            'profit_center': pawn.journal_id.profit_center,
            'type': type,
            'name': name,
            'price_unit': amount,
            'quantity': 1,
            'price': type == 'src' and amount or -amount,
            'account_id': account.id,
            'product_id': False,
            'uos_id': False,
            'account_analytic_id': False,
        }

    def line_get_convert(self, cr, uid, x, part, date, context=None):
        return {
            'pawn_order_id': x.get('pawn_order_id', False),
            'pawn_shop_id': x.get('pawn_shop_id', False),
            'profit_center': x.get('profit_center', False),
            'date_maturity': x.get('date_maturity', False),
            'partner_id': part.id,
            'name': x['name'][:64],
            'date': date,
            'debit': x['price'] > 0 and x['price'],
            'credit': x['price'] < 0 and -x['price'],
            'account_id': x['account_id'],
            'analytic_lines': x.get('analytic_lines', False),
            'amount_currency': x['price'] > 0 and abs(x.get('amount_currency', False)) or -abs(x.get('amount_currency', False)),
            'currency_id': x.get('currency_id', False),
            'tax_code_id': x.get('tax_code_id', False),
            'tax_amount': x.get('tax_amount', False),
            'ref': x.get('ref', False),
            'quantity': x.get('quantity', 1.00),
            'product_id': x.get('product_id', False),
            'product_uom_id': x.get('uos_id', False),
            'analytic_account_id': x.get('account_analytic_id', False),
        }

    def compute_pawnline_totals(self, cr, uid, pawn, company_currency, ref, account_move_lines, context=None):
        cur_obj = self.pool.get('res.currency')
        if context is None:
            context = {}
        context.update({'date': pawn.date_order or fields.date.context_today(self, cr, uid, context=context)})
        total = 0.0
        total_currency = 0.0
        for i in account_move_lines:
            if pawn.currency_id.id != company_currency:
                i['currency_id'] = pawn.currency_id.id
                i['amount_currency'] = i['price']
                i['price'] = cur_obj.compute(cr, uid, pawn.currency_id.id,
                        company_currency, i['price'],
                        context=context)
            else:
                i['amount_currency'] = False
                i['currency_id'] = False
            total -= i['price']
            total_currency -= i['amount_currency'] or i['price']
        return total, total_currency, account_move_lines

    def action_move_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        direction = context.get('direction', False) or 'pawn'
        move_pool = self.pool.get('account.move')
        for pawn in self.browse(cr, uid, ids, context=context):
            # Pawn, use Date Order, Redeem and Expire use today
            date = direction == 'pawn' and pawn.date_order or fields.date.context_today(self, cr, uid, context=context)
            company_currency = self._get_company_currency(cr, uid, pawn.id, context)
            diff_currency_p = pawn.currency_id.id != company_currency
            # we select the context to use accordingly if it's a multicurrency case or not
            context = self._sel_context(cr, uid, pawn.id, context)
            # Create the account move record.
            move_id = move_pool.create(cr, uid, self.account_move_get(cr, uid, pawn, pawn.journal_id, date, context=context), context=context)
            # one account.move.line per pawn line
            pml = self.move_line_get(cr, uid, pawn.id, direction, context=context)
            #create one more move line, a counterline for the total on payable account
            total, total_currency, pml = self.compute_pawnline_totals(cr, uid, pawn, company_currency, pawn.name, pml, context=context)

            acc = False
            sign = direction == 'pawn' and 1 or -1  # (redeem, expire) = -1
            date = False
            if direction == 'pawn':
                acc = pawn.journal_id.default_credit_account_id.id
                self.write(cr, uid, [pawn.id], {'pawn_move_id': move_id})
            else: # Redeem / Expire
                if direction == 'redeem':
                    acc = pawn.journal_id.default_debit_account_id.id
                else:  # expire
                    acc = pawn.item_id.property_account_expire_asset.id
                self.write(cr, uid, [pawn.id], {'redeem_move_id': move_id})
            pml.append({
                'pawn_order_id': pawn.id,
                'pawn_shop_id': pawn.pawn_shop_id.id,
                'profit_center': pawn.journal_id.profit_center,
                'type': 'dest',
                'name': '/',
                'price': total,
                'account_id': acc,
                'date_maturity': False,
                'amount_currency': diff_currency_p and sign * total_currency or False,
                'currency_id': diff_currency_p and pawn.currency_id.id or False,
                'ref': pawn.name
            })
            #convert eml into an osv-valid format
            lines = map(lambda x: (0, 0, self.line_get_convert(cr, uid, x, pawn.partner_id, date, context=context)), pml)
            journal_id = move_pool.browse(cr, uid, move_id, context).journal_id
            # post the journal entry if 'Skip 'Draft' State for Manual Entries' is checked
            if journal_id.entry_posted:
                move_pool.button_validate(cr, uid, [move_id], context)
            move_pool.write(cr, uid, [move_id], {'line_id': lines}, context=context)
        return True

    def action_move_accrued_interest_create(self, cr, uid, ids, amount_interest, account_date, context=None):
        """ Create 1 journal """
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        for pawn in self.browse(cr, uid, ids, context=context):
            if not amount_interest:
                return False
            context = self._sel_context(cr, uid, pawn.id, context)
            # Create the account move record.
            journal = pawn.property_journal_accrued_interest
            move_id = move_pool.create(cr, uid, self.account_move_get(cr, uid, pawn, journal, account_date, context=context), context=context)
            # Debit and Credit for interest
            pml = self.move_accrued_interest_get(cr, uid, pawn.id, amount_interest, context=context)
            #convert eml into an osv-valid format
            lines = map(lambda x: (0, 0, self.line_get_convert(cr, uid, x, pawn.partner_id, account_date, context=context)), pml)
            move_pool.write(cr, uid, [move_id], {'line_id': lines}, context=context)
        return move_id

    def action_move_actual_interest_create(self, cr, uid, ids, discount, addition, amount_interest, account_date, context=None):
        """ Create 1 journal """
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        for pawn in self.browse(cr, uid, ids, context=context):
            if not amount_interest:
                return False
            context = self._sel_context(cr, uid, pawn.id, context)
            # Create the account move record.
            journal = pawn.property_journal_actual_interest
            move_id = move_pool.create(cr, uid, self.account_move_get(cr, uid, pawn, journal, account_date, context=context), context=context)
            # Debit and Credit for interest & Reverse the Accrued Interest up to today
            pml = self.move_actual_interest_get(cr, uid, pawn.id, discount, addition, amount_interest, context=context)
            #convert eml into an osv-valid format
            lines = map(lambda x: (0, 0, self.line_get_convert(cr, uid, x, pawn.partner_id, account_date, context=context)), pml)

            move_pool.write(cr, uid, [move_id], {'line_id': lines}, context=context)
        return move_id

    def action_move_reversed_accrued_interest_create(self, cr, uid, ids, context=None):
        """ Create multiple reversed journal from accured interest journal """
        if context is None:
            context = {}
        move_obj = self.pool.get('account.move')
        accrued_obj = self.pool.get('pawn.accrued.interest')
        for pawn in self.browse(cr, uid, ids, context=context):
            # Get Accrued Interest Table
            search_domain = [('pawn_id', '=', pawn.id), ('move_id', '!=', False), ('reverse_move_id', '=', False)]
            accrued_ids = accrued_obj.search(cr, uid, search_domain, context=context)
            reverse_move_ids = []
            accrued_map = []
            for accrued in accrued_obj.browse(cr, uid, accrued_ids, context=context):
                # Copy new move and assien pawn.name
                default = {'period_id': self._get_period(cr, uid, context=context),
                           'date': fields.date.context_today(self, cr, uid, context=context)}
                reverse_move_id = move_obj.copy(cr, uid, accrued.move_id.id, default, context=context)
                move_obj.write(cr, uid, [reverse_move_id], {'ref': pawn.name})
                reverse_move_ids.append(int(reverse_move_id))
                accrued_map.append((accrued.id, int(reverse_move_id)))
            # Reverse Cr/Dr
            if reverse_move_ids:
                cr.execute("""update account_move_line
                            set debit = (case when credit is null then debit else credit end),
                            credit = (case when debit is null then credit else debit end),
                            name = 'Reversed Accrued Interest',
                            pawn_order_id = %s
                            where move_id in %s """, (pawn.id, tuple(reverse_move_ids)))
            # Register it to table
            for reverse_move in accrued_map:
                accrued_obj.write(cr, uid, [reverse_move[0]], {'reverse_move_id': reverse_move[1]}, context=context)
        return accrued_map

    def action_move_expired_redeem_create(self, cr, uid, id, redeem_amount, context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        pawn = self.browse(cr, uid, id, context=context)
        date = fields.date.context_today(self, cr, uid, context=context)
        # we select the context to use accordingly if it's a multicurrency case or not
        context = self._sel_context(cr, uid, pawn.id, context)
        # Create the account move record.
        move_id = move_pool.create(cr, uid, self.account_move_get(cr, uid, pawn, pawn.journal_id, date, context=context), context=context)
        self.write(cr, uid, [pawn.id], {'redeem_move_id': move_id})
        # Credit Revenue from expired ticket
        sign = -1
        pml = [{
            'pawn_order_id': pawn.id,
            'pawn_shop_id': pawn.pawn_shop_id.id,
            'profit_center': pawn.journal_id.profit_center,
            'type': 'src',
            'name': pawn.name.split('\n')[0][:64],
            'price_unit': sign * redeem_amount,
            'quantity': 1.0,
            'price': sign * redeem_amount,
            'account_id': pawn.item_id.property_account_revenue_reposessed_asset.id,
            'product_id': pawn.item_id.id,
            'uos_id': pawn.item_id.uom_id.id,
            'account_analytic_id': False,
        }]
        # Debit Cash
        sign = 1
        pml.append({
            'pawn_order_id': pawn.id,
            'pawn_shop_id': pawn.pawn_shop_id.id,
            'profit_center': pawn.journal_id.profit_center,
            'type': 'dest',
            'name': '/',
            'price': sign * redeem_amount,
            'account_id': pawn.journal_id.default_debit_account_id.id,
            'date_maturity': False,
            'ref': pawn.name
        })

        # Debit Cost of Reposessed Ticket
        sign = 1
        pml.append({
            'pawn_order_id': pawn.id,
            'pawn_shop_id': pawn.pawn_shop_id.id,
            'profit_center': pawn.journal_id.profit_center,
            'type': 'src',
            'name': pawn.name.split('\n')[0][:64],
            'price_unit': sign * pawn.amount_pawned,
            'quantity': 1.0,
            'price': sign * pawn.amount_pawned,
            'account_id': pawn.item_id.property_account_cost_reposessed_asset.id,
            'product_id': pawn.item_id.id,
            'uos_id': pawn.item_id.uom_id.id,
            'account_analytic_id': False,
        })
        # Credit Reposessed Ticket
        sign = -1
        pml.append({
            'pawn_order_id': pawn.id,
            'pawn_shop_id': pawn.pawn_shop_id.id,
            'profit_center': pawn.journal_id.profit_center,
            'type': 'dest',
            'name': '/',
            'price': sign * pawn.amount_pawned,
            'account_id': pawn.item_id.property_account_expire_asset.id,
            'date_maturity': False,
            'ref': pawn.name
        })

        #convert eml into an osv-valid format
        lines = map(lambda x: (0, 0, self.line_get_convert(cr, uid, x, pawn.partner_id, date, context=context)), pml)
        journal_id = move_pool.browse(cr, uid, move_id, context).journal_id
        # post the journal entry if 'Skip 'Draft' State for Manual Entries' is checked
        if journal_id.entry_posted:
            move_pool.button_validate(cr, uid, [move_id], context)
        move_pool.write(cr, uid, [move_id], {'line_id': lines}, context=context)
        return True

    def _calculate_months(self, cr, uid, pawn_date, redeem_date, context=None):
        pawn_date = datetime.strptime(pawn_date[:10], '%Y-%m-%d')
        redeem_date = datetime.strptime(redeem_date[:10], '%Y-%m-%d')
        delta = relativedelta(redeem_date, pawn_date)
        months = float(delta.years * 12) + float(delta.months) + (delta.days <= 15 and 0.5 or 1.0)
        return months

    def calculate_interest_remain(self, cr, uid, pawn_id, date, context=None):
        interest_todate = self.calculate_interest_todate(cr, uid, pawn_id, date, context=None)
        interest_paid = self.calculate_interest_paid(cr, uid, pawn_id, context=None)
        return interest_todate - interest_paid

    def calculate_interest_todate(self, cr, uid, pawn_id, date, context=None):
        pawn = self.browse(cr, uid, pawn_id, context=context)
        months = self._calculate_months(cr, uid, pawn.date_order, date, context=context)
        amount_interest = pawn.monthly_interest * months
        return amount_interest

    def calculate_interest_paid(self, cr, uid, pawn_id, context=None):
        pawn = self.browse(cr, uid, pawn_id, context=context)
        amount_interest_paid = 0.0
        for interest_paid in pawn.actual_interest_ids:
            amount_interest_paid += interest_paid.interest_amount + interest_paid.discount - interest_paid.addition
        return amount_interest_paid

    def show_customer_number(self, cr, uid, ids, context=None):
        """This function will call from server action"""
        pawn_orders = self.browse(cr, uid, ids, context=context)
        customer_count = len(list(set(map(lambda l: l.partner_id, pawn_orders))))
        raise osv.except_osv(_('Information'), _('Customer number is %s.') % customer_count)

pawn_order()


class pawn_order_line(osv.osv):

    _name = 'pawn.order.line'
    _description = 'Pawn Ticket Line'

    def _amount_line(self, cr, uid, ids, prop, arg, context=None):
        res = {}
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {
                'price_unit': 0.0,
                'pawn_price_unit': 0.0,
            }
            if not line.product_qty:
                raise osv.except_osv(_('Error!'), _('Quantity can not be zero!'))
            cur = line.order_id.pricelist_id.currency_id
            res[line.id]['price_unit'] = cur_obj.round(cr, uid, cur, line.price_subtotal / line.product_qty)
            pawn_price_unit = line.order_id.amount_total and res[line.id]['price_unit'] * line.order_id.amount_pawned / line.order_id.amount_total or 0.0
            res[line.id]['pawn_price_unit'] = cur_obj.round(cr, uid, cur, pawn_price_unit)
        return res

    def _get_uom_id(self, cr, uid, context=None):
        try:
            proxy = self.pool.get('ir.model.data')
            result = proxy.get_object_reference(cr, uid, 'product', 'product_uom_unit')
            return result[1]
        except Exception, ex:
            return False

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image, avoid_resize_medium=True)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    def _get_order_line(self, cr, uid, ids, context=None):
        line_ids = []
        for pawn in self.browse(cr, uid, ids, context=context):
            line_ids = self.pool.get('pawn.order.line').search(cr, uid, [('order_id', '=', pawn.id)], context=context)
        return line_ids

    _columns = {
        'name': fields.text('Description', required=True),
        'categ_id': fields.many2one('product.category', 'Category', domain=[('type', '=', 'normal')], required=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', domain="[('categ_ids', 'in', categ_id)]", required=True),
        #'price_unit': fields.float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price')),
        'price_unit': fields.function(_amount_line, string='Unit Price', digits_compute=dp.get_precision('Product Price'), store=True, multi="price"),
        'pawn_price_unit': fields.function(_amount_line, string='Unit Price', digits_compute=dp.get_precision('Product Price'),
            store={
                'pawn.order': (_get_order_line, ['amount_pawned'], 10),
            }, multi="price"),
        'price_subtotal': fields.float('Subtotal', required=True, digits_compute=dp.get_precision('Account')),
        #'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute=dp.get_precision('Account')),
        'order_id': fields.many2one('pawn.order', 'Pawn Ticket Reference', select=True, required=True, ondelete='cascade'),
        'company_id': fields.related('order_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'state': fields.related('order_id', 'state', string='State', readonly=True, type="selection", selection=STATE_SELECTION),
        'partner_id': fields.related('order_id', 'partner_id', string='Partner', readonly=True, type="many2one", relation="res.partner", store=True),
        'date_order': fields.related('order_id', 'date_order', string='Pawn Date', readonly=True, type="date"),
        'property_ids': fields.one2many('pawn.order.line.properties', 'order_line_id', 'Pawn Line Properties'),
        'image': fields.binary("Image",
            help="This field holds the image used as image for the product, limited to 1024x1024px."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized image", type="binary", multi="_get_image",
            store={
                'pawn.order.line': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized image of the product. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved, "\
                 "only when the image exceeds one of those sizes. Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized image", type="binary", multi="_get_image",
            store={
                'pawn.order.line': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized image of the product. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
        'is_jewelry': fields.boolean('Carat/Gram'),
        'carat': fields.float('Carat', required=False),
        'gram': fields.float('Gram', required=False),
    }
    _defaults = {
        'product_uom': _get_uom_id,
        'product_qty': lambda *a: 1.0,
    }

    def _check_price_subtotal(self, price_subtotal):
        if not price_subtotal:
            raise osv.except_osv(_('Warning!'),
                _('Line price equal to 0.0 is not allowed!'))

    def create(self, cr, uid, vals, context=None):
        self._check_price_subtotal(vals.get('price_subtotal', False))
        return super(pawn_order_line, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        self._check_price_subtotal(vals.get('price_subtotal', False))
        return super(pawn_order_line, self).write(cr, uid, ids, vals, context=context)

    def onchange_categ_id(self, cr, uid, ids, categ_id, context=None):
        res = {}
        if categ_id:
            category = self.pool.get('product.category').browse(cr, uid, categ_id, context=context)
            res['product_uom'] = category.uom_ids and category.uom_ids[0].id or False
            res['carat'] = False
            res['gram'] = False
            res['is_jewelry'] = category.is_jewelry or False
        return {'value': res}

    def action_update_pawn_line_property(self, cr, uid, property_data, context=None):
        if context == None:
            context = {}
        # Loop through pawn_order_line_properties, delete and recreate
        order_line_id = property_data.order_line_id.id
        # Update image and keep in pawn ticket line, if any,
        self.write(cr, uid, [order_line_id], {'image': property_data.image}, context=context)
        item_obj = self.pool.get('product.product')
        item_ids = item_obj.search(cr, uid, [('order_line_id', '=', order_line_id)], context=context)
        item_obj.write(cr, uid, item_ids, {'image': property_data.image}, context=context)
        # Find all property in this line
        line_properties_obj = self.pool.get('pawn.order.line.properties')
        ids = line_properties_obj.search(cr, uid, [('order_line_id', '=', order_line_id)])
        line_properties_obj.unlink(cr, uid, ids)
        for p in property_data.property_line:
            line_properties_obj.create(cr, uid, {
                                            'order_line_id': order_line_id,
                                            'property_id': p.property_id.id,
                                            'property_line_id': p.property_line_id.id,
                                            'other_property': p.other_property or False,
                                        })
        return True

pawn_order_line()


class pawn_order_line_properties(osv.osv):

    _name = 'pawn.order.line.properties'
    _description = 'Pawn Ticket Line Properties'

    _columns = {
        'order_line_id': fields.many2one('pawn.order.line', 'Pawn Ticket Line', select=True, required=True, ondelete='cascade'),
        'property_id': fields.many2one('item.property', 'Property', required=True, ondelete='cascade'),
        'property_line_id': fields.many2one('item.property.line', 'Value', domain="[('property_id', '=', property_id)]", required=True, ondelete='cascade'),
        'other_property': fields.char('Other', size=128, required=False),
    }

pawn_order_line_properties()


class pawn_accrued_interest(osv.osv):

    _name = 'pawn.accrued.interest'
    _description = 'Accrued Interest'

    _columns = {
        'pawn_id': fields.many2one('pawn.order', 'Pawn Ticket', ondelete='cascade', required=True, readonly=True, select=True),
        'interest_date': fields.date('Date', required=True, readonly=True, select=True, help="Date on which this interest journal will be created"),
        'num_days': fields.integer('Days', readonly=True, required=True),
        'interest_amount': fields.float('Interest Amount', readonly=True, required=True),
        'move_id': fields.many2one('account.move', 'Account Entry', readonly=True, ondelete='set null'),
        'reverse_move_id': fields.many2one('account.move', 'Reveresed Entry', readonly=True, ondelete='set null'),
        'parent_state': fields.related('pawn_id', 'state', type='char', string='State of Pawn Ticket'),
        'active': fields.boolean('Active', help="If not active, journal will not be created"),
        'write_date': fields.datetime('Write Date', readonly=True),
    }
    _defaults = {
        'move_id': False,
        'active': True
    }

    def create_interest_move(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            if not line.move_id:
                pawn_id = line.pawn_id.id
                amount_interest = line.interest_amount or 0.0
                account_date = line.interest_date
                move_id = self.pool.get('pawn.order').action_move_accrued_interest_create(cr, uid, [pawn_id], amount_interest, account_date, context=context)
                self.write(cr, uid, line.id, {'move_id': move_id}, context=context)
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'move_id': False,
        })
        return super(pawn_accrued_interest, self).copy(cr, uid, id, default, context)

pawn_accrued_interest()


class pawn_actual_interest(osv.osv):

    _name = 'pawn.actual.interest'
    _description = 'Actual Interest'

    _columns = {
        'pawn_id': fields.many2one('pawn.order', 'Pawn Ticket', required=True, readonly=True, select=True),
        'interest_date': fields.date('Date', required=True, readonly=True, select=True, help="Date on which this interest journal will be created"),
        'num_days': fields.integer('Days', readonly=True, required=True),
        'discount': fields.float('Discount', readonly=True, required=True),
        'addition': fields.float('Addition', readonly=True, required=True),
        'interest_amount': fields.float('Interest Amount', readonly=True, required=True),
        'move_id': fields.many2one('account.move', 'Account Entry', readonly=True),
        'parent_state': fields.related('pawn_id', 'state', type='char', string='State of Pawn Ticket'),
        'write_date': fields.datetime('Write Date', readonly=True),
    }
    _defaults = {
        'move_id': False
    }

    def create_interest_move(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pawn_obj = self.pool.get('pawn.order')
        for line in self.browse(cr, uid, ids, context=context):
            if not line.move_id:
                pawn_id = line.pawn_id.id
                discount = line.discount or 0.0
                addition = line.addition or 0.0
                amount_interest = line.interest_amount or 0.0
                account_date = line.interest_date
                move_id = pawn_obj.action_move_actual_interest_create(cr, uid, [pawn_id], discount, addition, amount_interest, account_date, context=context)
                self.write(cr, uid, line.id, {'move_id': move_id}, context=context)
        return True

pawn_actual_interest()

class pawn_status_history(osv.osv):

    _name = 'pawn.status.history'
    _description = 'Status History'

    _columns = {
        'order_id': fields.many2one('pawn.order', 'Pawn Ticket', required=True, readonly=True, select=True),
        'write_date': fields.datetime('Write Date', readonly=True),
        'period_id': fields.many2one('account.period', 'Period', readonly=True),
        'write_uid': fields.many2one('res.users', "Modifier", readonly=True),
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True),
    }

pawn_status_history()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
