# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Ecosoft Co., Ltd. (http://ecosoft.co.th).
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

from openerp.osv import osv
from openerp.tools.translate import _

class pawn_order(osv.osv):
    _inherit = "pawn.order"

    def onchange_partner_id(self, cr, uid, ids, partner_id):
        res = super(pawn_order, self).onchange_partner_id(cr, uid, ids, partner_id)
        partner_obj = self.pool.get('res.partner')
        if not partner_id:
            return False
        partner = partner_obj.browse(cr, uid, partner_id)
        blacklist_obj = self.pool.get('blacklist.sync')
        blacklist_id = blacklist_obj.search(cr, uid, [('partner_id', '=', partner.id), ('state', '=', 'active')], limit=1)
        if blacklist_id and partner.blacklist_customer:
            blacklist = blacklist_obj.browse(cr, uid, blacklist_id[0])
            remark_summary = blacklist.remark_summary
            res['warning'] = {
                'title': 'Warning',
                'message': _('%s is blacklisted.\nReason: %s') % (partner.name, remark_summary or _('No reason provided'))
            }
        return res

pawn_order()