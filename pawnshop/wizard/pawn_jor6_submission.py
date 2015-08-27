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
import time
from dateutil.relativedelta import relativedelta
from datetime import datetime


class pawn_jor6_submission(osv.osv_memory):

    _name = "pawn.jor6.submission"
    _description = "Submit Jor6"
    
    _columns = {
        'date': fields.date('    ', required=True)
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d')
    }

    def pawn_jor6_submit(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pawn_ids = context['active_ids']
        if pawn_ids:
            # Check all order are eligible, 1) date_expired < today, 2) no date_due yet
            valid_ids = self.pool.get('pawn.order').search(cr, uid, [('state','=','pawn'), ('date_expired','<', time.strftime('%Y-%m-%d')), ('date_due','=',False)], context=context)
            if pawn_ids != valid_ids and not set(pawn_ids).issubset(set(valid_ids)):
                raise osv.except_osv(_('Warning!'),
                                     _("""Some selection are not eligible for Jor6 Submission!\n
                                     Please filter with Jor6 Submission and try again."""))
            # Update submission date and new date_due
            wizard = self.browse(cr, uid, ids[0])
            pawn = self.pool.get('pawn.order').browse(cr, uid, pawn_ids[0], context=context)
            date_due = datetime.strptime(wizard.date[:10], '%Y-%m-%d') + relativedelta(days=pawn.rule_id.length_day or 0.0)
            # Update new dates
            self.pool.get('pawn.order').write(cr, uid, pawn_ids, {'date_jor6': wizard.date,
                                                                  'date_due': date_due.strftime('%Y-%m-%d')})
        return {'type': 'ir.actions.act_window_close'}

pawn_jor6_submission()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
