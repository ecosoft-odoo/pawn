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

from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.osv import fields, osv
from openerp import netsvc
from openerp import pooler
from openerp.tools.translate import _


class pawn_order_pawn(osv.osv_memory):

    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            return pawn.journal_id and pawn.journal_id.id or False
        return False

    def _get_date_due_ticket(self, cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            return str(datetime.strptime(pawn.date_order, "%Y-%m-%d").date() + relativedelta(months=pawn.rule_id.length_month + 1 or 0.0))
        return False

    def _get_parent_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            return pawn.parent_id and pawn.parent_id.id or False
        return False

    def _get_amount(self, cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            if pawn.parent_id:
                return pawn.amount_net
            else:
                return pawn.amount_pawned
        return False

    _name = "pawn.order.pawn"
    _description = "Pawn"
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Journal', domain="[('type','=','cash'), ('pawn_journal', '=', True)]", required=True),
        'parent_id': fields.many2one('pawn.order', 'Previous Pawn Ticket'),
        'amount': fields.float('Net Amount', readonly=True),
        'date_due_ticket': fields.date(string='Due Date', required=True),
    }
    _defaults = {
        'journal_id': _get_journal,
        'date_due_ticket': _get_date_due_ticket,
        'parent_id': _get_parent_id,
        'amount': _get_amount
    }

    def _check_pawn_item_image_first(self, cr, uid, pawn, context=None):
        if not pawn.pawn_item_image_first:
            raise osv.except_osv(_('Error!'), _('Please provide an image of the item before pawning it.'))

    def action_pawn(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # cr = pooler.get_db(cr.dbname).cursor()
        active_id = context.get('active_id')
        # Check status
        pawn = self.pool.get('pawn.order').browse(cr, uid, active_id)
        if pawn.state != 'draft':
            raise osv.except_osv(_('Error!'),
                                 _('Ticket need refresh before proceeding!'))
        # Check pawned amount
        if pawn.amount_pawned != sum([line.pawn_price_subtotal for line in pawn.order_line]):
            raise osv.except_osv(_('Error!'), _('Pawned amount must equal to sum of pawned subtotal'))
        # Check pawn item image
        self._check_pawn_item_image_first(cr, uid, pawn, context=context)
        # Write journal_id back to order
        wizard = self.browse(cr, uid, ids[0], context)
        self.pool.get('pawn.order').write(cr, uid, [active_id], {'journal_id': wizard.journal_id.id, 'date_due_ticket': wizard.date_due_ticket}, context=context)
        # Trigger workflow
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'pawn.order', active_id, 'order_pawn', cr)
        # Interest

        # Clear accrued interest

        # Close
        # cr.commit()
        # cr.close()
        return True


pawn_order_pawn()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
