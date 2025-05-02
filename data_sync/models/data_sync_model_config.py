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

class data_sync_model_config(osv.osv):
    _name = 'data.sync.model.config'
    _description = 'Data Sync Model Configuration'

    _columns = {
        'model_id': fields.many2one('ir.model', 'Model', required=True),
        'auto_create_field_ids': fields.many2many(
            'ir.model.fields',
            'data_sync_model_auto_create_field_rel',
            'config_id', 'field_id',
            'Auto Create Fields',
        ),
        'keywords_field_ids': fields.many2many(
            'ir.model.fields',
            'data_sync_model_keywords_field_rel',
            'config_id', 'field_id',
            'Keywords Fields',
        ),
        'needed_field_ids': fields.many2many(
            'ir.model.fields',
            'data_sync_model_needed_field_rel',
            'config_id', 'field_id',
            'Needed Fields',
        ),
    }

    _sql_constraints = [
        ('model_uniq', 'unique(model_id)', 'The configuration model must be unique!')
    ]
    
    def action_compute_needed_fields(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for model_config in self.browse(cr, uid, ids, context=context):
            model_id = model_config.model_id.id
            model_obj = self.pool.get('ir.model')
            model_record = model_obj.browse(cr, uid, model_id, context=context)
            model_name = model_record.model
            obj = self.pool.get(model_name)
            fields_info = obj.fields_get(cr, uid, context=context)
            field_obj = self.pool.get('ir.model.fields')
            field_names = [
                name for name, attrs in fields_info.iteritems()
                if attrs.get('type') not in ('many2one', 'one2many', 'many2many', 'binary')
                and ('function' not in attrs or attrs.get('store', True))
            ]
            field_ids = field_obj.search(cr, uid, [
                ('model_id', '=', model_id),
                ('name', 'in', field_names),
            ], context=context)
            self.write(cr, uid, [model_config.id], {'needed_field_ids': [(6, 0, field_ids)]}, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'model_id' in vals:
            vals['keywords_field_ids'] = [(6, 0, [])]
            vals['auto_create_field_ids'] = [(6, 0, [])]
            vals['needed_field_ids'] = [(6, 0, [])]
        return super(data_sync_model_config, self).write(cr, uid, ids, vals, context=context)

data_sync_model_config()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: