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


class product_template(osv.osv):

    _inherit = 'product.template'
    _columns = {
        'date_sold': fields.date('Date Sold'),
        'type': fields.selection([('product', 'Stockable Product'),
                                  ('consu', 'Pawn Item'),
                                  ('service', 'Service'),
                                  ('pawn_asset', 'Pawn Ticket')], 'Product Type', required=True, help="Consumable: Will not imply stock management for this product. \nStockable product: Will imply stock management for this product."),
    }

product_template()


class product_category(osv.osv):

    _inherit = 'product.category'
    _columns = {
        'uom_ids': fields.many2many('product.uom', 'category_uom_rel', 'categ_id', 'uom_id', 'Unit of Measures'),
        'is_jewelry': fields.boolean('Carat/Gram', help='If checked, pawn ticket line will allow entry of jewelry measurement, i.e., carat, gram')
    }

product_category()


class product_uom(osv.osv):

    _inherit = 'product.uom'
    _columns = {
        'categ_ids': fields.many2many('product.category', 'category_uom_rel', 'uom_id', 'categ_id', 'Categories'),
    }

product_uom()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
