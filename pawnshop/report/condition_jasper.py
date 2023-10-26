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


    def _check_pawn_order(self, cr, uid, ids, context=None):
        for report in self.browse(cr, uid, ids, context=context):
            if report.report_name == 'pawn.order.form':
                if context.get('active_ids', False):
                    for obj in self.pool.get('pawn.order').browse(cr, uid, context.get('active_ids')):
                        if (obj.state in ['draft']):
                            raise openerp.exceptions.Warning("Can't print form in %s state" % (obj.state, ))
        return True

    def _check_report_condition(self, cr, uid, ids, context=None):
        self._check_pawn_order(cr, uid, ids, context=context)

    def _report_content(self, cr, uid, ids, name, arg, context=None):
        self._check_report_condition(cr, uid, ids, context=context)
        return super(report_xml, self)._report_content(cr, uid, ids, name, arg, context=context)

    def _report_content_inv(self, cursor, user, id, name, value, arg, context=None):
        return super(report_xml, self)._report_content_inv(cursor, user, id, name, value, arg, context=context)

    _columns = {
        'report_sxw_content': fields.function(_report_content, fnct_inv=_report_content_inv, type='binary', string='SXW Content',),
        'report_rml_content': fields.function(_report_content, fnct_inv=_report_content_inv, type='binary', string='RML Content'),
    }
report_xml()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
