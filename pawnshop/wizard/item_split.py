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
import ast

class item_split(osv.osv_memory):

    _name = "item.split"
    _description = "Split Item"

    def _get_item_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        return context.get('active_id', False)

    _columns = {
        'item_id': fields.many2one('product.product', 'Product', readonly=True),
        'split_line': fields.one2many('item.split.line', 'item_id', 'Split Lines', readonly=False), 
    }
    _defaults = {
        'item_id': _get_item_id,
    }
    
    def open_items(self, cr, uid, item_ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'pawnshop', 'action_pawn_items_for_sale')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        domain = ast.literal_eval(result['domain'])
        domain.append(('id', 'in', item_ids))
        result['domain'] = domain
        result['name'] = _('Items For Sales')
        return result

    def action_split(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        wizard = self.browse(cr, uid, ids[0], context)
        # Check lines >= 2 lines when split
        if len(wizard.split_line) < 2:
            raise osv.except_osv(_('Warning!'), _('At least 2 split line must be created!'))
        # Check total quantity must equal to original
        new_qty = 0.0
        item = wizard.item_id
        for line in wizard.split_line:
            new_qty += line.product_qty
        if new_qty != item.product_qty:
            raise osv.except_osv(_('Warning!'), _('Sum of quantity must equal to the original quantity'))
        
        # Start coping and redirecton
        item_obj = self.pool.get('product.product')
        i = 0
        new_item_ids = []
        for line in wizard.split_line:
            if line.product_qty:
                i += 1
                default = {'product_qty': line.product_qty,
                           'description': line.description}
                new_item_id = item_obj.copy(cr, uid, item.id, default, context=context)
                item_obj.write(cr, uid, [new_item_id], {'name': item.name + '.' + str(i)}, context=context)
                new_item_ids.append(new_item_id)
        # Inactive old item
        item_obj.write(cr, uid, [item.id], {'active': False})
        return self.open_items(cr, uid, new_item_ids, context=context)

item_split()


class item_split_line(osv.osv_memory):

    _name = "item.split.line"
    _description = "Item Split Line"

    def _get_description(self, cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            item = self.pool.get('product.product').browse(cr, uid, active_id, context=context)
            return item.description or False
        return False

    _columns = {
        'item_id': fields.many2one('item.split', 'Item Split'),
        'description': fields.text('Description', required=True),
        'product_qty': fields.float('Item Quantity', required=True),       
    }
    _defaults = {
        'description': _get_description,
        'product_qty': 0.0
    }

item_split_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
