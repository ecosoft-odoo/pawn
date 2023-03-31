# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.osv import fields, osv


class pawn_order(osv.osv):
    _inherit = "pawn.order"

    _columns = {
        "book": fields.integer(readonly=False, string="Book"),
        "number": fields.integer(readonly=False, string="Number"),
    }

    def create(self, cr, uid, vals, context=None):
        book, number = vals.get("book", 0), vals.get("number", 0)
        pawn_id = super(pawn_order, self).create(cr, uid, vals, context=context)
        if not context.get("is_renew"):
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

    def update_data(self, cr, uid, context=None):
        # Update data in product.template
        ProductTemplate = self.pool.get("product.template")
        product_template_ids = ProductTemplate.search(cr, uid, [], context=context)
        product_templates = ProductTemplate.browse(cr, uid, product_template_ids, context=context)
        for product_template in product_templates:
            if product_template.order_id:
                cr.execute("""
                    update product_template set journal_id = %s where id = %s
                """ % (product_template.order_id.journal_id.id, product_template.id))
        # Update data in product.product
        ProductProduct = self.pool.get("product.product")
        product_ids = ProductProduct.search(cr, uid, [], context=context)
        products = ProductProduct.browse(cr, uid, product_ids, context=context)
        for product in products:
            item_description = ProductProduct._get_item_description(cr, uid, [product.id], ["item_description"], None)[product.id]
            price = ProductProduct._price_all(cr, uid, [product.id], ["total_price_pawned", "price_estimated", "price_pawned", "total_price_estimated"], None)[product.id]
            qty = ProductProduct._product_qty_total(cr, uid, [product.id], ["product_qty_total"], None)[product.id]
            cr.execute("""
                update product_product set item_description = '%s', price_estimated = %s, price_pawned = %s, total_price_estimated = %s, total_price_pawned = %s, product_qty_total = %s where id = %s
            """ % (item_description, price["price_estimated"] or 0.0, price["price_pawned"] or 0.0, price["total_price_estimated"] or 0.0, price["total_price_pawned"] or 0.0, qty or 0.0, product.id))
        # Update data in pawn.order.line
        PawnOrderLine = self.pool.get("pawn.order.line")
        line_ids = PawnOrderLine.search(cr, uid, [], context=context)
        lines = PawnOrderLine.browse(cr, uid, line_ids, context=context)
        for line in lines:
            price = PawnOrderLine._amount_line(cr, uid, [line.id], ["price_unit", "pawn_price_unit"], None)[line.id]
            cr.execute("""
                update pawn_order_line set price_unit = %s, pawn_price_unit = %s where id = %s
            """ % (price["price_unit"] or 0.0, price["pawn_price_unit"] or 0.0, line.id))
