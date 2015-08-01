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
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv


class item_property(osv.osv):

    _name = 'item.property'
    _description = 'Item Properties'

    def _selection_list(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for prop in self.browse(cursor, user, ids, context=context):
            str_list = ''
            for line in prop.line_ids:
                str_list += len(str_list) and (', ' + line.name) or line.name
            res[prop.id] = str_list
        return res

    _columns = {
        'name': fields.char('Property Name', size=64, required=True),
        'line_ids': fields.one2many('item.property.line', 'property_id', 'Selection List'),
        'selection_list': fields.function(_selection_list, string='Selection List', type='char')
    }

item_property()


class item_property_line(osv.osv):

    _name = 'item.property.line'
    _description = 'Item Property Selections'
    _rec_name = 'name'

    _columns = {
        'name': fields.char('Selection', size=128, required=True),
        'allow_text': fields.boolean('Allow Text', required=False),
        'property_id': fields.many2one('item.property', 'Item Property', required=True, ondelete='cascade'),
    }
    _defaults = {
        'allow_text': False
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
