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
from datetime import datetime
from openerp.osv import osv, fields
from openerp.tools.translate import _

STATE_SELECTION = [
    ('draft', 'Draft'),
    ('active', 'Blacklisted'),
    ('inactive', 'Unblacklisted'),
]

class BlacklistSync(osv.osv):
    _name = 'blacklist.sync'
    _description = "Customer Blacklist"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'banned_date desc'

    _columns = {
        'name': fields.related('partner_id', 'name', type='char', string='Name', readonly=True, store=True),
        'card_number': fields.related('partner_id', 'card_number', type='char', string='ID Number', readonly=True, store=True),
        'partner_id': fields.many2one('res.partner', 'Customer (for change)', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'),
        'pawnshop': fields.char('Pawnshop', readonly=True, track_visibility='onchange'),
        'unbanned_pawnshop': fields.char('Unbanned Pawnshop', readonly=True, track_visibility='onchange'),
        'banned_date': fields.datetime('Blacklist Date', readonly=True),
        'unbanned_date': fields.date('Unbanned Date', readonly=True),
        'suspicious_asset': fields.text('Suspicious Asset', required=True, size=85, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'),
        'price': fields.float('Price', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'),
        'suspicious_asset_image': fields.binary('Suspicious Asset Image', readonly=True, states={'draft': [('readonly', False)]}),
        'suspicious_asset_image_date': fields.datetime('Date of Suspicious Asset Image', readonly=True),
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True, track_visibility='onchange'),
        'index': fields.integer('Index'),
        'active': fields.boolean('Active'),
    }

    def _get_branch(self, cr, uid, context=None):
        context = context or {}
        shop_obj = self.pool.get('pawn.shop')
        shop_ids = shop_obj.search(cr, uid, [])
        for branch in shop_obj.browse(cr, uid, [shop_ids[0]], context=context):
            branch_name = branch.name
        return shop_ids and branch_name or False

    _defaults = {
        'active': True,
        'state': 'draft',
        'pawnshop' : _get_branch
    }

    def _login_to_remote(self, cr, uid, server, context=None):
        context = context or {}
        url, db_name, username, password = server
        common = xmlrpclib.ServerProxy("{}/xmlrpc/common".format(url))
        uid_remote = common.login(db_name, username, password)
        if not uid_remote:
            raise osv.except_osv(_('Connection Failed'), _('Authentication failed. Please check credentials.'))
        print("Logged in with UID: {}".format(uid_remote))
        return uid_remote
    
    def get_blacklist_remote(self, cr, uid, ids, server, uid_remote, model, context=None):
        context = context or {}
        url, db_name, username, password = server
        models = xmlrpclib.ServerProxy("{}/xmlrpc/object".format(url))
        for obj in self.browse(cr, uid, ids, context=context):
            domain = [
                ('card_number', '=', obj.card_number),
                ('state', '!=', 'draft'),
                ('index', '=', obj.index)
            ]
            blacklist_ids = models.execute(db_name, uid_remote, password, model, 'search', domain)
        return blacklist_ids
    
    def _get_last_blacklist_info_remote(self, cr, uid, server, uid_remote, blacklist_data, context=None):
        context = context or {}
        url, db_name, username, password = server
        if uid_remote:
            try:
                models = xmlrpclib.ServerProxy("{}/xmlrpc/object".format(url))
                record_data = models.execute(db_name, uid_remote, password, 'blacklist.sync', 'get_last_blacklist_info', blacklist_data, context)
                return record_data
            except Exception as e:
                raise osv.except_osv(_('Remote Sync Error!'), _('Unexpected Error: %s') % str(e))
    
    def _get_search_keys(self, cr, uid, model, context=None):
        """Return list of fields to use for searching"""
        context = context or {}
        key = ['name']
        if model == 'res.partner':
            key = ['name', 'card_number']
        return key
    
    def _update_blacklist_remote(self, cr, uid, ids, server, uid_remote, vals, context=None):
        context = context or {}
        url, db_name, username, password = server
        context['write_remote'] = False
        try:
            if not uid_remote:
                raise osv.except_osv(_('UserError!'), _('Remote user ID (uid_remote) is missing. Please verify your configuration.'))
            models = xmlrpclib.ServerProxy("{}/xmlrpc/object".format(url))
            models.execute(db_name, uid_remote, password, 'blacklist.sync', 'write', ids, vals, context)
        except Exception as e:
            raise osv.except_osv(_('Remote Sync Error!'), _('Unexpected Error: %s') % str(e))
    
    def _unlink_blacklist_remote(self, cr, uid, ids, server, uid_remote, context=None):
        context = context or {}
        url, db_name, username, password = server
        context['unlink_remote'] = False
        try:
            if not uid_remote:
                raise osv.except_osv(_('UserError!'), _('Remote user ID (uid_remote) is missing. Please verify your configuration.'))
            models = xmlrpclib.ServerProxy("{}/xmlrpc/object".format(url))
            models.execute(db_name, uid_remote, password, 'blacklist.sync', 'unlink', ids, context)
        except Exception as e:
            raise osv.except_osv(_('Remote Sync Error!'), _('Unexpected Error: %s') % str(e))

    def _create_blacklist_remote(self, cr, uid, server, uid_remote, blacklist_to_fetch, customer_to_fetch, context=None):
        context = context or {}
        url, db_name, username, password = server
        context['bypass_imagetime'] = True
        try:
            if not uid_remote:
                raise osv.except_osv(_('UserError!'), _('Remote user ID (uid_remote) is missing. Please verify your configuration.'))
            models = xmlrpclib.ServerProxy("{}/xmlrpc/object".format(url))
            models.execute(db_name, uid_remote, password, 'blacklist.sync', 'create_blacklist', blacklist_to_fetch, customer_to_fetch, context)
        except Exception as e:
            raise osv.except_osv(_('Remote Sync Error!'), _('Unexpected Error: %s') % str(e))
    
    def inactive_balcklist_remote(self, cr, uid, ids, server, uid_remote, context=None):
        context = context or {}
        url, db_name, username, password = server
        if uid_remote:
            try:
                models = xmlrpclib.ServerProxy("{}/xmlrpc/object".format(url))
                models.execute(db_name, uid_remote, password, 'blacklist.sync', 'inactive_balcklist', ids, context)
            except Exception as e:
                raise osv.except_osv(_('Remote Sync Error!'), _('Unexpected Error: %s') % str(e))
            
    def _get_customer(self, cr, uid, ids, context=None):
        context = context or {}
        partner_obj = self.pool.get('res.partner')
        for obj in self.browse(cr, uid, ids, context=context):
            partner_ids = partner_obj.search(cr, uid, [
                ('name', '=', obj.name),
                ('card_number', '=', obj.card_number)
            ], context=context)
        return partner_ids
    
    def get_last_blacklist_info(self, cr, uid, blacklist_data, context=None):
        context = context or {}
        blacklist_obj = self.pool.get('blacklist.sync')
        record_data = {'index': 0}
        blacklist_ids = blacklist_obj.search(
                    cr, uid,
                    [
                        ('name', '=', blacklist_data['name']),
                        ('card_number', '=', blacklist_data['card_number']),
                        ('state', '!=', 'draft')
                    ],
                    order='banned_date desc',
                    limit=1,
                    context=context
                )
        if blacklist_ids:
            record_data = blacklist_obj.read(cr, uid, blacklist_ids, ['index', 'state'], context=context)[0]

        return record_data
    
    # def check_duplicate(self, cr, uid, ids, context=None):
    #     context = context or {}
    #     blacklist_obj = self.pool.get('blacklist.sync')
    #     for obj in self.browse(cr, uid, ids, context=context):
    #         blacklist_ids = blacklist_obj.search(cr, uid, [
    #             ('card_number', '=', obj.card_number),
    #             ('state', '=', 'active'),
    #         ], context=context)
    #         if not blacklist_ids:
    #             return False
    #     return True
    
    def get_ignore_fields_to_create_fetch(self, cr, uid, model, context=None):
        ignore_fields = ['create_uid', 'write_uid']
        return ignore_fields
    
    def get_needed_fields_to_create_fetch(self, cr, uid, model, context=None):
        needed_fields = []
        if model == 'blacklist.sync':
            needed_fields.extend(['partner_id'])
        return needed_fields
    
    def batch_to_create_fetch(self, cr, uid, ids, model, context=None):
        context = context or {}
        objs = self.pool.get(model)
        
        fields_info = objs.fields_get(cr, uid, context=context)
        ignore_fields = self.get_ignore_fields_to_create_fetch(cr, uid, model, context=context)
        needed_fields = self.get_needed_fields_to_create_fetch(cr, uid, model, context=context)
        ignore_fields.extend([
            field_name for field_name, field_attrs in fields_info.items()
            if field_attrs.get('type') in ['many2one', 'one2many', 'many2many'] 
            and not field_attrs.get('required')
            and field_name not in needed_fields
        ])
        batch_to_fetch = {
            'vals': {},
            'many2one': {},
            'one2many': {},
            'many2many': {}
        }
        for obj in objs.browse(cr, uid, ids, context=context):
            for field, attrs in fields_info.items():
                record = getattr(obj, field, False)
                if field in ignore_fields:
                    continue
                field_type = attrs.get('type')
                if field_type == 'many2one':
                    relation = attrs.get('relation')
                    keys = self._get_search_keys(cr, uid, relation, context)
                    field_objs = self.pool.get(relation)
                    key_value = field_objs.read(cr, uid, [record.id], keys, context=context)[0]
                    key_value.pop('id')
                    search_info = {
                            'model': relation,
                            'keys': key_value
                        }
                    batch_to_fetch[field_type][field] = search_info
                elif field_type in ('one2many', 'many2many'):
                    batch_to_fetch[field_type][field] = attrs.get('relation')
                else:
                    batch_to_fetch['vals'][field] = record

        return batch_to_fetch
    
    def search_many2one_data(self, cr, uid, search_data, context=None):
        context = context or {}
        vals = {}
        for field, info in search_data.items():
            keys = info.get('keys', {})
            model = info.get('model')
            
            domain = [(k, '=', v) for k, v in keys.items()]
            
            obj = self.pool.get(model)
            ids = obj.search(cr, uid, domain, context=context)
            if ids:
                vals[field] = ids[0]
            else:
                vals[field] = False 
        return vals
    
    def create_blacklist(self, cr, uid, blacklist_to_fetch, customer_to_fetch, context=None):
        context = context or {}
        blacklist_obj = self.pool.get('blacklist.sync')
        partner_obj = self.pool.get('res.partner')

        blacklist_vals = blacklist_to_fetch.get('vals')
        customer_vals = customer_to_fetch.get('vals')
        blacklist_many2one_info = blacklist_to_fetch.get('many2one')
        customer_many2one_info = customer_to_fetch.get('many2one')

        blacklist_many2one_vals = self.search_many2one_data(cr, uid, blacklist_many2one_info, context=context)
        blacklist_vals.update(blacklist_many2one_vals)
        partner_id = blacklist_vals.get('partner_id')

        if not partner_id:
            customer_many2one_vals = self.search_many2one_data(cr, uid, customer_many2one_info, context=context)
            customer_vals.update(customer_many2one_vals)
            partner_id = partner_obj.create(cr, uid, customer_vals, context=context)
            blacklist_vals['partner_id'] = partner_id
            blacklist_obj.create(cr, uid, blacklist_vals, context=context)
        else: 
            blacklist_obj.create(cr, uid, blacklist_vals, context=context)       
            partner_obj.write(cr, uid, partner_id, {'blacklist_customer': True}, context=context)
        return True
    
    def inactive_balcklist(self, cr, uid, ids, context=None):
        context = context or {}
        partner_obj = self.pool.get('res.partner')
        for blacklist in self.browse(cr, uid, ids, context=context):
            partner_id =  blacklist.partner_id.id
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            branch  = self._get_branch(cr, uid, context=context)
            self.write(cr, uid, [blacklist.id], {'state': 'inactive','unbanned_date': now, 'unbanned_pawnshop': branch}, context=context)
            partner_obj.write(cr, uid, partner_id, {'blacklist_customer': False}, context=context)
        return True
         
    def action_active(self, cr, uid, ids, context=None):
        context = context or {}
        context['write_remote'] = False
        partner_obj = self.pool.get('res.partner')
        try:
            for blacklist in self.browse(cr, uid, ids, context=context):
                customer = self._get_customer(cr, uid, [blacklist.id], context=context)
                blacklist_data = {'name': blacklist.name, 'card_number': blacklist.card_number}
                l_blacklist_info = self.get_last_blacklist_info(cr, uid, blacklist_data, context=context)
                if not customer:
                    raise osv.except_osv(_('UserError!'), _('Customer not found.'))
                if l_blacklist_info.get('state', False) == 'active':
                    raise osv.except_osv(_('UserError!'), _('This customer is already blacklisted.'))
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                next_index = l_blacklist_info.get('index', 0) + 1
                self.write(cr, uid, [blacklist.id], {'state': 'active','banned_date': now,'index': next_index}, context=context)
                partner_obj.write(cr, uid, customer, {'blacklist_customer': True}, context=context)
                blacklist_to_fetch = self.batch_to_create_fetch(cr, uid, [blacklist.id], 'blacklist.sync', context=context)
                customer_to_fetch = self.batch_to_create_fetch(cr, uid, customer, 'res.partner', context=context)
                cr.execute("SELECT url, db_name, username, password FROM blacklist_sync_config WHERE active = TRUE")
                servers = cr.fetchall()
                for server in servers:
                    uid_remote = self._login_to_remote(cr, uid, server, context=context)
                    l_blacklist_info_remote = self._get_last_blacklist_info_remote(cr, uid, server, uid_remote, blacklist_data, context=context)
                    if l_blacklist_info_remote.get('state', False) == 'active':
                        raise osv.except_osv(_('UserError!'), _('This customer is already blacklisted on another Pawnshop'))
                    self._create_blacklist_remote(cr, uid, server, uid_remote, blacklist_to_fetch, customer_to_fetch, context=context)
        except osv.except_osv:
            raise
        except Exception as e:
            raise osv.except_osv(_('Error!'), _('Unexpected Error: %s') % str(e))
        
    def action_inactive(self, cr, uid, ids, context=None):
        context = context or {}
        context['write_remote'] = False
        try:
            for blacklist in self.browse(cr, uid, ids, context=context):
                self.inactive_balcklist(cr, uid, [blacklist.id], context=context)
                cr.execute("SELECT url, db_name, username, password FROM blacklist_sync_config WHERE active = TRUE")
                servers = cr.fetchall()
                for server in servers:
                    uid_remote = self._login_to_remote(cr, uid, server, context=context)
                    if uid_remote:
                        blacklist_ids = self.get_blacklist_remote(cr, uid, [blacklist.id], server, uid_remote, 'blacklist.sync', context=context)
                        self.inactive_balcklist_remote(cr, uid, blacklist_ids, server, uid_remote, context=context)
        except osv.except_osv:
            raise
        except Exception as e:
            raise osv.except_osv(_('Error!'), _('Unexpected Error: %s') % str(e))
        
    def create(self, cr, uid, vals, context=None):
        context = context or {}
        if vals.get('suspicious_asset_image', False) and not context.get('bypass_imagetime', False):
            vals['suspicious_asset_image_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return super(BlacklistSync, self).create(cr, uid, vals, context=context)
        
    def write(self, cr, uid, ids, vals, context=None):
        context = context or {}
        if vals.get('suspicious_asset_image', False) and not vals.get('suspicious_asset_image_date', False):
            vals['suspicious_asset_image_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if context.get('write_remote', True):
            try:
                for blacklist in self.browse(cr, uid, ids, context=context):
                    cr.execute("SELECT url, db_name, username, password FROM blacklist_sync_config WHERE active = TRUE")
                    servers = cr.fetchall()
                    for server in servers:
                        uid_remote = self._login_to_remote(cr, uid, server, context=context)
                        if uid_remote:
                            blacklist_ids = self.get_blacklist_remote(cr, uid, [blacklist.id], server, uid_remote, 'blacklist.sync', context=context)
                            self._update_blacklist_remote(cr, uid, blacklist_ids, server, uid_remote, vals, context=context)
            except osv.except_osv:
                raise
            except Exception as e:
                raise osv.except_osv(_('Error!'), _('Unexpected Error: %s') % str(e))
        return super(BlacklistSync, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        context = context or {}
        for blacklist in self.browse(cr, uid, ids, context=context):
            if blacklist.state == 'active':
                raise osv.except_osv(
                    _('Error!'),
                    _('Cannot delete history in active state.')
                )
            elif blacklist.state == 'inactive' and context.get('unlink_remote', True):
                try:
                    cr.execute("SELECT url, db_name, username, password FROM blacklist_sync_config WHERE active = TRUE")
                    servers = cr.fetchall()
                    for server in servers:
                        uid_remote = self._login_to_remote(cr, uid, server, context=context)
                        if uid_remote:
                            blacklist_ids = self.get_blacklist_remote(cr, uid, [blacklist.id], server, uid_remote, 'blacklist.sync', context=context)
                            self._unlink_blacklist_remote(cr, uid, blacklist_ids, server, uid_remote, context=context)
                except osv.except_osv:
                        raise
                except Exception as e:
                    raise osv.except_osv(_('Error!'), _('Unexpected Error: %s') % str(e))
        return super(BlacklistSync, self).unlink(cr, uid, ids, context=context)

BlacklistSync()
