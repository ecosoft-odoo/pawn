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


class select_multi_sale_item(osv.osv_memory):
    _name = 'select.multi.sale.item'

    _columns = {
        'item_ids': fields.many2many('product.product', 'select_multi_sale_item_rel', 'wizard_id', 'product_id', 'Items'),
    }

    def action_confirm(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if 'active_ids' in context and context['active_ids']:
            voucher_obj = self.pool.get('account.voucher')
            voucher_line_obj = self.pool.get('account.voucher.line')
            wizard = self.browse(cr, uid, ids[0], context=context)
            if wizard.item_ids:
                val_list = []
                for item in wizard.item_ids:
                    vals = {}
                    vals['product_id'] = item.id,
                    vals.update(voucher_line_obj.onchange_product_id(cr, uid, [], item.id, context=context)['value'])
                    val_list.append((0, 0, vals))
                voucher_obj.write(cr, uid, context['active_ids'], {'line_cr_ids': val_list}, context=context)
        return True
