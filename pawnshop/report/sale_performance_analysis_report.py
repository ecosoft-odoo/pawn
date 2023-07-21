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
        'quantity': fields.float(
            string='Quantity',
        ),
        'price_estimated': fields.float(
            string='Estimated Price',
        ),
        'price_pawned': fields.float(
            string='Pawned Price',
        ),
        'price_pawned_per_price_estimated': fields.float(
            string='Pawned Price Per Estimaed Price',
        ),
        'price_sale': fields.float(
            string='Sale Price',
        ),
        'price_sale_total': fields.float(
            string='Total Sale Price',
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
        'pawn_shop': fields.char(
            string='Shop',
        ),
    }

    def _get_quality(self, percent):
        if percent > 20:
            quality = 'ดีมาก'
        elif percent > 0:
            quality = 'ดี'
        elif percent == 0:
            quality = 'เสมอตัว'
        elif percent >= -20:
            quality = 'ไม่ดี'
        else:
            quality = 'ต้องปรับปรุง'
        return quality

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        res = super(sale_performance_analysis_report, self).read_group(
            cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)
        for line in res:
            price_estimated = line['price_estimated']
            price_pawned = line['price_pawned']
            price_sale = line['price_sale']
            sale_per_pawn_percent = 100 * (price_sale - price_pawned) / price_pawned
            sale_per_estimate_percent = 100 * (price_sale - price_estimated) / price_estimated
            sale_quality = self._get_quality(sale_per_pawn_percent)
            appraisal_quality = self._get_quality(sale_per_estimate_percent)
            price_pawned_per_price_estimated = price_pawned / price_estimated
            line.update({
                'sale_per_pawn_percent': sale_per_pawn_percent,
                'sale_per_estimate_percent': sale_per_estimate_percent,
                'sale_quality': sale_quality,
                'appraisal_quality': appraisal_quality,
                'price_pawned_per_price_estimated': price_pawned_per_price_estimated,
            })

        # Rearrange group
        if groupby:
            if groupby[0] in ['sale_quality', 'appraisal_quality']:
                res_temp = []
                groups = ['ดีมาก', 'ดี', 'เสมอตัว', 'ไม่ดี', 'ต้องปรับปรุง']
                for group in groups:
                    res_temp.extend(filter(lambda l: l[groupby[0]] == group, res))
                res_temp.extend(filter(lambda l: l[groupby[0]] not in groups, res))
                res = res_temp
        return res

    def _get_sql(self):
        sale_per_pawn_percent = "100 * (avl.price_unit - pp.price_pawned) / pp.price_pawned"
        sale_per_estimate_percent = "100 * (avl.price_unit - pp.price_estimated) / pp.price_estimated"
        sql = """
            SELECT
                pp.id, pt.name AS item,
                CASE
                    WHEN rp.partner_title = 'mr' THEN 'นาย '
                    WHEN rp.partner_title = 'mrs' THEN 'นาง '
                    WHEN rp.partner_title = 'miss' THEN 'นางสาว '
                    WHEN rp.partner_title = 'company' THEN 'บริษัท '
                    WHEN rp.partner_title = 'partnership' THEN 'ห้างหุ้นส่วน '
                    ELSE ''
                END || rp.name AS customer, pp.item_description,
                pc.name AS category, pp.date_order, pp.date_final_expired,
                av.date AS date_voucher, avl.quantity, pp.price_estimated, pp.price_pawned,
                pp.price_pawned / pp.price_estimated AS price_pawned_per_price_estimated,
                avl.price_unit AS price_sale, avl.amount AS price_sale_total,
                avl.price_unit - pp.price_pawned AS profit_loss,
                {sale_per_pawn_percent} AS sale_per_pawn_percent, {sale_per_estimate_percent} AS sale_per_estimate_percent,
                CASE
                    WHEN {sale_per_pawn_percent} > 20 THEN 'ดีมาก'
                    WHEN {sale_per_pawn_percent} > 0 THEN 'ดี'
                    WHEN {sale_per_pawn_percent} = 0 THEN 'เสมอตัว'
                    WHEN {sale_per_pawn_percent} >= -20 THEN 'ไม่ดี'
                    ELSE 'ต้องปรับปรุง'
                END AS sale_quality,
                CASE
                    WHEN {sale_per_estimate_percent} > 20 THEN 'ดีมาก'
                    WHEN {sale_per_estimate_percent} > 0 THEN 'ดี'
                    WHEN {sale_per_estimate_percent} = 0 THEN 'เสมอตัว'
                    WHEN {sale_per_estimate_percent} >= -20 THEN 'ไม่ดี'
                    ELSE 'ต้องปรับปรุง'
                END AS appraisal_quality, ps.name AS pawn_shop
            FROM product_product pp
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN res_partner rp ON pt.partner_customer_id = rp.id
            LEFT JOIN product_category pc ON pt.categ_id = pc.id
            LEFT JOIN account_voucher_line avl ON pp.id = avl.product_id
            LEFT JOIN account_voucher av ON avl.voucher_id = av.id
            LEFT JOIN pawn_shop ps ON av.pawn_shop_id = ps.id
            WHERE pt.type = 'consu' and pt.sale_ok = True AND av.state = 'posted'
        """.format(
            sale_per_pawn_percent=sale_per_pawn_percent,
            sale_per_estimate_percent=sale_per_estimate_percent,
        )
        return sql

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE OR REPLACE VIEW {} AS ({})""".format(self._table, self._get_sql()))


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
        result.update({
            'name': _(result['name']),
            'domain': domain,
        })
        return result
