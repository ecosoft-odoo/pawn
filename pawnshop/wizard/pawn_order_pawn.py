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
    }
    _defaults = {
        'journal_id': _get_journal,
        'parent_id': _get_parent_id,
        'amount': _get_amount
    }

    def action_pawn(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        cr = pooler.get_db(cr.dbname).cursor()
        active_id = context.get('active_id')
        # Check status
        pawn = self.pool.get('pawn.order').browse(cr, uid, active_id)
        if pawn.state != 'draft':
            raise osv.except_osv(_('Error!'),
                                 _('Ticket need refresh before proceeding!'))
        # Write journal_id back to order
        wizard = self.browse(cr, uid, ids[0], context)
        self.pool.get('pawn.order').write(cr, uid, [active_id], {'journal_id': wizard.journal_id.id}, context=context)
        # Trigger workflow
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'pawn.order', active_id, 'order_pawn', cr)
        # Interest

        # Clear accrued interest

        # Close
        cr.commit()
        cr.close()
        return True

pawn_order_pawn()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
