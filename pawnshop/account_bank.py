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


class bank(osv.osv):

    _inherit = "res.partner.bank"

    # Method Overwrite
    def _get_journal_currency(self, cr, uid, ids, name, args, context=None):
        res = dict.fromkeys(ids, False)
        account_obj = self.pool.get('account.account')
        for bank in self.browse(cr, uid, ids, context=context):
            # kittiu: 
            context.update({'pawn_shop_id': bank.pawn_shop_id and bank.pawn_shop_id.id or False})
            context.update({'profit_center': bank.journal_id and bank.journal_id.profit_center or False})
            # --
            if bank.journal_id and bank.journal_id.default_debit_account_id:
                account_id = bank.journal_id.default_debit_account_id.id
                # Note: we can't use the normal orm account_id.balance because it wont' be refreshed for the same account (too smart)
                # So, we get it manually
                result = account_obj.manual_compute(cr, uid, [account_id], ['balance'], context=context)
                balance = result[account_id]['balance']
                res[bank.id] = balance
        return res

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id.id

    _columns = {
        'balance': fields.function(_get_journal_currency, type="float", readonly=True, string="Balance in Company's Currency"),
    }
    _defaults = {
        'company_id': _default_company
    }

bank()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
