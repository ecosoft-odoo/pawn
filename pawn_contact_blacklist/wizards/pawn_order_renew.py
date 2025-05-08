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


class pawn_order_renew(osv.osv_memory):
    _inherit = "pawn.order.renew"
    _description = "Renew"

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

    def action_renew(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for wizard in self.browse(cr, uid, ids, context=context):
            partner = wizard.partner_id
            if partner and partner.blacklist_customer:
                raise osv.except_osv(
                    _('UserError!'),
                    _('%s is blacklisted.') % (partner.name)
                )
        return super(pawn_order_renew, self).action_renew(cr, uid, ids, context=context)
    
pawn_order_renew()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
