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

class pawn_undo_cancel(osv.osv_memory):

    def _validate_secret_key(self, cr, uid, pawn_shop, secret_key, context=None):
        # If there is no key, always ok.
        if not secret_key and not pawn_shop.secret_key and not pawn_shop.secret_key2:
            return True
        else:
            keys = []
            if pawn_shop.secret_key:
                keys.append(pawn_shop.secret_key)
            if pawn_shop.secret_key2:
                keys.append(pawn_shop.secret_key2)
            if secret_key in keys:
                return True
            else:
                raise osv.except_osv(_('Invalid Key!'), _("You need to provide a valid shop's secret key for this action!"))
            return False

    _name = "pawn.undo.cancel"
    _description = "Undo/Cancel"
    _columns = {
        'secret_key': fields.char('Secret Key'),
    }

    def action_execute(self, cr, uid, ids, context=None):
        pawn_obj = self.pool.get('pawn.order')
        wizard = self.browse(cr, uid, ids[0], context)
        action_type = context.get('action_type', False)
        active_id = context.get('active_id', False)
        pawn = pawn_obj.browse(cr, uid, active_id, context=context)
        # Check Password
        self._validate_secret_key(cr, uid, pawn.pawn_shop_id, wizard.secret_key, context=context)
        # Based on action, do the undo/cancel
        if action_type == 'order_cancel':
            self.pool.get('pawn.order').order_cancel(cr, uid, [active_id], context=context)
            # Set due date = False
            pawn_obj.write(cr, uid, [active_id], {'date_due_ticket': False}, context=context)
        if action_type == 'action_undo_pay_interest':
            self.pool.get('pawn.order').action_undo_pay_interest(cr, uid, [active_id], context=context)
        if action_type == 'action_undo_redeem':
            self.pool.get('pawn.order').action_undo_redeem(cr, uid, [active_id], context=context)
        return True

pawn_undo_cancel()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
