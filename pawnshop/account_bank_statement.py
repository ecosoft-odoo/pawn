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
import math
from openerp.tools.translate import _

class account_cash_statement(osv.osv):

    _inherit = 'account.bank.statement'

    def _auto_fill_cash_box(self, cr, uid, ids, context=None):
        cash_line_obj = self.pool.get('account.cashbox.line')
        for st in self.browse(cr, uid, ids, context=context):
            cr.execute('select id, pieces from account_cashbox_line where bank_statement_id = %s order by pieces desc', (st.id,))
            cash_lines = cr.fetchall()
            bal = round(st.balance_end, 2)
            for line in cash_lines:
                pieces = line[1]
                if not pieces:
                    continue
                qty = int(bal/pieces)
                bal = round(math.fmod(bal, pieces), 2)
                cash_line_obj.write(cr, uid, [line[0]], {'number_closing': qty})
            if bal > 10 **-4:
                raise osv.except_osv(_('Warning!'),
                    _('After attempt to fill in the cash box line, there are still remain amount of (%.2f).') % (bal,))
        self._update_balances(cr, uid, ids, context)                
        return True

    def button_confirm_cash_auto(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # Auto fill in cash box
        self._auto_fill_cash_box(cr, uid, ids, context=context)
        context.update({'is_cash_register': True})
        return super(account_cash_statement, self).button_confirm_cash(cr, uid, ids, context=context)

    def _get_default_shop_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company_id = context.get('company_id', user.company_id.id)
        shop_ids = self.pool.get('pawn.shop').search(cr, uid, [('company_id', '=', company_id), ('user_ids', 'in', uid)], context=context)
        return shop_ids and shop_ids[0] or False

    _columns = {
        # docnumber
        'number': fields.integer('Number', select=True, readonly=True),
        # --
        'pawn_shop_id': fields.many2one('pawn.shop', 'Shop', domain="[('company_id','=',company_id)]", readonly=True, required=True, states={'draft': [('readonly', False)]}),
    }
    _defaults = {
        'pawn_shop_id': _get_default_shop_id
    }
    _sql_constraints = [('name_unique', 'unique(company_id,name)', _('The number must be unique, make sure each shop prefix is unique!'))]

    def _get_next_name(self, cr, uid, date, pawn_shop_id, context=None):
        year = date[:4]
        # Get year from date
        cr.execute("""select coalesce(max(number), 0) from account_bank_statement
            where to_char(date, 'YYYY') = %s and pawn_shop_id = %s""", 
            (year, pawn_shop_id))
        number = cr.fetchone()[0] or 0
        number += 1
        shop_code = self.pool.get('pawn.shop').browse(cr, uid, pawn_shop_id).pc_code or '--'
        next_name = shop_code + '/' + year + '/' + str(number).zfill(3)     
        return next_name, number

    def create(self, cr, uid, vals, context=None):
        if vals.get('name', '/') == '/':
            name, number = self._get_next_name(cr, uid, vals.get('date', False), vals.get('pawn_shop_id', False), context=context)
            vals.update({'name': name, 'number': number})
        return super(account_cash_statement, self).create(cr, uid, vals, context=context)

    def copy(self, cr, uid, id, defaults, context=None):
        raise osv.except_osv(_('User Error!'), _('Duplication is not allowed!'))
    
account_cash_statement()


class account_bank_statement_line(osv.osv):
     
    _inherit = 'account.bank.statement.line'
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=False),
    }
    
    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        if context is None:
            context = {}
        if not product_id:
            return False
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        if product:
            account_id = product.property_account_expense.id
            return {'value': {'account_id': account_id}}
        return False
    
account_bank_statement_line()
    


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
