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
import re
from openerp.osv import fields, osv
import time
from datetime import datetime
from openerp.tools.translate import _

CARD_TYPE_SELECTION = [('citizen', 'Citizen ID'),
                       ('officer', 'Government Officer ID'),
                       ('driving', 'Driving License ID'),
                       ('passport', 'Passport Number'),
                       ('certificate', 'Certificate')]

PARTNER_TITLE = [('mr', 'Mr.'),
                 ('mrs', 'Mrs.'),
                 ('miss', 'Miss.'),
                 ('company', 'Company Limited'),
                 ('partnership', 'Partnership'),
                 ]


class res_partner(osv.osv):

    _inherit = 'res.partner'

    def _get_age(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.birth_date:
                res[partner.id] = False
                continue
            today = datetime.strptime(fields.date.context_today(self, cr, uid, context=context), '%Y-%m-%d')
            born = datetime.strptime(partner.birth_date, '%Y-%m-%d')
            res[partner.id] = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return res

    def _get_pawn_shop(self, cr, uid, ids, field_names, arg=None, context=None):
        result = {}
        if not ids: return result
        for id in ids:
            result.setdefault(id, [])
        cr.execute("""
                SELECT distinct partner_id, pawn_shop_id FROM pawn_order
                WHERE partner_id in %s
            """,(tuple(ids),))
        res = cr.fetchall()
        for r in res:
            result[r[0]].append(r[1])
        return result

    def _get_receipt_shop(self, cr, uid, ids, field_names, arg=None, context=None):
        result = {}
        if not ids: return result
        for id in ids:
            result.setdefault(id, [])
        cr.execute("""
                SELECT distinct partner_id, pt.pawn_shop_id FROM account_voucher av
                join account_voucher_line avl on av.id = avl.voucher_id
                join product_product pp on pp.id = avl.product_id
                join product_template pt on pt.id = pp.product_tmpl_id
                WHERE partner_id in %s
            """,(tuple(ids),))
        res = cr.fetchall()
        for r in res:
            result[r[0]].append(r[1])
        return result

    def _get_create_year(self, cr, uid, ids, name, args, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.create_date:
                continue
            res[partner.id] = datetime.strptime(partner.create_date, '%Y-%m-%d %H:%M:%S').year
        return res

    def _search_age(self, cr, uid, obj, name, args, domain=None, context=None):
        ids = []
        for arg in args:
            arg_1, arg_2 = arg[1], arg[2]
            if arg_2 is False and arg_1 in ['=', '!=']:
                # For search age by is set or is not set
                arg_1, arg_2 = arg_1 == '=' and 'is' or 'is not', 'null'
            # compare partner's age with input value and get partner_id
            cr.execute("""
                select id from res_partner
                where extract(year from age(cast(birth_date as date))) %s %s
            """ % (arg_1, arg_2))
            ids = map(lambda x: x[0], cr.fetchall())
        return [('id', 'in', ids)]

    _columns = {
        'pawnshop': fields.boolean('Pawnshop', required=False, track_visibility='onchange'),
        'partner_title': fields.selection(PARTNER_TITLE, 'Title', required=False, track_visibility='onchange'),
        'card_type': fields.selection(CARD_TYPE_SELECTION, 'Card Type', required=False, track_visibility='onchange'),
        'card_number': fields.char('ID Number', size=64, required=False, select=True, track_visibility='onchange'),
        'address_full': fields.text('Full Address', required=False, track_visibility='onchange'),
        'issue_date': fields.date('Date of Issue', required=False, track_visibility='onchange'),
        'expiry_date': fields.date('Date of Expiry', required=False, track_visibility='onchange'),
        'birth_date': fields.date('Birth Date', required=False, track_visibility='onchange'),
        'age': fields.function(_get_age, string='Age', type='integer', fnct_search=_search_age),
        'pawn_shop_ids': fields.function(_get_pawn_shop, method=True, type='one2many', relation='pawn.shop', string='Customer of shops', readonly=True),
        'pawn_order_ids': fields.one2many('pawn.order', 'partner_id', 'Pawn Order', readonly=True),
        'receipt_shop_ids': fields.function(_get_receipt_shop, method=True, type='one2many', relation='pawn.shop', string='Buyer of shops', readonly=True),
        'receipt_ids': fields.one2many('account.voucher', 'partner_id', 'Sales Receipt', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True),
        'create_year': fields.function(_get_create_year, type='char', string='Create Year', store=True),
        'fingerprint': fields.binary('Latest Fingerprint', readonly=True, help="Latest customer's fingerprint"),
        'fingerprint_date': fields.datetime('Date of Lastest Fingerprint', readonly=True, help="Date of latest customer's fingerprint"),
        'name': fields.char('Name', size=128, required=True, select=True, track_visibility='onchange'),
        'active': fields.boolean('Active', track_visibility='onchange'),
        'country_id': fields.many2one('res.country', 'Country', track_visibility='onchange'),
        'phone': fields.char('Phone', size=64, track_visibility='onchange'),
        'customer': fields.boolean('Customer', track_visibility='onchange', help="Check this box if this contact is a customer."),
        'supplier': fields.boolean('Supplier', track_visibility='onchange', help="Check this box if this contact is a supplier. If it's not checked, purchase people will not see it when encoding a purchase order."),
    }
    _defaults = {
        'pawnshop': True
    }
    _sql_constraints = [
        ('card_number_uniq', 'unique(card_type, card_number)', 'Card number must be unique!'),
    ]

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        trans_obj = self.pool.get('ir.translation')
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.partner_title:
                for title in PARTNER_TITLE:
                    if record.partner_title == title[0]:
                        trans_title = trans_obj._get_source(cr, uid, 'res.partner' + ',' + 'partner_title', 'selection',  context.get('lang', False), title[1])
                        name =  "%s %s" % (trans_title, name)
            res.append((record.id, name))
        return res

    # Onchange
    def onchange_card_number(self, cr, uid, ids, card_number, card_type, context=None):
        if not card_number:
            return False
        # If card_type not specified, do not allow card_number
        if not card_type:
            warning = {
                'title': _('Warning!'),
                'message': _('Please select Card Type')
            }
            return {'value': {'card_number': False}, 'warning': warning}
        # For these types, only number is allowed.
        if card_type in ('citizen', 'officer', 'driving'):
            if card_type == 'citizen' and len(re.sub("\D", "", card_number)) != 13:
                warning = {
                    'title': _('Warning!'),
                    'message': _('Citizen ID must be 13 digits')
                }
                return {'value': {'card_number': re.sub("\D", "", card_number)}, 'warning': warning}
            if not card_number.isdigit():
                warning = {
                    'title': _('Warning!'),
                    'message': _('Card Number of selected type can contain only number')
                }
                return {'value': {'card_number': re.sub("\D", "", card_number)}, 'warning': warning}
        return False


    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]
            # kittiu
            #query_args = {'name': search_name}
            query_args = {'name': search_name, 'card_number': search_name}
            # -- kittiu
            limit_str = ''
            if limit:
                limit_str = ' limit %(limit)s'
                query_args['limit'] = limit
            cr.execute('''SELECT partner.id FROM res_partner partner
                          LEFT JOIN res_partner company ON partner.parent_id = company.id
                          WHERE partner.card_number ''' + operator +''' %(card_number)s
                             OR partner.email ''' + operator +''' %(name)s
                             OR partner.name || ' (' || COALESCE(company.name,'') || ')'
                          ''' + operator + ' %(name)s ' + limit_str, query_args)
            ids = map(lambda x: x[0], cr.fetchall())
            ids = self.search(cr, uid, [('id', 'in', ids)] + args, limit=limit, context=context)
            if ids:
                return self.name_get(cr, uid, ids, context)
        return super(res_partner, self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)

    def create(self, cr, uid, vals, context=None):
        # Update fingerprint date
        if 'fingerprint' in vals and vals['fingerprint']:
            vals['fingerprint_date'] = fields.datetime.now()
        return super(res_partner, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        # Update fingerprint date
        if 'fingerprint' in vals and vals['fingerprint']:
            vals['fingerprint_date'] = fields.datetime.now()
        return super(res_partner, self).write(cr, uid, ids, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        # Reset fingerprint
        default.update({
            'fingerprint': False,
            'fingerprint_date': False,
        })
        return super(res_partner, self).copy(cr, uid, id, default=default, context=context)


res_partner()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
