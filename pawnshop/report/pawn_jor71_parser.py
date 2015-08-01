# -*- encoding: utf-8 -*-
##############################################################################
#
#
##############################################################################
import jasper_reports

def pawn_jor71_parser( cr, uid, ids, data, context ):
    return {
        'parameters': {
            'journal_id': data['form']['journal_id'],
            'pawn_shop_id': data['form']['pawn_shop_id'],
            'period_id': data['form']['period_id'],
        },
   }

jasper_reports.report_jasper(
    'report.pawn_jor71_report',
    'pawn.order',
    parser=pawn_jor71_parser
)
