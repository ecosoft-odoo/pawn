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


class pawn_item_create_receipt(osv.osv_memory):

    _name = "pawn.item.create.receipt"
    _description = "Create receipt from selected pawn items"

    _columns={
        'partner_id': fields.many2one('res.partner', 'Customer', required=True, domain=[('customer', '=', True), ('pawnshop', '=', True)]),
        'item_ids': fields.many2many('product.product', 'pawn_item_create_receipt_rel', 'wizard_id', 'product_id', 'Items'),
        'note': fields.text('Note'),
        'date_sold': fields.date('Date Sold'),
     }

    _defaults = {
        'date_sold': fields.date.context_today,
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(pawn_item_create_receipt, self).default_get(cr, uid, fields, context=context)
        if context and 'active_ids' in context and context['active_ids']:
            res.update({'item_ids': context['active_ids']})
        return res

    def pawn_item_create_receipt(self, cr, uid, ids, context):
        wizard = self.browse(cr, uid, ids[0], context)
        item_ids = [item.id for item in wizard.item_ids]
        item_obj = self.pool.get('product.product')
        voucher_obj = self.pool.get('account.voucher')
        loc_status_obj = self.pool.get('product.location.status')

        data_inv = item_obj.read(cr, uid, item_ids, ['location_status'], context=context)
        for record in data_inv:
            loc_status = loc_status_obj.browse(cr, uid, record['location_status'][0], context=context)
            if loc_status.code == 'item_sold':
                raise osv.except_osv(_('Warning!'), _("Selected item(s) are already Sold Out"))

        items = item_obj.browse(cr, uid, item_ids, context=context)
        # Validate
        l = len(list(set([p.journal_id.id for p in items])))
        if l > 1:
            raise osv.except_osv(_('Error!'), _("Item from different journal is not allowed"))

        lines = []
        prev_shop = None
        # Prepare Lines
        for item in items:
            if prev_shop and prev_shop != item.pawn_shop_id.id:
                raise osv.except_osv(_('Error!'),
                            _('Please make sure that all items are from same shop'))
            line = self._prepare_voucher_line(cr, uid, item, account_id=False, context=context)
            lines.append([0, False, line])
            prev_shop = item.pawn_shop_id.id
        # Prepare Voucher
        voucher = self._prepare_voucher(cr, uid, wizard, lines, context=context)
        voucher_id = voucher_obj.create(cr, uid, voucher, context=context)
        return self.open_vouchers(cr, uid, ids, voucher_id, context=context)

    def _prepare_voucher_line(self, cr, uid, item, account_id=False, context=None):
        if not account_id:
            if item:
                account_id = item.property_account_revenue_reposessed_asset.id
                if not account_id:
                    raise osv.except_osv(_('Error!'),
                            _('Please define revenue reposessed ticket account for this product: "%s" (id:%d).') % \
                                (item.descripton, item.id,))
        if not account_id:
            raise osv.except_osv(_('Error!'),
                        _('There is no revenue reposessed ticket account defined in Pawnshop Accounting Configuration'))
        res = {
            'pawn_shop_id': item.pawn_shop_id.id,
            'name': item.description,
            'account_id': account_id,
            'price_unit': item.standard_price,
            'quantity': item.product_qty,
            'uos_id': item.uom_id.id,
            'product_id': item.id or False,
        }
        return res

    def _prepare_voucher(self, cr, uid, wizard, lines, context=None):
        if context is None:
            context = {}
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        partner = wizard.partner_id
        journal_ids = self.pool.get('account.journal').search(cr, uid,
            [('type', '=', 'sale'), ('company_id', '=', company.id)],
            limit=1)
        if not journal_ids:
            raise osv.except_osv(_('Error!'),
                _('Please define sales journal for this company: "%s" (id:%d).') % (company.name, company.id))
        voucher_vals = {
            'pawn_shop_id': lines[0][2]['pawn_shop_id'],
            'pawnshop': True,
            'type': 'sale',
            'reference': False,
            'account_id': partner.property_account_receivable.id,
            'partner_id': partner.id,
            'journal_id': journal_ids[0],
            'line_cr_ids': lines,
            'name': wizard.note,
            'pay_now': 'pay_now',
            'date': wizard.date_sold or fields.date.context_today(self, cr, uid, context=context),
            'company_id': company.id,
            'user_id': uid or False
        }
        return voucher_vals

    def open_vouchers(self, cr, uid, ids, voucher_id, context=None):
        """ open a view on one of the given voucher_ids """
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'account_voucher', 'view_sale_receipt_form')
        form_id = form_res and form_res[1] or False
        tree_res = ir_model_data.get_object_reference(cr, uid, 'account_voucher', 'view_voucher_tree')
        tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Sales Receipt'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'account.voucher',
            'res_id': voucher_id,
            'view_id': False,
            'views': [(form_id, 'form'), (tree_id, 'tree')],
            'context': "{'default_type': 'sale', 'type': 'sale'}",
            'type': 'ir.actions.act_window',
        }

pawn_item_create_receipt()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
