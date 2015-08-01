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
import openerp.addons.decimal_precision as dp


class pawn_line_property(osv.osv_memory):

    _name = "pawn.line.property"
    _description = "Pawn Line Property"

    _columns = {
        'order_line_id': fields.many2one('pawn.order.line', 'Item', readonly=True),
        'property_line': fields.one2many('pawn.line.property.line', 'pawn_line_property_id', 'Property Lines', readonly=False),
        'image': fields.binary("Image",
            help="This field holds the image used as image for the product, limited to 1024x1024px."),
    }
    _defaults = {
        'order_line_id': lambda self, cr, uid, ctx: ctx.get('active_id', False),
        'image': lambda self, cr, uid, ctx: self.pool.get('pawn.order.line').browse(cr, uid, ctx.get('active_id', False)).image
    }

    def onchange_order_line_id(self, cr, uid, ids, order_line_id, context=None):
        if context is None:
            context = {}
        order_line = self.pool.get('pawn.order.line').browse(cr, uid, order_line_id)
        category_properties = order_line.categ_id.property_line_ids
        property_line = []
        exising_properties = {}
        for line in order_line.property_ids:
            exising_properties.update({line.property_id.id: {
                                            'property_line_id': line.property_line_id.id,
                                            'other_property': line.other_property
                                            }})
        for line in category_properties:
            x = exising_properties.get(line.property_id.id, {})
            final_property = {'property_id': line.property_id.id,
                              'property_line_id': line.property_id.line_ids and line.property_id.line_ids[0].id or False,
                              'other_property': False
                              }
            final_property.update(x)
            property_line.append([0, 0, final_property])
        return {'value': {
            'property_line': property_line,
        }}

    def action_save(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        order_line_obj = self.pool.get('pawn.order.line')
        for property_data in self.browse(cr, uid, ids):
            order_line_obj.action_update_pawn_line_property(cr, uid, property_data, context=context)
        return True
#         return {'type': 'ir.actions.client',
#                 'tag': 'reload'}

pawn_line_property()


class pawn_line_property_line(osv.osv_memory):

    _name = "pawn.line.property.line"
    _description = "Item Property Lines"

    _columns = {
        'pawn_line_property_id': fields.many2one('pawn.line.property', 'Pawn Line Property'),
        'property_id': fields.many2one('item.property', 'Property', required=True, ondelete='cascade'),
        'property_line_id': fields.many2one('item.property.line', 'Value', domain="[('property_id', '=', property_id)]", required=True, ondelete='cascade'),
        'other_property': fields.text('Other', required=False),
    }

pawn_line_property_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
