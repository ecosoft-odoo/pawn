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

    def _get_remark_summary(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            remark_list = []
            if record.is_fake:
                remark_list.append(u'ของปลอม')
            if record.is_redeemed:
                remark_list.append(u'ปล่อยของหลุดจำนำ')
            if record.is_stolen:
                remark_list.append(u'ทรัพย์ขโมยมา')
            if record.other:
                remark_list.append(record.other)
            result[record.id] = ', '.join(remark_list)
        return result

    _columns = {
        'name': fields.related('partner_id', 'name', type='char', string='Name', readonly=True, store=True),
        'firstname': fields.char('First Name', size=64, track_visibility='onchange'),
        'lastname': fields.char('Last Name', size=64, track_visibility='onchange'),
        'card_number': fields.related('partner_id', 'card_number', type='char', string='ID Number', store=True, track_visibility='onchange'),
        'partner_id': fields.many2one('res.partner', 'Customer (for change)', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'),
        'pawnshop': fields.char('Pawnshop', track_visibility='onchange'),
        'unbanned_pawnshop': fields.char('Unbanned Pawnshop', track_visibility='onchange'),
        'banned_date': fields.datetime('Blacklist Date', track_visibility='onchange'),
        'unbanned_date': fields.date('Unbanned Date', track_visibility='onchange'),
        'is_fake': fields.boolean('Fake Item', track_visibility='onchange'),
        'is_redeemed': fields.boolean('Redeemed Item', track_visibility='onchange',),
        'is_stolen': fields.boolean('Stolen Property', track_visibility='onchange',),
        'other': fields.char('Other', size=256, track_visibility='onchange'),
        'remark_summary': fields.function(
            _get_remark_summary,
            type='char',
            track_visibility='onchange',
            string='Remark',
            readonly=False,
            store={
            'blacklist.sync': (
                lambda self, cr, uid, ids, c={}: ids,
                ['is_fake', 'is_redeemed', 'is_stolen', 'other'],
                10
            )
            }
        ),
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True, track_visibility='onchange'),
        'index': fields.integer('Index'),
        'blacklist_line_ids': fields.one2many('blacklist.sync.line', 'blacklist_id', 'Blacklist Line', track_visibility='onchange'),
        'create_uid': fields.many2one('res.users', 'Responsible', readonly=True),
        'create_user': fields.char(string='Create User', readonly=True, track_visibility='onchange'),
        'write_uid': fields.many2one('res.users', "Modifier", readonly=True),
        'write_user': fields.char(string='Modifier User', readonly=True, track_visibility='onchange'),
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
        'pawnshop' : _get_branch,
    }

    def split_partner_name(self, cr, uid, partner_id, context=None):
        context = context or {}
        partner_obj = self.pool.get('res.partner')
        partner = partner_obj.browse(cr, uid, partner_id, context=context)
        name_parts = partner.name.split(' ', 1)
        if len(name_parts) > 1:
            return name_parts[0], name_parts[1]
        else:
            return name_parts[0], ''
        
    def get_last_blacklisted_partner(self, cr, uid, partner, context=None):
        context = context or {}
        blacklist_obj = self.pool.get('blacklist.sync')
        last_blacklist = {'index': 0}
        blacklist_ids = blacklist_obj.search(
                    cr, uid,
                    [
                        ('partner_id', '=', partner.id),
                        ('state', '!=', 'draft')
                    ],
                    order='banned_date desc',
                    limit=1,
                    context=context
                )
        if blacklist_ids:
            last_blacklist = blacklist_obj.read(cr, uid, blacklist_ids, ['index', 'state'], context=context)[0]

        return last_blacklist

    def action_active(self, cr, uid, ids, context=None):
        context = context or {}
        sender_obj = self.pool.get('data.sync.sender')
        partner_obj = self.pool.get('res.partner')
        for blacklist in self.browse(cr, uid, ids, context=context):
            partner = blacklist.partner_id
            l_blacklist = self.get_last_blacklisted_partner(cr, uid, partner, context=context)
            if l_blacklist.get('state', False) == 'active':
                raise osv.except_osv(_('UserError!'), _('This customer is already blacklisted.'))
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            next_index = l_blacklist.get('index', 0) + 1
            to_update = {'state': 'active','banned_date': now,'index': next_index}
            self.write(cr, uid, [blacklist.id], to_update, context=context)
            partner_obj.write(cr, uid, [partner.id], {'blacklist_customer': True}, context=context)
            fetch_vals = self.copy_data(cr, uid, blacklist.id, context=context)
            fetch_vals.update(to_update)
            context['check_card_number'] = partner.card_number
            context['check_customer_name'] = partner.name
            sender_obj.sync_create(cr, uid, 'blacklist.sync', fetch_vals, context=context)
        return True

    def action_inactive(self, cr, uid, ids, context=None):
        context = context or {}
        for blacklist in self.browse(cr, uid, ids, context=context):
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            branch  = self._get_branch(cr, uid, context=context)
            self.write(cr, uid, [blacklist.id], {'state': 'inactive','unbanned_date': now, 'unbanned_pawnshop': branch}, context=context)
        return True

    def create(self, cr, uid, vals, context=None):
        context = context or {}
        if vals.get('partner_id', False):
            # ถ้ามีการส่งลูกค้าจะทำการแยกชื่อและนามสกุล
            partner_obj = self.pool.get('res.partner')
            partner_id = vals.get('partner_id', False)
            if not vals.get('firstname', False) and not vals.get('lastname', False):
                vals['firstname'], vals['lastname'] = self.split_partner_name(cr, uid, partner_id, context=context)
            partner_obj.write(cr, uid, [partner_id], {'blacklist_customer': True}, context=context)
        if context.get('sync', True):
            # ถ้าไม่มีการส่ง sync เป็น False
            user_obj = self.pool.get('res.users')
            user = user_obj.browse(cr, uid, uid, context=context)
            vals['create_user'] = user.name
            vals['write_user'] = user.name
        return super(BlacklistSync, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        context = context or {}
        if context.get('sync', True):
            # ถ้าไม่มีการส่ง sync เป็น False
            user_obj = self.pool.get('res.users')
            user = user_obj.browse(cr, uid, uid, context=context)
            vals['write_user'] = user.name
        for blacklist in self.browse(cr, uid, ids, context=context):
            sender_obj = self.pool.get('data.sync.sender')
            if blacklist.state != 'draft' and context.get('sync', True):
                # อัพเดทข้อมูลใน server อื่น ถ้า สถานะไม่ใช่ draft และ ไม่มีการส่งcontext 'sync' = False
                sender_obj.sync_write(cr, uid, blacklist.id, 'blacklist.sync', vals, context=context)
            if vals.get('state', False) == 'inactive':
                # ถ้ามีการอัพเดทสถานะ inactive ให้ทำการอัพเดท partner ให้ติด blacklist เป็น Flase
                partner_obj = self.pool.get('res.partner')
                partner_id =  blacklist.partner_id.id
                partner_obj.write(cr, uid, partner_id, {'blacklist_customer': False}, context=context)
            if vals.get('partner_id', False):
                partner_id = vals.get('partner_id', False)
                if not vals.get('firstname', False) and not vals.get('lastname', False):
                    vals['firstname'], vals['lastname'] = self.split_partner_name(cr, uid, partner_id, context=context)
        return super(BlacklistSync, self).write(cr, uid, ids, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        context = context or {}
        for blacklist in self.browse(cr, uid, ids, context=context):
            if blacklist.state == 'active':
                raise osv.except_osv(
                    _('Error!'),
                    _('Cannot delete history in active state.')
                )
            sender_obj = self.pool.get('data.sync.sender')
            if blacklist.state == 'inactive' and context.get('sync', True):
                sender_obj.sync_unlink(cr, uid, blacklist.id, 'blacklist.sync', context=context)
        return super(BlacklistSync, self).unlink(cr, uid, ids, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}

        branch_name = self._get_branch(cr, uid, context)

        default.update({
            'state': 'draft',
            'index': 0,
            'pawnshop': branch_name,
            'unbanned_pawnshop': False,
            'banned_date': False,
            'unbanned_date': False,
        })

        return super(BlacklistSync, self).copy(cr, uid, id, default, context)

BlacklistSync()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: