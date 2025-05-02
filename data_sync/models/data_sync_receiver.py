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

class data_sync_receiver(osv.AbstractModel):
    _name = 'data.sync.receiver'
    _description = 'Data Sync Receiver'

    def resolve_search_keys(self, cr, uid, relation, keywords, auto_create_data=None, context=None):
        """Finds or creates a record for a many2one field based on keyword"""
        rel_obj = self.pool.get(relation)
        param = auto_create_data.get('param', {})
        # ใช้ keyword หา record
        domain = []  # base domain
        related_domain = []
        for key, value in keywords.items():
            if isinstance(value, dict) and 'keywords' in value:
                related_model = self.pool.get(value['model'])
                for k, v in value['keywords'].items():
                    related_domain.append((k, '=', v))
                related_id = related_model.search(cr, uid, related_domain, context=context, limit=1)
                if related_id:
                    domain.append((key, '=', related_id[0]))
                else:
                    return False
            else:
                domain.append((key, '=', value))
        print('domain', domain)
        ids = rel_obj.search(cr, uid, domain, limit=1)

        if ids:
            return ids[0]

        if param:
            new_vals = self.prepare_create_data_param(cr, uid, relation, param, context=context)
            return rel_obj.create(cr, uid, new_vals, context=context)
        else:
            raise osv.except_osv(
                'Error', 'Cannot find record in model {}'.format(relation)
            )

    def prepare_create_data_param(self, cr, uid, model, param, context=None):
        context = context or {}
        obj = self.pool.get(model)
        vals = {}

        # ข้อมูลทั่วไปใน 'data'
        vals.update(param.get('data', {}))

        # จัดการ many2one
        for field_name, field_info in param.get('many2one', {}).items():
            if 'keywords' in field_info:
                # resolve หรือสร้าง record หากไม่พบ
                rel_id = self.resolve_search_keys(
                    cr, uid, field_info['model'], field_info['keywords'], field_info.get('auto_create', {}), context
                )
                vals[field_name] = rel_id
        #จัดการ one2many
        for field_name, lines in param.get('one2many', {}).items():
            new_lines = []
            for line in lines:
                model = line.get('model')
                child_vals = self.prepare_create_data_param(cr, uid, model, line.get('param', {}), context=context)
                new_lines.append((0, 0, child_vals))
            vals[field_name] = new_lines

        return vals
    
    def prepare_write_data_param(self, cr, uid, model, param, context=None):
        context = context or {}
        obj = self.pool.get(model)
        vals = {}

        # ข้อมูลทั่วไปใน 'data'
        vals.update(param.get('data', {}))

        # จัดการ many2one
        for field_name, field_info in param.get('many2one', {}).items():
            if 'keywords' in field_info:
                # resolve หรือสร้าง record หากไม่พบ
                rel_id = self.resolve_search_keys(
                    cr, uid, field_info['model'], field_info['keywords'], field_info.get('auto_create', {}), context
                )
                vals[field_name] = rel_id
        #จัดการ one2many
        for field_name, lines in param.get('one2many', {}).items():
            write_line = []
            for line in lines:
                if line[0] == 1:
                    # write
                    rel_id = self.resolve_search_keys(
                        cr, uid, line[1]['model'], line[1]['keywords'], context
                    )
                    write_line.append([1, rel_id, line[2]])
                elif line[0] == 0:
                    # create
                    write_line.append([0, 0, line[2]])
                elif line[0] in [2, 4]:
                    rel_id = self.resolve_search_keys(
                        cr, uid, line[1]['model'], line[1]['keywords'], context
                    )
                    write_line.append([line[0], rel_id, False])
            vals[field_name] = write_line

        return vals

    def create_sync(self, cr, uid, vals, context=None):
        """Create data from the synced information"""
        context = context or {}
        context['sync'] = False
        model = vals.pop('model')
        obj = self.pool.get(model)
        param = vals.get('param', {})
        vals = self.prepare_create_data_param(cr, uid, model, param, context=context)
        print("Create Sync Vals:", vals)
        return obj.create(cr, uid, vals, context=context)

    def write_sync(self, cr, uid, vals, context=None):
        """Update data from the synced information"""
        context = context or {}
        context['sync'] = False
        model = vals.pop('model')
        obj = self.pool.get(model)
        param = vals.get('param', {})
        keywords = param.get('keywords', {})
        res_id = self.resolve_search_keys(
                    cr, uid, model, keywords, context
                )
        vals = self.prepare_write_data_param(cr, uid, model, param, context=context)
        print("Update Sync Vals:", vals)
        return obj.write(cr, uid, [res_id], vals, context=context)

    def unlink_sync(self, cr, uid, vals, context=None):
        """ลบข้อมูลจากข้อมูลที่ sync มา"""
        context = context or {}
        context['sync'] = False
        model = vals.pop('model')
        obj = self.pool.get(model)
        keywords = vals.get('keywords', {})
        res_id = self.resolve_search_keys(
                    cr, uid, model, keywords, context
                )
        return obj.unlink(cr, uid, [res_id], context=context)

    def check_server_ready(self, cr, uid, model, method='read', context=None):
        """เช็คว่า user นี้มีสิทธิ์ใช้งาน model และ method นั้นๆ หรือไม่"""
        if not self.pool.get(model):
            raise osv.except_osv('Error', 'Model {} not found.'.format(model))

        model_obj = self.pool.get(model)

        if method == 'create':
            has_access = model_obj.check_access_rights(cr, uid, 'create', raise_exception=False)
        elif method == 'write':
            has_access = model_obj.check_access_rights(cr, uid, 'write', raise_exception=False)
        elif method == 'unlink':
            has_access = model_obj.check_access_rights(cr, uid, 'unlink', raise_exception=False)
        else:
            has_access = model_obj.check_access_rights(cr, uid, 'read', raise_exception=False)

        if not has_access:
            raise osv.except_osv('Permission Error', 'No {} permission for model: {}'.format(method, model))

        return True
