# -*- encoding: utf-8 -*-
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _


class sale_performance_analysis_report(osv.osv):
    _name = 'sale.performance.analysis.report'
    _description = 'Sale Performance Analysis Report'
    _auto = False

    _columns = {
        'item': fields.char(
            string='Item',
        ),
        'customer': fields.char(
            string='Customer',
        ),
        'item_description': fields.text(
            string='Description',
        ),
        'category': fields.char(
            string='Category',
        ),
        'date_order': fields.date(
            string='Pawn Date',
        ),
        'date_final_expired': fields.date(
            string='Final Expire Date',
        ),
        'date_voucher': fields.date(
            string='Voucher Date',
        ),
        'price_estimated': fields.float(
            string='Estimated Price',
        ),
        'price_pawned': fields.float(
            string='Pawned Price',
        ),
        'price_sale': fields.float(
            string='Sale Price',
        ),
        'profit_loss': fields.float(
            string='Profit / Loss',
        ),
        'sale_per_pawn_percent': fields.float(
            string='% Sale Price Per Pawned Price'
        ),
        'sale_per_estimate_percent': fields.float(
            string='% Sale Price Per Estimated Price',
        ),
        'sale_quality': fields.char(
            string='Sale Quality',
        ),
        'appraisal_quality': fields.char(
            string='Appraisal Quality',
        ),
    }

    def _get_sql(self):
        sale_per_pawn_percent = "100 * (avl.price_unit - pp.price_pawned) / pp.price_pawned"
        sale_per_estimate_percent = "100 * (avl.price_unit - pp.price_estimated) / pp.price_estimated"
        sql = """
            SELECT
                pp.id, pt.name AS item, rp.name AS customer, pp.item_description,
                pc.name AS category, pp.date_order, pp.date_final_expired,
                av.date AS date_voucher, pp.price_estimated, pp.price_pawned,
                avl.price_unit AS price_sale, avl.price_unit - pp.price_pawned AS profit_loss,
                %s AS sale_per_pawn_percent, %s AS sale_per_estimate_percent,
                CASE
                    WHEN %s > 20 THEN 'ดีมาก'
                    WHEN %s > 0 THEN 'ดี'
                    WHEN %s = 0 THEN 'เสมอตัว'
                    WHEN %s >= -20 THEN 'ไม่ดี'
                    ELSE 'ต้องปรับปรุง'
                END AS sale_quality,
                CASE
                    WHEN %s > 20 THEN 'ดีมาก'
                    WHEN %s > 0 THEN 'ดี'
                    WHEN %s = 0 THEN 'เสมอตัว'
                    WHEN %s >= -20 THEN 'ไม่ดี'
                    ELSE 'ต้องปรับปรุง'
                END AS appraisal_quality
            FROM product_product pp
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN res_partner rp ON pt.partner_customer_id = rp.id
            LEFT JOIN product_category pc ON pt.categ_id = pc.id
            LEFT JOIN account_voucher_line avl ON pp.id = avl.product_id
            LEFT JOIN account_voucher av ON avl.voucher_id = av.id
            WHERE pt.type = 'consu' and pt.sale_ok = True AND av.state = 'posted'
        """ % (
            sale_per_pawn_percent, sale_per_estimate_percent,
            sale_per_pawn_percent, sale_per_pawn_percent, sale_per_pawn_percent, sale_per_pawn_percent,
            sale_per_estimate_percent, sale_per_estimate_percent, sale_per_estimate_percent, sale_per_estimate_percent
        )
        return sql

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE OR REPLACE VIEW %s AS (%s)""" % (self._table, self._get_sql()))


class sale_performance_analysis_report_wizard(osv.osv_memory):
    _name = 'sale.performance.analysis.report.wizard'
    _description = 'Sale Performance Analysis Report Wizard'

    _columns = {
        'date_from': fields.date(
            string='Date From',
        ),
        'date_to': fields.date(
            string='Date To',
        ),
    }

    def start_report(self, cr, uid, ids, data, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj._get_id(cr, uid, 'pawnshop', 'action_sale_performance_analysis_report')
        id = mod_obj.read(cr, uid, [result], ['res_id'], context=context)[0]['res_id']
        result = act_obj.read(cr, uid, [id], context=context)[0]
        # Domain
        wizard = self.browse(cr, uid, ids[0], context=context)
        domain = []
        if wizard.date_from:
            domain += [('date_voucher', '>=', wizard.date_from)]
        if wizard.date_to:
            domain += [('date_voucher', '<=', wizard.date_to)]
        result['domain'] = domain
        result['name'] = _(result['name'])
        return result
