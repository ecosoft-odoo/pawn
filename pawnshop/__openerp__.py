# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Ecosoft Co., Ltd. (http://ecosoft.co.th).
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

{
    'name': 'Pawn Shop Management',
    'version': '1.0',
    'author': 'Ecosoft',
    'summary': '',
    'description': """

    """,
    'category': 'Pawnshop Management',
    'website': 'http://www.ecosoft.co.th',
    'images': [],
    'depends': ['web_m2x_options',
                'account',
                'account_accountant',
                'account_cancel',
                'product',
                'account_auto_post',
                'account_transfer',
                'account_bank_balance',
                'hr_expense',
                'report_xls',
                ],
    'demo': [],
    'data': [
        'module_data.xml',
        'ir_config_parameter_data.xml',
        'security/pawn_security.xml',
        'security/ir.model.access.csv',
        'pawn_workflow.xml',
        'pawn_sequence.xml',
        'wizard/pawn_line_property_view.xml',
        'wizard/pawn_order_pawn_view.xml',
        'wizard/pawn_order_redeem_view.xml',
        'wizard/pawn_order_renew_view.xml',
        'wizard/pawn_order_pay_interest_view.xml',
        'wizard/pawn_item_location_status_view.xml',
        'wizard/pawn_item_create_receipt_view.xml',
        'wizard/pawn_undo_cancel_view.xml',
        'wizard/pawn_asset_for_sale_view.xml',
        'wizard/item_split_view.xml',
        'wizard/account_chart_view.xml',
        'wizard/pawn_jor6_submission_view.xml',
        'wizard/pawn_expire_final_view.xml',
        'wizard/update_partner_fingerprint_view.xml',
        'wizard/select_multi_sale_item_view.xml',
        'wizard/validate_sale_receipt_view.xml',
        'res_partner_view.xml',
        'pawn_view.xml',
        'item_view.xml',
        'pawn_rule_view.xml',
        'pawn_shop_view.xml',
        'account_view.xml',
        'account_voucher_view.xml',
        'account_transfer_view.xml',
        'item_property_view.xml',
        'res_config_view.xml',
        'res_bank_view.xml',
        'osv_scheduled_actions.xml',
        'res_users_view.xml',
        'data/pawn.rule.csv',
        'data/pawn.interest.rate.csv',
        'data/product.uom.csv',
        'data/product.category.csv',
        'report/custom_reports.xml',
        'report/pawn_report_view.xml',
        'report/pawn_status_report_view.xml',
        'report/pawn_interest_report_view.xml',
        'report/sale_performance_analysis_report.xml',
        'report/customer_report.xml',
        'report/item_sold_report.xml',
        'report/bank_transfer_report_view.xml',
        'report/wizard/pawn_jor6_wizard.xml',
        'report/wizard/pawn_jor7_wizard.xml',
        'report/wizard/pawn_op_cash_wizard.xml',
        'report/wizard/pawn_wh_cash_wizard.xml',
        'report/wizard/pawn_daily_wizard.xml',
    ],
    'qweb': [
        'static/src/xml/base.xml',
    ],
    'test': [
    ],
    'auto_install': False,
    'application': True,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
