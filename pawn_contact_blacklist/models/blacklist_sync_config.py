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

import xmlrpclib

from openerp.osv import osv, fields
from openerp.tools.translate import _

class BlacklistSyncConfig(osv.osv):
    _name = 'blacklist.sync.config'
    _description = 'Blacklist Sync Configuration'

    _columns = {
        'name': fields.char('Server Name', required=True),
        'url': fields.char('Odoo URL', required=True),
        'db_name': fields.char('Database Name', required=True),
        'username': fields.char('Username', required=True),
        'password': fields.char('Password', required=True, password=True),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': False
    }

    _sql_constraints = [
        ('unique_url', 'unique(url)', 'The URL must be unique!'),
    ]
    
    def test_connection(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context=context)

        try:
            # Connect to common service
            common = xmlrpclib.ServerProxy("{}/xmlrpc/common".format(config.url))
            uid_remote = common.login(config.db_name, config.username, config.password)

            if not uid_remote:
                raise osv.except_osv(_('Connection Failed'), _('Authentication failed. Please check credentials.'))
            
            print("Logged in with UID: {}".format(uid_remote))

        except Exception as e:
            raise osv.except_osv(_('Connection Logs'), _('Error: %s') % str(e))

BlacklistSyncConfig()