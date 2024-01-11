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
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
from random import randrange

AVAILABLE_STATE = [('draft', 'Draft'),
                    ('pawn', 'Pawned'),
                    ('redeem', 'Redeemed'),
                    ('expire', 'Expired'),
                    ('cancel', 'Cancelled'),
                    ('for_sale', 'For Sale')]

# This data is in table product_location_status, we just show here for reference.
LOCATION_STATUS = [('asset_incoming', 'Incoming'),
                    ('asset_stock', 'In-Stock'),
                    ('asset_outgoing', 'Outgoing'),
                    ('asset_returned', 'Returned'),
                    ('asset_split', 'Split to Items'),
                    # -------------------------------
                    ('item_with_asset', 'With Ticket'),
                    ('item_for_sale', 'For Sale'),
                    ('item_borrowed', 'Borrowed'),
                    ('item_sold', 'Sold Out')]

ASSET_STATUS_MAPPING = {'pawn': 'asset_incoming',
                        'redeem': 'asset_outgoing',
                        'expire': 'asset_stock',
                        'for_sale': 'asset_split'}

ITEM_STATUS_MAPPING = {'pawn': 'item_with_asset',
                        'redeem': 'item_with_asset',
                        'for_sale': 'item_for_sale'}

# This mapping ensure that, before asset is changing to next status, its original location must be valid.
# Example, to change to Redeem, the original location must be in In Stock
ASSET_STATUS_VS_INIT_LOC = {'redeem': ['asset_stock', 'asset_outgoing'],
                            'expire': ['asset_stock', 'asset_outgoing', 'asset_split'],
                            'for_sale': ['asset_stock']}

class product_template(osv.osv):

    _inherit = 'product.template'

    def _get_product(self, cr, uid, ids, context=None):
        return self.pool.get('product.template').search(cr, uid, [('order_id','in',ids)])

    _columns = {
        # No translation
        'name': fields.char('Name', size=128, required=True, translate=False, select=True),
        'description': fields.text('Description',translate=False),
        'description_purchase': fields.text('Purchase Description',translate=False),
        'description_sale': fields.text('Sale Description',translate=False),
        # --
        'type': fields.selection([('product', 'Stockable Product'),
                                  ('consu', 'Pawn Item'),
                                  ('service', 'Service'),
                                  ('pawn_asset', 'Pawn Ticket')], 'Product Type', required=True, help="Consumable: Will not imply stock management for this product. \nStockable product: Will imply stock management for this product."),
        'pawn_shop_id': fields.related('order_id', 'pawn_shop_id', type='many2one', relation='pawn.shop', string='Shop', store=True, readonly=True),
        'parent_order_id': fields.related('order_id', 'parent_id', type='many2one', relation='pawn.order', string='Previous Pawn Ticket', readonly=True,
                                    store={
                                        'pawn.order': (_get_product, ['parent_id'], 10),
                                    }),
        'order_id': fields.many2one('pawn.order', 'Pawn Ticket', ondelete='cascade'),
        'partner_customer_id': fields.related('order_id','partner_id',type='many2one',relation='res.partner',string='Customer', store=True, readonly=True),
        'journal_id': fields.related('order_id', 'journal_id', type='many2one', relation='account.journal', string='Journal', readonly=True,
                                    store={
                                        'pawn.order': (_get_product, ['journal_id'], 10),
                                    }),
    }

product_template()

