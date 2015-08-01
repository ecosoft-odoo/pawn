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

class pawn_wh_cash_wizard(osv.osv_memory):

    _name = 'pawn.wh.cash.wizard'

    def _get_pawn_shop_id(self, cr, uid, context=None):
        shop_obj = self.pool.get('pawn.shop')
        shop_ids = shop_obj.search(cr, uid, [])
        return shop_ids and shop_ids[0] or False

    _columns = {
        'pawn_shop_id': fields.many2one('pawn.shop', 'Pawnshop', required=True),
        'journal_id': fields.many2one('account.journal', 'Journal', domain=[('type', '=', 'cash'), ('pawn_journal', '=', False)], required=True),
        'report_from_date': fields.date('Date From', required=True),
        'report_to_date': fields.date('Date To', required=True),
    }
    _defaults = {
        'pawn_shop_id': _get_pawn_shop_id,
    }

    def onchange_report_date_from(self, cr, uid, ids, report_from_date, report_to_date):
        res = {}
        if not report_to_date:
            res = {'report_to_date': report_from_date}
        return {'value': res}

    def start_report(self, cr, uid, ids, data, context=None):
        for wiz_obj in self.read(cr, uid, ids):
            if 'form' not in data:
                data['form'] = {}
            data['form']['pawn_shop_id'] = wiz_obj['pawn_shop_id'][0]
            data['form']['journal_id'] = wiz_obj['journal_id'][0]
            data['form']['report_from_date'] = wiz_obj['report_from_date']
            data['form']['report_to_date'] = wiz_obj['report_to_date']
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'pawn_wh_cash_report',
                'datas': data,
            }

pawn_wh_cash_wizard()
