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
from openerp.osv import fields, osv
from openerp.service import web_services
import contextlib
import base64
import locale
import logging
import os
import platform
import sys
import thread
import threading
import time
import traceback
from cStringIO import StringIO
from openerp.tools.translate import _
import openerp.netsvc as netsvc
import openerp.pooler as pooler
import openerp.release as release
import openerp.sql_db as sql_db
import openerp.tools as tools
import openerp.modules
import openerp.exceptions
from openerp.service import http_server
from openerp import SUPERUSER_ID
import openerp


class report_xml(osv.osv):

    _inherit = 'ir.actions.report.xml'

    def _check_pawn_order(self, cr, uid, report, context=None):
        res = super(report_xml, self)._check_pawn_order(cr, uid, report, context=context)
        if report.report_name == 'lost.pawn.order.form':
            for obj in self.pool.get('pawn.order').browse(cr, uid, context.get('active_ids', []), context=context):
                if not obj.is_lost:
                    raise openerp.exceptions.Warning("Can't print form for non-lost pawn order")
        return res
    
report_xml()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
