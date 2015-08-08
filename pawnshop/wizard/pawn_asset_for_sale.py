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
from openerp.tools.translate import _

class pawn_undo_cancel(osv.osv_memory):
    
    def _validate_secret_key(self, cr, uid, pawn_shop, secret_key, context=None):
        # If there is no key, always ok.
        if not secret_key and not pawn_shop.secret_key and not pawn_shop.secret_key2:
            return True
        else:
            keys = []
            if pawn_shop.secret_key:
                keys.append(pawn_shop.secret_key)
            if pawn_shop.secret_key2:
                keys.append(pawn_shop.secret_key2)
            if secret_key in keys:
                return True
            else:
                raise osv.except_osv(_('Invalid Key!'), _("You need to provide a valid shop's secret key for this action!"))            
            return False

    _name = "pawn.asset.for.sale"
    _description = "Asset For Sales"
    _columns = {
        'secret_key': fields.char('Secret Key'),
    }

    def action_execute(self, cr, uid, ids, context=None):
        if context == None:
            context= {}
        product_obj = self.pool.get('product.product')
        wizard = self.browse(cr, uid, ids[0], context)
        active_ids = context.get('active_ids', False)
        for product in product_obj.browse(cr, uid, active_ids, context=context):
            self._validate_secret_key(cr, uid, product.pawn_shop_id, wizard.secret_key, context=context)
            context.update({'allow_for_sale': True})
            product_obj.action_asset_sale(cr, uid, [product.id], context=context)
        return True

pawn_undo_cancel()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
