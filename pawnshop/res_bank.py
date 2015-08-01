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
import re
from openerp.osv import fields, osv
import time
from datetime import datetime
from openerp.tools.translate import _

class res_partner_bank(osv.osv):

    _inherit = 'res.partner.bank'
    
    def _get_shop(self, cr, uid, context=None):
        if context is None:
            context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company_id = context.get('company_id', user.company_id.id)        
        shop_ids = self.pool.get('pawn.shop').search(cr, uid, [('company_id', '=', company_id), ('user_ids', 'in', uid)], context=context)
        shop_id = shop_ids and shop_ids[0] or False
        return shop_id

    # Overwrite
    def _bank_type_get(self, cr, uid, context=None):
        bank_type_obj = self.pool.get('res.partner.bank.type')
        result = []
        type_ids = bank_type_obj.search(cr, uid, [])
        bank_types = bank_type_obj.browse(cr, uid, type_ids, context=context)
        for bank_type in bank_types:
            result.append((bank_type.code, bank_type.name))
        return result

    _columns = {
        'acc_number': fields.char('Account Number', size=64, required=False),
        'is_cash': fields.boolean('Cash', required=False),
        'state': fields.selection(_bank_type_get, 'Bank Account Type', required=False,
            change_default=True),  # Change to required=False, move required logic to view
        'pawn_shop_id': fields.many2one('pawn.shop', 'Shop', domain="[('company_id','=',company_id)]", readonly=False, required=True),
    }
    _defaults = {
        'acc_number': '0',
        'is_cash': lambda self,cr,uid,c: c.get('is_cash', False),  # Normally, default to False
        'pawn_shop_id': _get_shop,
    }
    
res_partner_bank()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
