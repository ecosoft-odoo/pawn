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
import xmlrpclib

class data_sync_server(osv.osv):
    _name = 'data.sync.server'
    _description = 'Data Sync Server'

    _columns = {
        'name': fields.char('Server Name', required=True),
        'server_url': fields.char('Server URL', required=True),
        'db_name': fields.char('Database Name', required=True),
        'username': fields.char('Username', required=True),
        'password': fields.char('Password', required=True),
        'active': fields.boolean('Active', help="If unchecked, this server will be ignored for sync."),
    }

    _defaults = {
        'active': True,
    }

    _sql_constraints = [
        ('server_url_unique', 'unique(server_url, db_name, username)', 'Server URL, Database and Username must be unique!')
    ]

    def test_connection(self, cr, uid, ids, context=None):
        """Function to test connection and login to server"""
        if context is None:
            context = {}
        for server in self.browse(cr, uid, ids, context=context):
            try:
                common = xmlrpclib.ServerProxy('{}/xmlrpc/common'.format(server.server_url))
                uid_remote = common.login(server.db_name, server.username, server.password)
                if not uid_remote:
                    raise osv.except_osv('Login Failed', 'Cannot authenticate to server: {}'.format(server.server_url))
                print("Logged in {} with UID: {}".format(server.server_url, uid_remote))
            except Exception as e:
                raise osv.except_osv('Connection Error', 'Failed to connect to server: {}\n\n{}'.format(server.server_url, str(e)))
        return True

data_sync_server()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: