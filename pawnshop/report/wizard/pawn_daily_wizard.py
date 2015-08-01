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
from datetime import datetime

class pawn_daily_wizard(osv.osv_memory):

    _name = 'pawn.daily.wizard'

    def _get_pawn_shop_id(self, cr, uid, context=None):
        shop_obj = self.pool.get('pawn.shop')
        shop_ids = shop_obj.search(cr, uid, [])
        return shop_ids and shop_ids[0] or False

    _columns = {
        'pawn_shop_id': fields.many2one('pawn.shop', 'Pawnshop', required=True),
        'stk1_journal_id': fields.many2one('account.journal', 'Journal (1)', domain=[('type', '=', 'cash'), ('pawn_journal', '=', True)], required=True),
        'stk2_journal_id': fields.many2one('account.journal', 'Journal (2)', domain=[('type', '=', 'cash'), ('pawn_journal', '=', True)], required=True),
        'report_from_date': fields.date('Date From', required=True),
        'report_to_date': fields.date('Date To', required=True),
        # Accounting
        'accrued_interest_account_id': fields.many2one('account.account', 'Accrued Interest', required=True),
        'interest_account_id': fields.many2one('account.account', 'Actual Interest', required=True),
        'interest_disc_account_id': fields.many2one('account.account', 'Discount Interest', required=True),
        'interest_add_account_id': fields.many2one('account.account', 'Addition Interest', required=True),
        'sale_account_id': fields.many2one('account.account', 'Sales', required=True),
        'refund_account_id': fields.many2one('account.account', 'Sales Refund', required=True),
    }
    _defaults = {
        'pawn_shop_id': _get_pawn_shop_id,
    }

    def onchange_report_date_from(self, cr, uid, ids, report_from_date, report_to_date):
        res = {'report_to_date': report_from_date}
        return {'value': res}

    def start_report(self, cr, uid, ids, data, context=None):
        for wiz_obj in self.read(cr, uid, ids):
            # Not allow to run this report > today
            test_date = datetime.strptime(wiz_obj['report_to_date'], "%Y-%m-%d")
            today = fields.date.context_today(self, cr, uid, context=context)
            if test_date > datetime.strptime(today, "%Y-%m-%d"):
                raise osv.except_osv(_('Warning!'), _("You can not choose future date"))
            if 'form' not in data:
                data['form'] = {}
            data['form']['pawn_shop_id'] = wiz_obj['pawn_shop_id'][0]
            data['form']['stk1_journal_id'] = wiz_obj['stk1_journal_id'][0]
            data['form']['stk2_journal_id'] = wiz_obj['stk2_journal_id'][0]
            data['form']['report_from_date'] = wiz_obj['report_from_date']
            data['form']['report_to_date'] = wiz_obj['report_to_date']
            # Accounts
            data['form']['accrued_interest_account_id'] = wiz_obj['accrued_interest_account_id'][0]
            data['form']['interest_account_id'] = wiz_obj['interest_account_id'][0]
            data['form']['interest_disc_account_id'] = wiz_obj['interest_disc_account_id'][0]
            data['form']['interest_add_account_id'] = wiz_obj['interest_add_account_id'][0]
            data['form']['sale_account_id'] = wiz_obj['sale_account_id'][0]
            data['form']['refund_account_id'] = wiz_obj['refund_account_id'][0]
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'pawn_daily_report',
                'datas': data,
            }

pawn_daily_wizard()
