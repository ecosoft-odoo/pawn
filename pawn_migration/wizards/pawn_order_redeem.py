# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.osv import fields, osv


class pawn_order_redeem(osv.osv_memory):
    _inherit = "pawn.order.redeem"

    _columns = {
        "date_redeem": fields.date(readonly=False),
        "interest_amount": fields.float(readonly=False),
    }
