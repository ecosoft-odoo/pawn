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

from openerp.osv import osv
import xmlrpclib

import logging
_logger = logging.getLogger(__name__)

class data_sync_sender(osv.AbstractModel):
    _name = 'data.sync.sender'
    _description = 'Data Sync Sender'

    def _get_server_list(self, cr, uid, context=None):
        context = context or {}
        cr.execute("SELECT id, name, server_url, db_name, username, password FROM data_sync_server WHERE active = TRUE")
        servers = cr.dictfetchall()
        return servers
    
    def _get_keywords(self, cr, uid, model, context=None):
        context = context or {}
        sync_model_obj = self.pool.get('data.sync.model.config')
        sync_model_ids = sync_model_obj.search(cr, uid, [('model_id', '=', model)])
        if not sync_model_ids:
            return False
        keys = sync_model_obj.browse(cr, uid, sync_model_ids[0]).keywords_field_ids
        return list(keys)
    
    def _get_auto_create(self, cr, uid, model, context=None):
        context = context or {}
        sync_model_obj = self.pool.get('data.sync.model.config')
        sync_model_ids = sync_model_obj.search(cr, uid, [('model_id', '=', model)])
        if not sync_model_ids:
            return []

        sync_model = sync_model_obj.browse(cr, uid, sync_model_ids[0], context=context)
        field_names = [f.name for f in sync_model.auto_create_field_ids]
        return field_names
    
    def _get_to_fetch_field(self, cr, uid, model, context=None):
        """ Get fields to fetch from the model """
        context = context or {}
        sync_model_obj = self.pool.get('data.sync.model.config')
        sync_model_ids = sync_model_obj.search(cr, uid, [('model_id', '=', model)])
        if not sync_model_ids:
            return []
        sync_model = sync_model_obj.browse(cr, uid, sync_model_ids[0], context=context)
        f_to_fetch = set(map(
            lambda f: f.name, 
            sync_model.needed_field_ids + sync_model.keywords_field_ids + sync_model.auto_create_field_ids
            )
        )
        return list(f_to_fetch)
        
    
    def _prepare_search_key(self, cr, uid, relation, ids, context=None):
        """ Prepare search key for relation field """
        context = context or {}
        if not ids:
            return False
        related_record = self.pool.get(relation).browse(cr, uid, ids)
        keys = self._get_keywords(cr, uid, relation, context=context)
        if not keys:
            return {
                'keywords': {
                    'name': related_record.name,
                },
                'model': relation,
            }
        key = {}
        for k in keys:
            field_name = k.name
            value = getattr(related_record, field_name, False)
            if hasattr(value, '_table'):
                record_id = getattr(value, 'id', False)
                sub_relation = value._name
                key[field_name] = self._prepare_search_key(cr, uid, sub_relation, record_id, context=context)
                key[field_name]['model'] = sub_relation
            else:
                key[field_name] = value
        return {
            'keywords': key,
            'model': relation,
        }

    def _prepare_create_one2many(self, cr, uid, model, relation_field, value, context=None):
        """ Prepare one2many field """
        context = context or {}
        res = []
        if not value or not isinstance(value, list):
            return res
        for sub in value:
            if isinstance(sub, tuple) and len(sub) == 3:
                _, _, sub_val = sub
                if relation_field and relation_field in sub_val:
                    sub_val.pop(relation_field)
                vals = self.prepare_create_sync_vals(cr, uid, model, sub_val, context=context)
                res.append(vals)
        return res

    def _prepare_many2many(self, cr, uid, relation, value, context=None):
        """ Prepare many2many field """
        context = context or {}
        res = {'keywords': 'name', 'vals': []}
        if not value or not isinstance(value, list):
            return res

        keys = self._get_keywords(cr, uid, relation, context=context)
        if keys:
            keyword_list = [k.name for k in keys]
            res['keywords'] = keyword_list

        for related_id in value:
            related_record = self.pool.get(relation).browse(cr, uid, related_id)
            if related_record:
                data = {}
                for key in keyword_list:
                    data[key] = getattr(related_record, key, False)
                res['vals'].append(data)
        return res
    
    def prepare_create_sync_vals(self, cr, uid, model, vals, context=None):
        """ Prepare vals to sync across servers safely """
        if context is None:
            context = {}

        res = {
            'model': model,
            'param': {
                'data': {},
                'many2one': {},
                'one2many': {},
                'many2many': {},
            }
            
        }
        model_obj = self.pool.get(model)
        # Get Fields to fetch
        fetch_field = self._get_to_fetch_field(cr, uid, model,context=context)
        # Get Fields Info
        fields_info = model_obj.fields_get(cr, uid, fetch_field, context=context)
        # Get Auto Create Fields
        fields_auto_create = self._get_auto_create(cr, uid, model, context=context)

        for field_name, value in vals.items():
            info = fields_info.get(field_name, False)
            if not info:
                # Skip if field is not in fetch_field and not in fields_info
                continue
            field_type = info.get('type', False)
            relation = info.get('relation', False)
            if not relation:
                res['param']['data'][field_name] = value
                continue
            if field_type == 'many2one':
                res['param']['many2one'][field_name] = self._prepare_search_key(cr, uid, relation, value, context=context)
                if field_name in fields_auto_create:
                    sub_obj = self.pool.get(relation)
                    sub_vals = sub_obj.copy_data(cr, uid, value, context=context)
                    sub_vals = self.prepare_create_sync_vals(cr, uid, relation, sub_vals, context=context)
                    res['param']['many2one'][field_name]['auto_create'] = sub_vals
            elif field_type == 'one2many':
                relation_field = info.get('relation_field')
                res['param']['one2many'][field_name] = self._prepare_create_one2many(cr, uid, relation, relation_field, value, context=context)
        return res
    
    def prepare_write_sync_vals(self, cr, uid, res_id, model, vals, context=None):
        """ Prepare vals to sync across servers safely """
        if context is None:
            context = {}
        res = {
            'model': model,
            'param': {
                'data': {},
                'many2one': {},
                'one2many': {},
                'many2many': {},
                'keywords': {},
            }
        }
        model_obj = self.pool.get(model)
        fetch_field = vals.keys()
        fields_info = model_obj.fields_get(cr, uid, fetch_field, context=context)
        fields_auto_create = self._get_auto_create(cr, uid, model, context=context)
        res['param'].update(self._prepare_search_key(cr, uid, model, res_id, context=context))

        for field_name, value in vals.items():
            info = fields_info.get(field_name)
            if not info:
                # Skip if field is not in fetch_field and not in fields_info
                continue
            field_type = info.get('type', False)
            relation = info.get('relation', False)
            if not relation:
                res['param']['data'][field_name] = value
                continue
            if field_type == 'many2one':
                res['param']['many2one'][field_name] = self._prepare_search_key(cr, uid, relation, value, context=context)
                if field_name in fields_auto_create:
                    sub_obj = self.pool.get(relation)
                    sub_vals = sub_obj.copy_data(cr, uid, value, context=context)
                    sub_vals = self.prepare_create_sync_vals(cr, uid, relation, sub_vals, context=context)
                    res['param']['many2one'][field_name]['auto_create'] = sub_vals
            elif field_type == 'one2many':
                key_list = []
                relation_model = info.get('relation')
                for vk in value:
                    if vk[0] == 1:
                        line_id = vk[1]
                        line_val = vk[2]
                        keys_val = [1, self._prepare_search_key(cr, uid, relation_model, line_id, context=context), line_val]
                    elif vk[0] == 0:
                        line_val = vk[2]
                        keys_val = [0, 0, line_val]
                    elif vk[0] in [2, 4] :
                        line_id = vk[1]
                        keys_val = [vk[0], self._prepare_search_key(cr, uid, relation_model, line_id, context=context)]
                    key_list.append(keys_val)
                res['param']['one2many'][field_name] = key_list
        return res

    def _send_data(self, cr, uid, servers, method, vals, context=None):
        context = context or {}
        for server in servers:
            url = server['server_url']
            db_name = server['db_name']
            username = server['username']
            password = server['password']
            try:
                common = xmlrpclib.ServerProxy('{}/xmlrpc/common'.format(url))
                uid_remote = common.login(db_name, username, password)
                if not uid_remote:
                    raise Exception('Login failed on server {}'.format(url))
                models = xmlrpclib.ServerProxy('{}/xmlrpc/object'.format(url))
                models.execute(db_name, uid_remote, password, 'data.sync.receiver', method, vals, context)

            except Exception as e:
                raise osv.except_osv('Sync Error', 'Failed to sync to server {}: {}'.format(url, str(e)))
        
    def _check_all_servers_ready(self, cr, uid, model, servers, method, context=None):
        """Check if all servers are ready to receive data before sending"""
        context = context or {}
        for server in servers:
            url = server['server_url']
            db_name = server['db_name']
            username = server['username']
            password = server['password']
            try:
                common = xmlrpclib.ServerProxy('{}/xmlrpc/common'.format(url))
                uid_remote = common.login(db_name, username, password)

                models = xmlrpclib.ServerProxy('{}/xmlrpc/object'.format(url))
                is_ready = models.execute(
                    db_name,
                    uid_remote,
                    password,
                    'data.sync.receiver',
                    'check_server_ready',
                    model,
                    method,
                    context or {}
                )
                if not is_ready:
                    raise Exception('Server {} not ready for model {} with method {}'.format(url, model, method))
            except osv.except_osv as e:
                raise
            except Exception as e:
                raise osv.except_osv('Sync Error', 'Server {} not ready: {}'.format(url, str(e)))

    # ------ ฟังก์ชัน CRUD  ------

    def sync_create(self, cr, uid, model, vals, context=None):
        context = context or {}
        servers = self._get_server_list(cr, uid, context=context)
        self._check_all_servers_ready(cr, uid, model, servers, 'create', context=context)
        _logger.info("All servers already to receive data")
        vals = self.prepare_create_sync_vals(cr, uid, model, vals, context=context)
        _logger.info("Data sync create operation initiated for model: %s", model)
        self._send_data(cr, uid, servers, 'create_sync', vals, context=context)

    def sync_write(self, cr, uid, res_id, model, vals, context=None):
        context = context or {}
        servers = self._get_server_list(cr, uid, context=context)
        self._check_all_servers_ready(cr, uid, model, servers, 'write', context=context)
        _logger.info("All servers already to receive data")
        vals = self.prepare_write_sync_vals(cr, uid, res_id, model, vals, context=context)
        _logger.info("Data sync update operation initiated for model: %s", model)
        self._send_data(cr, uid, servers, 'write_sync', vals, context=context)

    def sync_unlink(self, cr, uid, res_id, model, context=None):
        context = context or {}
        servers = self._get_server_list(cr, uid, context=context)
        self._check_all_servers_ready(cr, uid, model, servers, 'unlink', context=context)
        vals = self._prepare_search_key(cr, uid, model, res_id, context=context)
        self._send_data(cr, uid, servers, 'unlink_sync', vals, context=context)
