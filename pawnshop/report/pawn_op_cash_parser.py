# -*- encoding: utf-8 -*-
##############################################################################
#
#
##############################################################################
import jasper_reports

def pawn_op_cash_parser( cr, uid, ids, data, context ):
    return {
        'parameters': {
            'pawn_shop_id': data['form']['pawn_shop_id'],
            'journal_id': data['form']['journal_id'],
            'report_from_date': data['form']['report_from_date'],
            'report_to_date': data['form']['report_to_date'],
            # Accounts
            'redeem_account_id': data['form']['redeem_account_id'],
            'expire_account_id': data['form']['expire_account_id'],
            'accrued_interest_account_id': data['form']['accrued_interest_account_id'],
            'interest_account_id': data['form']['interest_account_id'],
            'interest_disc_account_id': data['form']['interest_disc_account_id'],
            'interest_add_account_id': data['form']['interest_add_account_id'],
            'sale_account_id': data['form']['sale_account_id'],
            'refund_account_id': data['form']['refund_account_id'],
            'cost_account_id': data['form']['cost_account_id'],
            'op_cash_account_id': data['form']['op_cash_account_id'],
        },
   }

jasper_reports.report_jasper(
    'report.pawn_op_cash_report',
    'pawn.order',
    parser=pawn_op_cash_parser
)
