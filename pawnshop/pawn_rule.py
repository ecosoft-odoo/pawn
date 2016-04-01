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
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Available interest rule
INTEREST_RULE = [('amount_rate', 'Interest Rate By Amount'),
                 ('fixed_rate', 'Fixed interest Rate')]
# INTEREST_PERIOD = [('1_month', 'Monthly'),
#                  ('1_day', 'Daily')]
DAYS = [(0, '0 days'),
        (10, '10 days'),
        (15, '15 days'),
        (20, '20 days'),
        (25, '25 days'),
        (30, '30 days')]
MONTHS = [(1, '1 month'),
        (2, '2 months'),
        (3, '3 months'),
        (4, '4 months'),
        (5, '5 months'),
        (6, '6 months')]


class pawn_rule(osv.osv):

    _name = "pawn.rule"
    _description = "Pawn Rule"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'length_month': fields.selection(MONTHS, 'Months', required=True),
        'length_day': fields.selection(DAYS, 'Days', required=True),
        #'interest_period': fields.selection(INTEREST_PERIOD, 'Interest Period', required=True, help="Period which interest will be created and posted."),
        'interest_type': fields.selection(INTEREST_RULE, 'Type of Interest', required=True, help="Determine type of interest to be used for calculation."),
        'interest_fixed_rate': fields.float('Fixed Percentage'),
        'interest_amount_rates': fields.one2many('pawn.interest.rate', 'rule_id', 'Amount Rates'),
    }
    _defaults = {
        'interest_type': 'amount_rate'
    }

    def _get_date_expired(self, cr, uid, rule_id, date, context=None):
        rule_obj = self.pool.get('pawn.rule')
        rule = rule_obj.browse(cr, uid, rule_id, context=context)
        start_date = datetime.strptime(date[:10], '%Y-%m-%d')
        # date expired
        date_expired = start_date + relativedelta(months=rule.length_month or 0.0)
        #date_expired = date_expired + relativedelta(days=(start_date.day - date_expired.day) or 0.0)  # If not getting the same date i.e., from 31/10 -> 28/02
        return date_expired

    def calculate_monthly_interest(self, cr, uid, id, amount, context=None):
        rule = self.browse(cr, uid, id, context=context)
        interest_amt = 0.0
        if rule.interest_type == 'amount_rate':
            amount_from = 0.0
            for r in rule.interest_amount_rates:
                rate = r.rate / 100
                # Case 1: In Range, get interest and quit.
                if amount_from <= r.amount_upto and amount <= r.amount_upto:
                    interest_amt += (amount - amount_from) * rate
                    break
                # Case 2: Over Range, only get commission for this range first and postpone to next range.
                elif amount_from <= r.amount_upto and amount > r.amount_upto:
                    interest_amt += (r.amount_upto - amount_from) * rate
                    amount_from = r.amount_upto
        if rule.interest_type == 'fixed_rate':
            rate = rule.interest_fixed_rate / 100
            interest_amt = amount * rate
        return interest_amt

pawn_rule()


class pawn_interest_rate(osv.osv):

    _name = "pawn.interest.rate"
    _description = "Amount Rates"
    _columns = {
        'rule_id': fields.many2one('pawn.rule', 'Pawn Rule', ondelete='cascade'),
        'amount_upto': fields.float('Amount Up-To', required=True),
        'rate': fields.float('Interest Rate (%)', required=True),
    }
    _order = 'id'

pawn_interest_rate()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
