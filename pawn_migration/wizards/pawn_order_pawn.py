# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.osv import  osv


class pawn_order_pawn(osv.osv_memory):
    _inherit = "pawn.order.pawn"

    def _check_pawn_item_image_first(self, cr, uid, pawn, context=None):
        # Don't check pawn item image for data migration
        return True
