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

from openerp.osv import osv
from openerp.tools.translate import _


class pawn_asset_to_for_sale(osv.osv_memory):

    _name = "pawn.asset.to.for.sale"
    _description = "Change ticket status to For Sale"    

    def pawn_asset_to_for_sale(self, cr, uid, ids, context=None):
        self.pool.get('product.product').action_asset_sale(cr, uid, context['active_ids'], context=context)
        return {'type': 'ir.actions.act_window_close'}

pawn_asset_to_for_sale()

class pawn_item_to_borrowed(osv.osv_memory):

    _name = "pawn.item.to.borrowed"
    _description = "Change location status of items"

    def for_sales_to_borrowed(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        item_obj = self.pool.get('product.product')
        loc_status_obj = self.pool.get('product.location.status')
        data_inv = item_obj.read(cr, uid, context['active_ids'], ['location_status'], context=context)

        for record in data_inv:
            loc_status = loc_status_obj.browse(cr, uid, record['location_status'][0], context=context)
            if loc_status.code != 'item_for_sale':
                raise osv.except_osv(_('Warning!'), _("Selected item(s) are not in 'For Sales' status"))
            to_loc_status = loc_status_obj.search(cr, uid, [('code', '=', 'item_borrowed')])[0]
            item_obj.write(cr, uid, [record['id']], {'location_status': to_loc_status})
        return {'type': 'ir.actions.act_window_close'}

pawn_item_to_borrowed()

class pawn_item_to_for_sale(osv.osv_memory):

    _name = "pawn.item.to.for.sale"
    _description = "Change location status of items"

    def borrowed_to_for_sales(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        item_obj = self.pool.get('product.product')
        loc_status_obj = self.pool.get('product.location.status')
        data_inv = item_obj.read(cr, uid, context['active_ids'], ['location_status'], context=context)

        for record in data_inv:
            loc_status = loc_status_obj.browse(cr, uid, record['location_status'][0], context=context)
            if loc_status.code != 'item_borrowed':
                raise osv.except_osv(_('Warning!'), _("Selected item(s) are not in 'Borrowed' status"))
            to_loc_status = loc_status_obj.search(cr, uid, [('code', '=', 'item_for_sale')])[0]
            item_obj.write(cr, uid, [record['id']], {'location_status': to_loc_status})
        return {'type': 'ir.actions.act_window_close'}

pawn_item_to_borrowed()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