class product_product(osv.osv):

    _inherit = 'product.product'

    def _get_item_description(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for item in self.browse(cr, uid, ids, context=context):
            item_description = ''
            try:
                if item.line_ids:
                    for item_line in item.line_ids:
                        jewelry_desc = ''
                        order_line = item_line.item_id.order_line_id
                        if order_line and order_line.is_jewelry:
                            if order_line.carat and order_line.gram:
                                jewelry_desc = ' [' + str(order_line.carat) + ' ' + _('กะรัต') + ', ' + str(order_line.gram) + ' ' + _('กรัม') + ']'
                            elif order_line.carat and not order_line.gram:
                                jewelry_desc = ' [' + str(order_line.carat) + ' ' + _('กะรัต') + ']'
                            elif not order_line.carat and order_line.gram:
                                jewelry_desc = ' [' + str(order_line.gram) + ' ' + _('กรัม') + ']'
                        item_description += item_line.description + jewelry_desc + u' (' + str(item_line.product_qty or 0.0) + '), '
                    item_description = item_description[:-2]
                elif item.description:
                    item_description = item.description
            except Exception:
                pass
            res[item.id] = item_description
        return res

    def _read_group_location_status(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        access_rights_uid = access_rights_uid or uid
        loc_status_obj = self.pool.get('product.location.status')
        order = loc_status_obj._order
        # lame hack to allow reverting search, should just work in the trivial case
        if read_group_order == 'location_status desc':
            order = "%s desc" % order
        location_status = context.get('location_status', [])
        # retrieve section_id from the context and write the domain
        # - ('id', 'in', 'ids'): add columns that should be present
        # - OR ('department_id', '=', False), ('fold', '=', False): add default columns that are not folded
        # - OR ('department_id', 'in', department_id), ('fold', '=', False) if department_id: add department columns that are not folded
        search_domain = [('code', 'in', location_status)]
        loc_status_ids = loc_status_obj._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
        result = loc_status_obj.name_get(cr, access_rights_uid, loc_status_ids, context=context)
        # restore order of the search
        result.sort(lambda x,y: cmp(loc_status_ids.index(x[0]), loc_status_ids.index(y[0])))

        fold = {}
        for loc_status in loc_status_obj.browse(cr, access_rights_uid, loc_status_ids, context=context):
            fold[loc_status.id] = loc_status.fold or False
        return result, fold

    def _price_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = {
                'price_estimated': 0.0,
                'price_pawned': 0.0,
                'total_price_estimated': 0.0,
                'total_price_pawned': 0.0,
            }
            if item.order_line_id:  # Items
                res[item.id]['price_estimated'] = item.order_line_id.price_unit
                res[item.id]['price_pawned'] = item.order_line_id.pawn_price_unit
                res[item.id]['total_price_estimated'] = item.order_line_id.price_unit * item.product_qty
                res[item.id]['total_price_pawned'] = item.order_line_id.pawn_price_unit * item.product_qty
            else:
                res[item.id]['price_estimated'] = item.order_id.amount_total or False
                res[item.id]['price_pawned'] =item.order_id.amount_pawned or False
                res[item.id]['total_price_estimated'] = item.order_id.amount_total and (item.order_id.amount_total * item.product_qty) or False
                res[item.id]['total_price_pawned'] = item.order_id.amount_pawned and (item.order_id.amount_pawned * item.product_qty) or False
        return res

    # Display price sold, use data from account_voucher_line
    def _price_selling(self, cr, uid, ids, field_name, arg, context=None):
        cr.execute("""
                select product_id, price_unit * quantity as total_price_sold from account_voucher av
                join account_voucher_line avl on av.id = avl.voucher_id
                join product_product pp on pp.id = avl.product_id
                join product_location_status pls on pp.location_status = pls.id
                where av.is_refund = false and av.state = 'posted' and avl.product_id in %s
                and pls.code = 'item_sold'
                and avl.id = (select max(id) from account_voucher_line where product_id = avl.product_id)
            """, (tuple(ids),))
        data = cr.fetchall()
        res = {}
        total_price_pawned = {}
        for item in self.browse(cr, uid, ids, context=context):

            total_price_pawned[item.id] = item.total_price_pawned
            res[item.id] = {
                'total_price_sold': 0.0,
                'total_profit': 0.0,
            }
        # Update price sold
        for r in data:
            res[r[0]].update({
                'total_price_sold': r[1],
                'total_profit': r[1] - total_price_pawned[r[0]],
            })
        return res

    def _get_product(self, cr, uid, ids, context=None):
        item_ids = []
        for pawn in self.browse(cr, uid, ids, context=context):
            item_ids = self.pool.get('product.product').search(cr, uid, [('order_id', '=', pawn.id)], context=context)
        return item_ids

    def _get_product_sold(self, cr, uid, ids, context=None):
        voucher_line_ids = self.pool.get('account.voucher.line').search(cr, uid, [('voucher_id', 'in', ids)], context=context)
        reads = self.pool.get('account.voucher.line').read(cr, uid, voucher_line_ids, ['product_id'], context=context)
        item_ids = [x['product_id'] and x['product_id'][0] or False for x in reads]
        item_ids = [x for x in item_ids if x != False]
        return item_ids

    def _product_qty_total(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = 0.0
            for line in product.line_ids:
                res[product.id] += line.product_qty
        return res

    def _get_product_from_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('product.product.line').browse(cr, uid, ids, context=context):
            result[line.parent_id.id] = True
        return result.keys()

    def _get_extended(self, cr, uid, ids, name, args, context=None):
        res = {}
        for pawn in self.browse( cr, uid, ids, context=context):
            if pawn.extended:
                res[pawn.id] = 'x'
            else:
                res[pawn.id] = ''
        return res


    _columns = {
        'parent_id': fields.many2one('product.product', 'Pawn Ticket', ondelete='cascade'),
        'item_ids': fields.one2many('product.product', 'parent_id', 'Items'),
        'order_line_id': fields.many2one('pawn.order.line', 'Pawn Ticket Line', ondelete='cascade'),
        'line_ids': fields.one2many('product.product.line', 'parent_id', 'Item Detail'),
        'state': fields.selection(AVAILABLE_STATE, 'Status', readonly=True),
        'extended': fields.boolean('Extended', readonly=True),
        'extended_x': fields.function(_get_extended, method=True, string='Extended', type='char'),
        'property_account_pawn_asset': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Pawned Ticket Account",
            view_load=True,
            required=True,
            readonly=False),
        'property_account_expire_asset': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Expired Ticket Account",
            view_load=True,
            required=True,
            readonly=False),
        'property_account_revenue_reposessed_asset': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Revenue Reposessed Ticket Account",
            view_load=True,
            required=True,
            readonly=False),
        'property_account_refund_reposessed_asset': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Revenue Reposessed Ticket Account",
            view_load=True,
            required=True,
            readonly=False),
        'property_account_cost_reposessed_asset': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Cost Reposessed Ticket Account",
            view_load=True,
            required=True,
            readonly=False),
        'item_description': fields.function(_get_item_description, type='text', string='Description', store=True),
        'product_qty': fields.float('Item Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'location_status': fields.many2one('product.location.status', 'Location Status', domain=[('fold', '=', False)], readonly=True),
        'color': fields.integer('Color Index'),
        'price_estimated': fields.function(_price_all, digits_compute=dp.get_precision('Account'), string='Estimated Price',
            store={
                'product.product': (lambda self, cr, uid, ids, ctx: ids, [], 10),
                'pawn.order': (_get_product, ['amount_total', 'amount_pawned'], 10),
            },
            multi='pawn_price', help="Price estimated"),
        'total_price_estimated': fields.function(_price_all, digits_compute=dp.get_precision('Account'), string='Total Estimated Price',
            store={
                'product.product': (lambda self, cr, uid, ids, ctx: ids, [], 10),
                'pawn.order': (_get_product, ['amount_total', 'amount_pawned'], 10),
            },
            multi='pawn_price', help="Total Price estimated"),
        'price_pawned': fields.function(_price_all, digits_compute=dp.get_precision('Account'), string='Pawned Price',
            store={
                'product.product': (lambda self, cr, uid, ids, ctx: ids, [], 10),
                'pawn.order': (_get_product, ['amount_total', 'amount_pawned'], 10),
            },
            multi='pawn_price', help="Price pawned"),
        'total_price_pawned': fields.function(_price_all, digits_compute=dp.get_precision('Account'), string='Total Pawned Price',
            store={
                'product.product': (lambda self, cr, uid, ids, ctx: ids, [], 10),
                'pawn.order': (_get_product, ['amount_total', 'amount_pawned'], 10),
            },
            multi='pawn_price', help="Total Price pawned"),
        'date_order': fields.related('order_id', 'date_order', string='Pawn Date', readonly=True, type="date", store=True),
        'date_due': fields.related('order_id', 'date_due', string='Grace Period End Date', readonly=True, type="date", store=True),
        'date_final_expired': fields.related('order_id', 'date_final_expired', string='Final Expire Date', readonly=True, type="date", store=True),
        # Price sold is coming from its latest account_voucher_line's unit price
        'total_price_sold': fields.function(_price_selling, string='Total Sold Price',
            store={
                'account.voucher': (_get_product_sold, ['state'], 10),
            },
            multi="sold"),
        'total_profit': fields.function(_price_selling, string='Total Profit',
            store={
                'account.voucher': (_get_product_sold, ['state'], 10),
            },
            multi="sold"),
        'product_qty_total': fields.function(_product_qty_total, string='Total Quantity',
            store={
                'product.product': (lambda self, cr, uid, ids, c={}: ids, ['line_ids'], 10),
                'product.product.line': (_get_product_from_line, ['product_qty'], 10),
            }, help="The total quantity."),
        'is_jewelry': fields.related('order_line_id', 'is_jewelry', type='boolean', string='Carat/Gram'),
        'carat': fields.related('order_line_id', 'carat', type='float', string='Carat'),
        'gram': fields.related('order_line_id', 'gram', type='float', string='Gram'),
    }
    _defaults = {
        'color': lambda self, cr, uid, context: randrange(10),
    }
    _group_by_full = {
        'location_status': _read_group_location_status
    }

    _order = 'id desc'
    _sql_constraints = [
        ('code_uniq', 'unique(default_code)', 'Item code must be unique per pawn shop!'),
    ]

    # More menu to show based on context
    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(product_product, self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        hide_action_models = context.get('hide_action_model', False)
        if hide_action_models:
            if res.get('toolbar', False):
                actions = res['toolbar']['action']
                i = 0
                for action in actions:
                    if action.get('res_model', False) in hide_action_models:
                        actions[i] = False
                    i += 1
                while False in actions:
                    actions.remove(False)
        return res

#     # Change status from UI
#     def set_location_status(self, cr, uid, ids, location_status, context=None):
#         for task in self.browse(cr, uid, ids, context=context):
#             self.write(cr, uid, [task.id], {'location_status': location_status}, context=context)
#         return True
#
#     def set_location_status_incoming(self, cr, uid, ids, context=None):
#         return self.set_location_status(cr, uid, ids, 'asset_incoming', context)
#
#     def set_location_status_stock(self, cr, uid, ids, context=None):
#         return self.set_location_status(cr, uid, ids, 'asset_stock', context)
#
#     def set_location_status_outgoing(self, cr, uid, ids, context=None):
#         return self.set_location_status(cr, uid, ids, 'asset_outgoing', context)
#
#     def set_location_status_returned(self, cr, uid, ids, context=None):
#         return self.set_location_status(cr, uid, ids, 'asset_returned', context)

#     def unlink(self, cr, uid, ids, context=None):
#         unlink_ids = []
#         unlink_product_ids = []
#         for item in self.browse(cr, uid, ids, context=context):
#             product_id = item.item_id.id
#             other_item_ids = self.search(cr, uid, [('item_id', '=', product_id), ('id', '!=', item.id)], context=context)
#             if not other_item_ids:
#                 unlink_product_ids.append(product_id)
#             unlink_ids.append(item.id)
#         res = super(pawn_item, self).unlink(cr, uid, unlink_ids, context=context)
#         self.pool.get('product.product').unlink(cr, uid, unlink_product_ids, context=context)
#         return res

    def update_item_status_by_asset(self, cr, uid, asset_ids, val, context=None):
        child_ids = self.search(cr, uid, [('parent_id', 'in', asset_ids)], context=context)
        self.write(cr, uid, child_ids, val, context=context)
        # Update item's location_status
        if val.get('state', False) in ITEM_STATUS_MAPPING:
            location_status = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pawnshop', ITEM_STATUS_MAPPING[val.get('state')])[1]
            self.write(cr, uid, child_ids, {'location_status': location_status}, context=context)
        return True

    def update_asset_state(self, cr, uid, ids, state, context=None):
        # Validate original location_status of the asset before change
        if state in ASSET_STATUS_VS_INIT_LOC:
            for asset in self.browse(cr, uid, ids, context=context):
                if asset.location_status.code not in ASSET_STATUS_VS_INIT_LOC[state]:
                    raise osv.except_osv(_('Error!'), _('Ticket original location not valid.\nTicket is still @ %s') % (asset.location_status.name))
        # Do the update
        if state in ASSET_STATUS_MAPPING:
            location_status = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pawnshop', ASSET_STATUS_MAPPING[state])[1]
            self.write(cr, uid, ids, {'location_status': location_status}, context=context)

    def update_asset_status_by_order(self, cr, uid, order_ids, val, context=None):
        asset_ids = self.search(cr, uid, [('order_id', 'in', order_ids), ('parent_id', '=', False)], context=context)
        # Only if state = 'cancel', location_status = 'asset_returned'
        if val.get('state', False) == 'cancel':
            val.update({'location_status': False})
        self.write(cr, uid, asset_ids, val, context=context)
        self.update_item_status_by_asset(cr, uid, asset_ids, val, context=None)
        # Update asset's location_status
        state = val.get('state', False)
        self.update_asset_state(cr, uid, asset_ids, state, context=context)
        return True

    # Update status of asset and items to For Sales
    def action_asset_sale(self, cr, uid, ids, context=None):
        # Do not allow for Extended Item
        res = [x['extended'] for x in self.read(cr, uid, ids, ['extended'], context=context)]
        if True in res and not context.get('allow_for_sale', False):
            raise osv.except_osv(_('Warning!'), _('Please do not choose ticket which are in extended status!'))
        val = {'state': 'for_sale'}
        self.write(cr, uid, ids, val, context=context)
        self.update_item_status_by_asset(cr, uid, ids, val, context=context)
        # Update asset's location_status
        state = val.get('state', False)
        self.update_asset_state(cr, uid, ids, state, context=context)

    def action_asset_sale_backto_expire(self, cr, uid, ids, context=None):
        # TEST
        is_warning = False
        for asset in self.browse(cr, uid, ids, context=context):
            if asset.extended:
                is_warning = True
            # Asset Check, it must come from for_sale
            if asset.state != 'for_sale':
                is_warning = True
            asset_loc_status = self.pool.get('product.location.status').browse(cr, uid, asset.location_status.id)
            if not asset_loc_status or asset_loc_status.code != ASSET_STATUS_MAPPING['for_sale']:
                is_warning = True
            # Items Check, it must come from for_sale
            for item in asset.item_ids:
                if asset.state != 'for_sale':
                    is_warning = True
                item_loc_status = self.pool.get('product.location.status').browse(cr, uid, item.location_status.id)
                if not item_loc_status or item_loc_status.code != ITEM_STATUS_MAPPING['for_sale']:
                    is_warning = True
        if is_warning:
            raise osv.except_osv(_('Warning!'), _('This ticket can not be set back to expired!'))
        val = {'state': 'expire'}
        self.write(cr, uid, ids, val, context=context)
        self.update_item_status_by_asset(cr, uid, ids, val, context=context)
        # Update asset's location_status
        state = val.get('state', False)
        self.update_asset_state(cr, uid, ids, state, context=context)

    # Update status of ticket and items to Extended
    def action_asset_extend(self, cr, uid, ids, context=None):
        val = {'extended': True}
        self.write(cr, uid, ids, val, context=context)
        self.update_item_status_by_asset(cr, uid, ids, val, context=context)

    def action_asset_unextend(self, cr, uid, ids, context=None):
        val = {'extended': False}
        self.write(cr, uid, ids, val, context=context)
        self.update_item_status_by_asset(cr, uid, ids, val, context=context)

    def onchange_hr_expense_ok(self, cr, uid, ids, hr_expense_ok, context=None):
        res = {}
        if hr_expense_ok:
            res['type'] = 'service'
        return {'value': res}

class product_product_line(osv.osv):

    _name = 'product.product.line'

    def _amount_line(self, cr, uid, ids, prop, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.price_unit * line.product_qty
        return res

    _columns = {
        'parent_id': fields.many2one('product.product', 'Pawn Ticket Reference', select=True, required=True, ondelete='cascade'),
        'item_id': fields.many2one('product.product', 'Pawn Item', required=True, ondelete='cascade'),
        'description': fields.related('item_id', 'description', type='text', string='Description'),
        'categ_id': fields.related('item_id', 'categ_id', type='many2one', relation='product.category', string='Category'),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'uom_id': fields.related('item_id', 'uom_id', type='many2one', relation='product.uom', string='Unit of Measure'),
        'price_pawned': fields.related('item_id', 'price_pawned', type='float', string='Pawn Price', digits_compute=dp.get_precision('Product Price')),
        'pawn_line_id': fields.many2one('pawn.order.line', 'Pawn Order Line Ref.', select=True),
        'is_jewelry': fields.related('pawn_line_id', 'is_jewelry', type='boolean', string='Carat/Gram'),
        'carat': fields.related('pawn_line_id', 'carat', type='float', string='Carat'),
        'gram': fields.related('pawn_line_id', 'gram', type='float', string='Gram'),
    }

product_product_line()


class product_category(osv.osv):
    _inherit = "product.category"
    _columns = {
        'property_line_ids': fields.one2many('product.category.property', 'category_id', 'Item Properties'),
    }
product_category()


class product_category_property(osv.osv):

    _name = "product.category.property"
    _columns = {
        'category_id': fields.many2one('product.category', 'Product Category', required=True, ondelete='cascade'),
        'property_id': fields.many2one('item.property', 'Property', required=True, ondelete='cascade'),
        'active': fields.boolean('Active', required=True),
    }
    _sql_constraints = [
        ('property_uniq', 'unique(category_id, property_id)', 'Duplicated Property!'),
    ]
    _defaults = {
        'active': True
    }

product_category_property()

class product_location_status(osv.osv):
    _name = "product.location.status"
    _description = "Location Status of Products"
    _order = 'sequence'
    _columns = {
        'name': fields.char('Name', size=64, translate=True, required=True),
        'code': fields.char('Code', size=64, required=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of stages."),
        'fold': fields.boolean('Hide in views if empty', help="This stage is not visible, for example in status bar or kanban view, when there are no records in that stage to display."),
    }
    _defaults = {
        'sequence': 1,
        'fold': False,
    }
product_location_status()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
