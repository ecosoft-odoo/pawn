# -*- encoding: utf-8 -*-
##############################################################################
#
#
##############################################################################
import jasper_reports

def pawn_daily_parser( cr, uid, ids, data, context ):
    return {
        'parameters': {
            'pawn_shop_id': data['form']['pawn_shop_id'],
            'stk1_journal_id': data['form']['stk1_journal_id'],
            'stk2_journal_id': data['form']['stk2_journal_id'],
            'report_from_date': data['form']['report_from_date'],
            'report_to_date': data['form']['report_to_date'],
            # Accounts
            'accrued_interest_account_id': data['form']['accrued_interest_account_id'],
            'interest_account_id': data['form']['interest_account_id'],
            'interest_disc_account_id': data['form']['interest_disc_account_id'],
            'interest_add_account_id': data['form']['interest_add_account_id'],
            'sale_account_id': data['form']['sale_account_id'],
            'refund_account_id': data['form']['refund_account_id'],
        },
   }

jasper_reports.report_jasper(
    'report.pawn_daily_report',
    'pawn.order',
    parser=pawn_daily_parser
)
