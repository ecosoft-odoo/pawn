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

from openerp.osv import osv, fields
from openerp.tools.translate import _

class pawn_order_pawn(osv.osv_memory):
    _inherit = "pawn.order.pawn"

    def _get_partner_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        if active_id:
            pawn = self.pool.get('pawn.order').browse(cr, uid, active_id, context=context)
            return pawn.partner_id and pawn.partner_id.id or False
        return False

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Customer', readonly=True),
    }

    _defaults = {
        'partner_id': _get_partner_id,
    }

    def action_pawn(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        blacklist_obj = self.pool.get('blacklist.sync')
        wizard = self.browse(cr, uid, ids[0], context)
        blacklist_ids = blacklist_obj.search(cr, uid, [('state', '=', 'active'),('partner_id', '=', wizard.partner_id.id)], context=context)
        if blacklist_ids:
            blacklist = blacklist_obj.browse(cr, uid, blacklist_ids[0], context=context)
            if blacklist.is_stolen:
                raise osv.except_osv(
                    _('UserError!'),
                    _('This asset is reported as stolen and cannot be used for transactions.')
                )
        return super(pawn_order_pawn, self).action_pawn(cr, uid, ids, context=context)

pawn_order_pawn()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: