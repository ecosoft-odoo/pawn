# -*- encoding: utf-8 -*-
##############################################################################
#
#
##############################################################################
import jasper_reports

def pawn_jor6_parser( cr, uid, ids, data, context ):
    return {
        'parameters': {
            'pawn_shop_id': data['form']['pawn_shop_id'],
            'journal_id': data['form']['journal_id'],
            'pawn_rule_id': data['form']['pawn_rule_id'],
            'report_date': data['form']['report_date'],
        },
   }

jasper_reports.report_jasper(
    'report.pawn_jor6_report',
    'pawn.order',
    parser=pawn_jor6_parser
)
