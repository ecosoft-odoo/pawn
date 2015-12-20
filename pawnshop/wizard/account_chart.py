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

class account_chart(osv.osv_memory):

    _inherit = "account.chart"
    _columns = {
        'pawn_shop_id': fields.many2one('pawn.shop', 'Shop', help='Keep empty for all'),
        'profit_center': fields.selection([(1, '1'), (2, '2')], 'Profit Center', help='Keep empty for all')
    }

    def _get_fiscalyear(self, cr, uid, context=None):
        """Return default Fiscalyear value"""
        return self.pool.get('account.fiscalyear').find(cr, uid, context=context)
    
    def account_chart_open_window(self, cr, uid, ids, context=None):
        result = super(account_chart, self).account_chart_open_window(cr, uid, ids, context=context)
        data = self.read(cr, uid, ids, [], context=context)[0]
        context_dict = eval(result['context'])
        context_dict.update({
            'pawn_shop_id': data.get('pawn_shop_id') and data.get('pawn_shop_id')[0] or False,
            'profit_center': data.get('profit_center', False),
        })
        result['context'] = str(context_dict)
        return result

account_chart()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
