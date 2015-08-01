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
import logging
import time

from openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class pawn_order(osv.osv):

    _inherit = 'pawn.order'

    def process_expired_order(self, cr, uid, context=None):
        """
        This process will check for pawn_order with state = 'pawn', then check whether it expired.
        If expired, set state = 'expire'
        """
        if context is None:
            context = {}
        now = fields.date.context_today(self, cr, uid, context=context)
        filters = [('state', '=', 'pawn'), ('date_due', '<', now)]
        ids = self.search(cr, uid, filters, context=context)
        try:
            if ids:
                self.order_expire(cr, uid, ids, context=context)
        except Exception:
            _logger.exception("Failed processing expired pawn ticket")

pawn_order()


class pawn_accrued_interest(osv.osv):

    _inherit = 'pawn.accrued.interest'

    def process_accrued_interest_move(self, cr, uid, context=None):
        """
        This process interest move as date arrived
        """
        if context is None:
            context = {}
        now = fields.date.context_today(self, cr, uid, context=context)
        filters = [('parent_state','=','pawn'), ('move_id', '=', False), ('interest_date', '<=', now)]
        ids = self.search(cr, uid, filters, context=context)
        try:
            if ids:
                self.create_interest_move(cr, uid, ids, context=context)
        except Exception:
            _logger.exception("Failed processing accrued interest table")

pawn_accrued_interest()


class pawn_actual_interest(osv.osv):

    _inherit = 'pawn.actual.interest'

    def process_actual_interest_move(self, cr, uid, context=None):
        """
        This process interest move as date arrived
        """
        if context is None:
            context = {}
        now = fields.date.context_today(self, cr, uid, context=context)
        filters = [('parent_state','in',('pawn', 'redeem')), ('move_id', '=', False), ('interest_date', '<=', now)]
        ids = self.search(cr, uid, filters, context=context)
        try:
            if ids:
                self.create_interest_move(cr, uid, ids, context=context)
        except Exception:
            _logger.exception("Failed processing actual interest table")

pawn_accrued_interest()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
