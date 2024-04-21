# -*- coding: utf-8 -*-
# © 2024 Ecosoft (ecosoft.co.th).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.osv import osv, fields


class CustomerReport(osv.osv_memory):
    _inherit = "customer.report"

    _columns = {
        "township": fields.char(
            string="Township",
        ),
        "district": fields.char(
            string="District",
        ),
        "province": fields.char(
            string="Province",
        ),
    }


class CustomerReportWizard(osv.osv_memory):
    _inherit = "customer.report.wizard"

    def hook_column_insert_customer_report(self):
        res = super(CustomerReportWizard, self).hook_column_insert_customer_report()
        res += ", township, district, province"
        return res

    def hook_sql_select(self):
        res = super(CustomerReportWizard, self).hook_sql_select()
        res += ", rp.township, rp.district, rp.province"
        return res
