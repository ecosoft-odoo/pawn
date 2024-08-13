# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2014 OpenERP S.A. <http://www.openerp.com>
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
import openerp


class report_xml(osv.osv):

    _inherit = 'ir.actions.report.xml'

    def _check_pawn_order(self, cr, uid, ids, context=None):
        # Status of pawn order can not print form
        pw_state = {
            'pawn.order.form.new': ['draft'],
            'redeem.order.form.new': ['draft', 'pawn', 'expire', 'cancel'],
        }
        # --
        for report in self.browse(cr, uid, ids, context=context):
            if report.report_name in pw_state.keys():
                for obj in self.pool.get('pawn.order').browse(cr, uid, context.get('active_ids', []), context=context):
                    if (obj.state in pw_state[report.report_name]):
                        raise openerp.exceptions.Warning("Can't print form in %s state" % (obj.state, ))
        return True

report_xml()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
