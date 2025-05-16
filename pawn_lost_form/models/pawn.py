# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Ecosoft Co., Ltd. (http://ecosoft.co.th).
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

from datetime import datetime
from openerp.osv import fields, osv
from openerp.addons.pawnshop import pawn

pawn.MAX_LINE = 6 # Change max pawn line from 8 lines to 6 lines (Objective: print pawn ticket only)

class pawn_order(osv.osv):
    _inherit = "pawn.order"

    _columns = {
        "lost_date": fields.date('Lost date', readonly=True),
    }

    def onchange_is_lost(self, cr, uid, ids, is_lost, context=None):
        if is_lost:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return {'value': {'lost_date': now}}
        return {'value': {'lost_date': False}}
    
    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('is_lost'):
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            vals['lost_date'] = now
        return super(pawn_order, self).write(cr, uid, ids, vals, context=context)

class pawn_order_line(osv.osv):
    _inherit = 'pawn.order.line'

    # Set maximum size of description equal to 85 (Objective: print pawn ticket only)
    _columns = {
        'name': fields.text('Description', required=True, size=85),
    }