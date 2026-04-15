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
from openerp.tools.translate import _

class data_sync_receiver(osv.AbstractModel):
    _inherit = 'data.sync.receiver'

    def check_server_ready(self, cr, uid, model, method='read', context=None):
        if context is None:
            context = {}
        result = super(data_sync_receiver, self).check_server_ready(
            cr, uid, model, method=method, context=context
        )
        card_number = context.get('check_card_number', False)
        customer_name = context.get('check_customer_name', False)
        if card_number:
            partner_ids = self.pool.get('res.partner').search(
                cr, uid, [
                    ('card_number', '=', card_number),
                    ('name', '!=', customer_name)
                ], context=context
            )
            if partner_ids:
                raise osv.except_osv(_('UserError!'), _('Another customer with the same card number but a different name.'))
        return result
