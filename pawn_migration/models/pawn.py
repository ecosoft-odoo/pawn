# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.osv import fields, osv


class pawn_order(osv.osv):
    _inherit = "pawn.order"

    _columns = {
        "book": fields.integer(readonly=False),
        "number": fields.integer(readonly=False),
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
