# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.osv import fields, osv
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _


class pawn_order(osv.osv):
    _inherit = "pawn.order"

    _columns = {
        # Editable field for import pawn order
        "book": fields.integer(readonly=False, string="Book"),
        "number": fields.integer(readonly=False, string="Number"),
        "date_order": fields.date(readonly=False, string="Pawn Date"),
        "buddha_year": fields.char(readonly=False, string="Buddha Year"),
        "amount_pawned": fields.float(readonly=False, string="Pawned Amount"),
    }

    def create(self, cr, uid, vals, context=None):
        # book and number input manually, no generate from system
        book, number = vals.get("book", 0), vals.get("number", 0)
        pawn_id = super(pawn_order, self).create(cr, uid, vals, context=context)
        if not context.get("is_renew"):
            if not book or not number:
                raise osv.except_osv(_("Warning!"),
                    _("Book or number don't assign to zero."))
            self.write(cr, uid, [pawn_id], {
                "book": book,
                "number": number,
            })
        return pawn_id

    def write(self, cr, uid, ids, vals, context=None):
        res = super(pawn_order, self).write(cr, uid, ids, vals, context=context)
        for pawn in self.browse(cr, uid, ids, context=context):
            name = pawn.pawn_shop_id.code + pawn.period_id.fiscalyear_id.code + str(pawn.book).zfill(3) + str(pawn.number).zfill(3)
            if name != pawn.name:
                self.write(cr, uid, [pawn.id], {"name": name})
        return res

    def _check_pawn_item_image_first(self, cr, uid, pawn, context=None):
        # Don't check pawn item image for data migration
        return True

    def update_data(self, cr, uid, context=None):
        # Re assign name (For update pawn asset)
        PawnOrder = self.pool.get("pawn.order")
        pawn_order_ids = PawnOrder.search(cr, uid, [("state", "=", "draft")], context=context)
        pawn_orders = PawnOrder.browse(cr, uid, pawn_order_ids, context=context)
        for pawn_order in pawn_orders:
            PawnOrder.write(cr, uid, [pawn_order.id], {"name": pawn_order.name}, context=context)
        # Update data in product.template
        ProductTemplate = self.pool.get("product.template")
        product_template_ids = ProductTemplate.search(cr, uid, [("journal_id", "=", False)], context=context)
        product_templates = ProductTemplate.browse(cr, uid, product_template_ids, context=context)
        for product_template in product_templates:
            if product_template.order_id:
                cr.execute("""
                    update product_template set journal_id = %s where id = %s
                """ % (product_template.order_id.journal_id.id, product_template.id))
        # Update data in product.product
        ProductProduct = self.pool.get("product.product")
        product_ids = ProductProduct.search(cr, uid, [("state", "=", "draft")], context=context)
        products = ProductProduct.browse(cr, uid, product_ids, context=context)
        for product in products:
            if product.order_id and product.order_line_id:
                item_description = ProductProduct._get_item_description(cr, uid, [product.id], ["item_description"], None)[product.id]
                if product.order_line_id:
                    price_estimated = product.order_line_id.price_unit
                    price_pawned = product.order_line_id.pawn_price_unit
                    total_price_estimated = product.order_line_id.price_subtotal
                    total_price_pawned = product.order_line_id.pawn_price_subtotal
                    product_qty = product.order_line_id.product_qty
                else:
                    price_estimated = sum([line.price_subtotal for line in product.order_id.order_line])
                    price_pawned = sum([line.pawn_price_subtotal for line in product.order_id.order_line])
                    total_price_estimated = price_estimated
                    total_price_pawned = price_pawned
                    product_qty = 1.0
                cr.execute("""
                    update product_product set item_description = '%s', price_estimated = %s, price_pawned = %s, total_price_estimated = %s, total_price_pawned = %s, product_qty = %s where id = %s
                """ % (item_description, price_estimated or 0.0, price_pawned or 0.0, total_price_estimated or 0.0, total_price_pawned or 0.0, product_qty or 1.0, product.id))

    def action_pawn(self, cr, uid, context=None):
        PawnOrder = self.pool.get("pawn.order")
        PawnOrderPawn = self.pool.get("pawn.order.pawn")
        Product = self.pool.get("product.product")
        LocationStatus = self.pool.get("product.location.status")
        pawn_order_ids = PawnOrder.search(cr, uid, [("state", "=", "draft")], context=context)
        for pawn_order_id in pawn_order_ids:
            pawn_order = PawnOrder.browse(cr, uid, pawn_order_id, context=context)
            context = {"active_id": pawn_order_id}
            journal_id = PawnOrderPawn._get_journal(cr, uid, context=context)
            parent_id = PawnOrderPawn._get_parent_id(cr, uid, context=context)
            amount = PawnOrderPawn._get_amount(cr, uid, context=context)
            wizard_id = PawnOrderPawn.create(cr, uid, {
                "journal_id": journal_id, "parent_id": parent_id, "amount": amount,
                "date_due_ticket": str(datetime.strptime(pawn_order.date_order, '%Y-%m-%d').date() + relativedelta(months=pawn_order.rule_id.length_month + 1 or 0.0)),
            })
            PawnOrderPawn.action_pawn(cr, uid, [wizard_id], context=context)
        # Pawn Ticket : Incoming -> In-Stock
        product_ids = Product.search(cr, uid, [("type", "=", "pawn_asset"), ("state", "!=", "draft"), ("location_status.code", "=", "asset_incoming")])
        for product_id in product_ids:
            location_status_id = LocationStatus.search(cr, uid, [("code", "=", "asset_stock")], limit=1)[0]
            Product.write(cr, uid, [product_id], {
                "location_status": location_status_id,
            }, context=context)
