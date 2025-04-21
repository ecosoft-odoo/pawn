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


class pawn_expire_final(osv.osv_memory):

    _name = "pawn.expire.final"
    _description = "Finalize Expired Ticket"

    _columns = {
        'run_background': fields.boolean('Run Background', help='Run background to expire tickets'),
    }

    _defaults = {
        'run_background': True,
    }

    def pawn_expire_final(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pawn_ids = context['active_ids']
        if pawn_ids:
            PawnOrder = self.pool.get('pawn.order')
            # Check all order are eligible, 1) date_expired < today, 2) no date_due yet
            valid_ids = PawnOrder.search(cr, uid, [('ready_to_expire', '=', True), ('state', '=', 'pawn')], context=context)
            if pawn_ids != valid_ids and not set(pawn_ids).issubset(set(valid_ids)):
                raise osv.except_osv(_('Warning!'),
                                     _("""Some selection are not eligible to finalize expired ticket"""))
            # Check extended order
            PawnOrder._check_order_extend(cr, uid, pawn_ids, context=context)
            # --
            wizard = self.browse(cr, uid, ids, context=context)[0]
            if wizard.run_background:
                PawnOrder.write(cr, uid, pawn_ids, {
                    'run_background': wizard.run_background,
                }, context=context)
            else:
                if PawnOrder.search(cr, uid, [('id', 'in', pawn_ids), ('run_background', '=', True)], context=context):
                    raise osv.except_osv(_('Warning!'), _("""Please select tickets not run as background"""))
                # expire it.
                PawnOrder.order_expire(cr, uid, pawn_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}


pawn_expire_final()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
