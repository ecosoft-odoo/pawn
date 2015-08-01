# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

INTEREST_INTERVAL = [('month_end', 'End of month'),
                  ('month_mid', '15th of month'),
                  ('daily', 'Everyday')]


class pawn_config_settings(osv.osv_memory):
    _name = 'pawn.config.settings'
    _inherit = 'res.config.settings'
    _columns = {
        'property_account_pawn_asset': fields.many2one('account.account', 'Pawned Ticket Account'),
        'property_account_expire_asset': fields.many2one('account.account', 'Expired Ticket Account'),
        'property_account_revenue_reposessed_asset': fields.many2one('account.account', 'Revenue Reposessed Ticket Account'),
        'property_account_refund_reposessed_asset': fields.many2one('account.account', 'Refund Reposessed Ticket Account'),
        'property_account_cost_reposessed_asset': fields.many2one('account.account', 'Cost Reposessed Ticket Account'),
        'property_account_interest_discount': fields.many2one('account.account', 'Interest Discount'),
        'property_account_interest_addition': fields.many2one('account.account', 'Interest Addition'),
        'property_journal_accrued_interest': fields.many2one('account.journal', 'Accrued Interest Journal'),
        'property_journal_actual_interest': fields.many2one('account.journal', 'Actual Interest Journal'),
        'default_interest_interval': fields.selection(INTEREST_INTERVAL,
            'Interest Calculation Interval', default_model='pawn.order',
            help="Specify how often interest journal will be created."),
    }
    _defaults = {
        'default_interest_interval': 'month_end'
    }

    def set_default_account_pawn(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids)[0]
        property_obj = self.pool.get('ir.property')
        field_obj = self.pool.get('ir.model.fields')
        todo_list = [
            ('property_account_pawn_asset', 'product.product', 'account.account'),
            ('property_account_expire_asset', 'product.product', 'account.account'),
            ('property_account_revenue_reposessed_asset', 'product.product', 'account.account'),
            ('property_account_refund_reposessed_asset', 'product.product', 'account.account'),
            ('property_account_cost_reposessed_asset', 'product.product', 'account.account'),
            ('property_account_interest_discount', 'pawn.order', 'account.account'),
            ('property_account_interest_addition', 'pawn.order', 'account.account'),
            ('property_journal_accrued_interest', 'pawn.order', 'account.journal'),
            ('property_journal_actual_interest', 'pawn.order', 'account.journal'),
        ]
        for record in todo_list:
            account = getattr(wizard, record[0])
            value = account and 'account.account,' + str(account.id) or False
            if value:
                field = field_obj.search(cr, uid, [('name', '=', record[0]), ('model', '=', record[1]), ('relation', '=', record[2])], context=context)
                vals = {
                    'name': record[0],
                    'company_id': False,
                    'fields_id': field[0],
                    'value': value,
                }
                property_ids = property_obj.search(cr, uid, [('name', '=', record[0])], context=context)
                if property_ids:
                    #the property exist: modify it
                    property_obj.write(cr, uid, property_ids, vals, context=context)
                else:
                    #create the property
                    property_obj.create(cr, uid, vals, context=context)
        return True

    def get_default_account_pawn(self, cr, uid, fields, context=None):
        ir_property_obj = self.pool.get('ir.property')
        fiscal_obj = self.pool.get('account.fiscal.position')
        todo_list = [
            ('property_account_pawn_asset', 'product.product', 'account.account'),
            ('property_account_expire_asset', 'product.product', 'account.account'),
            ('property_account_revenue_reposessed_asset', 'product.product', 'account.account'),
            ('property_account_refund_reposessed_asset', 'product.product', 'account.account'),
            ('property_account_cost_reposessed_asset', 'product.product', 'account.account'),
            ('property_account_interest_discount', 'pawn.order', 'account.account'),
            ('property_account_interest_addition', 'pawn.order', 'account.account'),
            ('property_journal_accrued_interest', 'pawn.order', 'account.journal'),
            ('property_journal_actual_interest', 'pawn.order', 'account.journal'),
        ]
        res = {}
        for record in todo_list:
            prop = ir_property_obj.get(cr, uid,
                        record[0], record[1], context=context)
            prop_id = prop and prop.id or False
            account_id = fiscal_obj.map_account(cr, uid, False, prop_id)
            res.update({record[0]: account_id})
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
