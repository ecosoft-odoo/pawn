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
from openerp.osv import fields, osv
from openerp.tools.translate import _


class update_partner_fingerprint(osv.osv_memory):
    _name = 'update.partner.fingerprint'
    _description = 'Update Partner Fingerprint'

    _columns = {
        'fingerprint': fields.binary('Fingerprint', required=True),
        'secret_key': fields.char('Secret Key', required=True),
    }

    def view_init(self, cr , uid , fields_list, context=None):
        if context is None:
            context = {}
        active_model = context.get('active_model', '')
        active_ids = context.get('active_ids', [])
        if active_model != 'res.partner':
            raise osv.except_osv(_('Error!'), _('This action use for update fingerprint on customer only.'))
        if not active_ids:
            raise osv.except_osv(_('Error!'), _('Please select at least 1 customer to update fingerprint.'))
        if len(active_ids) > 1:
            raise osv.except_osv(_('Error!'), _('Multiple customer not allowed to update fingerprint.'))
        return super(update_partner_fingerprint, self).view_init(cr , uid , fields_list, context=context)

    def _validate_secret_key(self, cr, uid, secret_key, context=None):
        valid_secret_key = self.pool.get('ir.config_parameter').get_param(cr, uid, 'pawnshop.update_fingerprint_secret_key', '')
        if secret_key != valid_secret_key:
            raise osv.except_osv(_('Error!'), _('The secret key is invalid.'))
        return True

    def action_update(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        if ids and active_model == 'res.partner' and active_ids:
            wizard = self.browse(cr, uid, ids[0], context=context)
            self._validate_secret_key(cr, uid, wizard.secret_key, context=context)
            self.pool.get(active_model).write(cr, uid, active_ids, {'fingerprint': wizard.fingerprint}, context=context)
        return True
