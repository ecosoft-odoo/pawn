# -*- encoding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _


class customer_report(osv.osv_memory):
    _name = 'customer.report'
    _description = 'Customer Report'

    _columns = {
        'pawn_shop': fields.char(
            string='Shop',
        ),
        'customer': fields.char(
            string='Customer',
        ),
        'subdistrict': fields.char(
            string='Subdistrict',
        ),
        'district': fields.char(
            string='District',
        ),
        'province': fields.char(
            string='Province',
        ),
        'country': fields.char(
            string='Nationality',
        ),
        'sex': fields.char(
            string='Sex',
        ),
        'age': fields.char(
            string='Age',
        ),
        'age_range': fields.char(
            string='Age Range',
        ),
        'number_of_ticket': fields.integer(
            string='Number Of Ticket',
        ),
        'amount_pawned': fields.float(
            string='Pawned Amount',
        ),
        'customer_status': fields.char(
            string='Customer Status',
        ),
        'customer_aging': fields.char(
            string='Customer Aging',
        ),
        'pawn_ticket_aging_1': fields.float(
            string='Pawn Ticket Aging 0-3 M',
        ),
        'pawn_ticket_aging_2': fields.float(
            string='Pawn Ticket Aging 3-6 M',
        ),
        'pawn_ticket_aging_3': fields.float(
            string='Pawn Ticket Aging 6-9 M',
        ),
        'pawn_ticket_aging_4': fields.float(
            string='Pawn Ticket Aging 9-12 M',
        ),
        'pawn_ticket_aging_5': fields.float(
            string='Pawn Ticket Aging > 12 M',
        ),
        'number_of_ticket_aging_1': fields.float(
            string='Number Of Ticket Aging 0-3 M',
        ),
        'number_of_ticket_aging_2': fields.float(
            string='Number Of Ticket Aging 3-6 M',
        ),
        'number_of_ticket_aging_3': fields.float(
            string='Number Of Ticket Aging 6-9 M',
        ),
        'number_of_ticket_aging_4': fields.float(
            string='Number Of Ticket Aging 9-12 M',
        ),
        'number_of_ticket_aging_5': fields.float(
            string='Number Of Ticket Aging > 12 M',
        ),
        'wizard_id': fields.many2one(
            'customer.report.wizard',
            string='Wizard',
        ),
    }


class customer_report_groupby_ticket_aging(osv.osv_memory):
    _name = 'customer.report.groupby.ticket.aging'
    _description = 'Customer Report Group By Pawn Ticket Aging'

    _columns = {
        'pawn_ticket_aging': fields.char(
            string='Pawn Ticket Aging',
        ),
        'number_of_customer': fields.integer(
            string='Number Of Customer',
        ),
        'number_of_ticket': fields.integer(
            string='Number Of Ticket',
        ),
        'amount_pawned': fields.float(
            string='Pawned Amount',
        ),
        'wizard_id': fields.many2one(
            'customer.report.wizard',
            string='Wizard',
        ),
    }


class customer_report_wizard(osv.osv_memory):
    _name = 'customer.report.wizard'
    _description = 'Customer Report Wizard'

    _columns = {
        'pawn_ticket_status': fields.selection(
            [('all', 'All'), ('pawn', 'Pawn'), ('redeem', 'Redeem'), ('expire', 'Expire')],
            string='Pawn Ticket Status',
            required=True,
        ),
        'report_at_date': fields.date(
            string='At Date',
            required=True,
        ),
        'groupby_pawn_ticket_aging': fields.boolean(
            string='Group By Pawn Ticket Aging',
        ),
    }

    _defaults = {
        'pawn_ticket_status': 'all',
        'report_at_date': fields.date.context_today,
        'groupby_pawn_ticket_aging': False,
    }

    def _get_column_insert_customer_report(self):
        columns = """
            (
                id, create_uid, create_date, write_date, write_uid, wizard_id,
                pawn_shop, customer, subdistrict, district, province, country, sex, age, age_range,
                number_of_ticket, amount_pawned, customer_status, customer_aging,
                pawn_ticket_aging_1, pawn_ticket_aging_2, pawn_ticket_aging_3,
                pawn_ticket_aging_4, pawn_ticket_aging_5, number_of_ticket_aging_1,
                number_of_ticket_aging_2, number_of_ticket_aging_3, number_of_ticket_aging_4,
                number_of_ticket_aging_5
            )
        """
        return columns

    def _get_sql_customer_report(self, uid, wizard):
        # Get value from wizard
        report_at_date = wizard.report_at_date
        pawn_ticket_status = wizard.pawn_ticket_status
        # SQL query for pawn ticket aging
        pawn_ticket_aging = """
            (DATE_PART('YEAR', AGE(TO_DATE('{report_at_date}', 'YYYY-MM-DD') + INTERVAL '1' DAY, date_order)) * 12) + 
            DATE_PART('MONTH', AGE(TO_DATE('{report_at_date}', 'YYYY-MM-DD') + INTERVAL '1' DAY, date_order)) + 
            (DATE_PART('DAY', AGE(TO_DATE('{report_at_date}', 'YYYY-MM-DD') + INTERVAL '1' DAY, date_order)) / 100)
        """.format(report_at_date=report_at_date)
        # SQL query for age
        age = "DATE_PART('YEAR', AGE('{report_at_date}', rp.birth_date))".format(report_at_date=report_at_date)
        # Extra where for filter pawn ticket status
        extra_where = ''
        if pawn_ticket_status == 'pawn':
            extra_where += """ AND (
                (po_sub.date_redeem IS NULL AND po_sub.date_final_expired IS NULL) OR 
                (po_sub.date_redeem IS NOT NULL AND '{report_at_date}' < po_sub.date_redeem) OR 
                (po_sub.date_final_expired IS NOT NULL AND '{report_at_date}' < po_sub.date_final_expired)
            )""".format(report_at_date=report_at_date)
        elif pawn_ticket_status == 'redeem':
            extra_where += " AND (po_sub.date_redeem IS NOT NULL AND '{report_at_date}' >= po_sub.date_redeem)".format(report_at_date=report_at_date)
        elif pawn_ticket_status == 'expire':
            extra_where += " AND (po_sub.date_final_expired IS NOT NULL AND '{report_at_date}' >= po_sub.date_final_expired)".format(report_at_date=report_at_date)
        # Get SQL
        sql = """
            (
                SELECT
                    NEXTVAL('customer_report_id_seq') AS id, {uid} AS create_uid, NOW() AS create_date,
                    NOW() AS write_date, {uid} AS write_uid, {wizard_id} AS wizard_id, po.pawn_shop,
                    CASE
                        WHEN rp.partner_title = 'mr' THEN 'นาย '
                        WHEN rp.partner_title = 'mrs' THEN 'นาง '
                        WHEN rp.partner_title = 'miss' THEN 'นางสาว '
                        WHEN rp.partner_title = 'company' THEN 'บริษัท '
                        WHEN rp.partner_title = 'partnership' THEN 'ห้างหุ้นส่วน '
                        ELSE ''
                    END || rp.name AS customer, NULL AS subdistrict, NULL AS district, NULL AS province, rc.name AS country,
                    CASE
                        WHEN rp.partner_title IN ('mr') THEN 'ชาย'
                        WHEN rp.partner_title IN ('mrs', 'miss') THEN 'หญิง'
                        ELSE 'อื่นๆ'
                    END AS sex, {age} AS age,
                    CASE
                        WHEN {age} <= 0 THEN '<= 0 ปี'
                        WHEN {age} > 0 AND {age} <= 10 THEN '1-10 ปี'
                        WHEN {age} > 10 AND {age} <= 20 THEN '11-20 ปี'
                        WHEN {age} > 20 AND {age} <= 30 THEN '21-30 ปี'
                        WHEN {age} > 30 AND {age} <= 40 THEN '31-40 ปี'
                        WHEN {age} > 40 AND {age} <= 50 THEN '41-50 ปี'
                        WHEN {age} > 50 AND {age} <= 60 THEN '51-60 ปี'
                        WHEN {age} > 60 AND {age} <= 70 THEN '61-70 ปี'
                        WHEN {age} > 70 AND {age} <= 80 THEN '71-80 ปี'
                        WHEN {age} > 80 AND {age} <= 90 THEN '81-90 ปี'
                        WHEN {age} > 90 AND {age} <= 100 THEN '91-100 ปี'
                        WHEN {age} > 100 THEN '> 100 ปี'
                        ELSE 'ไม่ได้กำหนด'
                    END AS age_range,
                    po.number_of_ticket, po.amount_pawned, po.customer_status,
                    CASE
                        WHEN po.customer_aging > 0 AND po.customer_aging <= 3 THEN '0-3 เดือน'
                        WHEN po.customer_aging <= 6 THEN '3-6 เดือน'
                        WHEN po.customer_aging <= 9 THEN '6-9 เดือน'
                        WHEN po.customer_aging <= 12 THEN '9-12 เดือน'
                        WHEN po.customer_aging > 12 THEN '> 12 เดือน'
                        ELSE ''
                    END AS customer_aging, po.pawn_ticket_aging_1, po.pawn_ticket_aging_2, po.pawn_ticket_aging_3,
                    po.pawn_ticket_aging_4, po.pawn_ticket_aging_5, po.number_of_ticket_aging_1, po.number_of_ticket_aging_2,
                    po.number_of_ticket_aging_3, po.number_of_ticket_aging_4, po.number_of_ticket_aging_5
                FROM res_partner rp
                LEFT JOIN res_country rc ON rp.country_id = rc.id
                LEFT JOIN (
                    SELECT
                        po_sub.partner_id, COUNT(po_sub.*) AS number_of_ticket, SUM(po_sub.amount_pawned) AS amount_pawned, MAX(ps_sub.name) AS pawn_shop,
                        CASE
                            WHEN COUNT(DISTINCT po_sub.date_order) > 1 THEN 'ลูกค้าเก่า'
                            ELSE 'ลูกค้าใหม่'
                        END AS customer_status, 
                        (DATE_PART('YEAR', AGE(TO_DATE('{report_at_date}', 'YYYY-MM-DD') + INTERVAL '1' DAY, MIN(po_sub.date_order))) * 12) +  
                        DATE_PART('MONTH', AGE(TO_DATE('{report_at_date}', 'YYYY-MM-DD') + INTERVAL '1' DAY, MIN(po_sub.date_order))) + 
                        (DATE_PART('DAY', AGE(TO_DATE('{report_at_date}', 'YYYY-MM-DD') + INTERVAL '1' DAY, MIN(po_sub.date_order))) / 100) AS customer_aging,
                        SUM(CASE WHEN {pawn_ticket_aging} > 0 AND {pawn_ticket_aging} <= 3 THEN amount_pawned ELSE 0 END) AS pawn_ticket_aging_1,
                        SUM(CASE WHEN {pawn_ticket_aging} > 3 AND {pawn_ticket_aging} <= 6 THEN amount_pawned ELSE 0 END) AS pawn_ticket_aging_2,
                        SUM(CASE WHEN {pawn_ticket_aging} > 6 AND {pawn_ticket_aging} <= 9 THEN amount_pawned ELSE 0 END) AS pawn_ticket_aging_3,
                        SUM(CASE WHEN {pawn_ticket_aging} > 9 AND {pawn_ticket_aging} <= 12 THEN amount_pawned ELSE 0 END) AS pawn_ticket_aging_4,
                        SUM(CASE WHEN {pawn_ticket_aging} > 12 THEN amount_pawned ELSE 0 END) AS pawn_ticket_aging_5,
                        SUM(CASE WHEN {pawn_ticket_aging} > 0 AND {pawn_ticket_aging} <= 3 THEN 1 ELSE 0 END) AS number_of_ticket_aging_1,
                        SUM(CASE WHEN {pawn_ticket_aging} > 3 AND {pawn_ticket_aging} <= 6 THEN 1 ELSE 0 END) AS number_of_ticket_aging_2,
                        SUM(CASE WHEN {pawn_ticket_aging} > 6 AND {pawn_ticket_aging} <= 9 THEN 1 ELSE 0 END) AS number_of_ticket_aging_3,
                        SUM(CASE WHEN {pawn_ticket_aging} > 9 AND {pawn_ticket_aging} <= 12 THEN 1 ELSE 0 END) AS number_of_ticket_aging_4,
                        SUM(CASE WHEN {pawn_ticket_aging} > 12 THEN 1 ELSE 0 END) AS number_of_ticket_aging_5
                    FROM pawn_order po_sub
                    LEFT JOIN pawn_shop ps_sub ON po_sub.pawn_shop_id = ps_sub.id
                    WHERE po_sub.state not in ('draft', 'cancel') AND po_sub.date_order <= '{report_at_date}' {extra_where}
                    GROUP BY po_sub.partner_id
                ) po ON rp.id = po.partner_id
                WHERE rp.supplier = True AND rp.pawnshop = True AND po.number_of_ticket IS NOT NULL
            )
        """.format(
            uid=uid,
            wizard_id=wizard.id,
            age=age,
            report_at_date=report_at_date,
            pawn_ticket_aging=pawn_ticket_aging,
            extra_where=extra_where,
        )
        return sql

    def _execute_customer_report(self, cr, uid, wizard):
        cr.execute("""INSERT INTO customer_report {} {}""".format(
            self._get_column_insert_customer_report(),
            self._get_sql_customer_report(uid, wizard)
        ))
        return True

    def _get_customer_report(self, cr, uid, wizard, context=None):
        # Execute the report
        self._execute_customer_report(cr, uid, wizard)
        # View the report
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj._get_id(cr, uid, 'pawnshop', 'action_customer_report')
        id = mod_obj.read(cr, uid, [result], ['res_id'], context=context)[0]['res_id']
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result.update({
            'name': _(result['name']),
            'domain': [('wizard_id', '=', wizard.id)],
        })
        return result

    def _get_column_insert_customer_report_groupby_ticket_aging(self):
        columns = """
            (
                id, create_uid, create_date, write_date, write_uid, wizard_id,
                pawn_ticket_aging, number_of_customer, number_of_ticket, amount_pawned
            )
        """
        return columns

    def _get_sql_customer_report_groupby_ticket_aging(self, uid, wizard):
        _from = self._get_sql_customer_report(uid, wizard)
        sql = """
            (
                (
                    SELECT
                        NEXTVAL('customer_report_groupby_ticket_aging_id_seq') AS id,
                        {uid} AS create_uid, NOW() AS create_date, NOW() AS write_date, {uid} AS write_uid,
                        {wizard_id} AS wizard_id, '0-3 เดือน' AS pawn_ticket_aging, COUNT(*) AS number_of_customer,
                        SUM(number_of_ticket_aging_1) AS number_of_ticket, SUM(pawn_ticket_aging_1) AS amount_pawned
                    FROM {_from} AS customer_report
                    WHERE pawn_ticket_aging_1 > 0
                )
                UNION
                (
                    SELECT
                        NEXTVAL('customer_report_groupby_ticket_aging_id_seq') AS id,
                        {uid} AS create_uid, NOW() AS create_date, NOW() AS write_date, {uid} AS write_uid,
                        {wizard_id} AS wizard_id, '3-6 เดือน' AS pawn_ticket_aging, COUNT(*) AS number_of_customer,
                        SUM(number_of_ticket_aging_2) AS number_of_ticket, SUM(pawn_ticket_aging_2) AS amount_pawned
                    FROM {_from} AS customer_report
                    WHERE pawn_ticket_aging_2 > 0
                )
                UNION
                (
                    SELECT
                        NEXTVAL('customer_report_groupby_ticket_aging_id_seq') AS id,
                        {uid} AS create_uid, NOW() AS create_date, NOW() AS write_date, {uid} AS write_uid,
                        {wizard_id} AS wizard_id, '6-9 เดือน' AS pawn_ticket_aging, COUNT(*) AS number_of_customer,
                        SUM(number_of_ticket_aging_3) AS number_of_ticket, SUM(pawn_ticket_aging_3) AS amount_pawned
                    FROM {_from} AS customer_report
                    WHERE pawn_ticket_aging_3 > 0
                )
                UNION
                (
                    SELECT
                        NEXTVAL('customer_report_groupby_ticket_aging_id_seq') AS id,
                        {uid} AS create_uid, NOW() AS create_date, NOW() AS write_date, {uid} AS write_uid,
                        {wizard_id} AS wizard_id, '9-12 เดือน' AS pawn_ticket_aging, COUNT(*) AS number_of_customer,
                        SUM(number_of_ticket_aging_4) AS number_of_ticket, SUM(pawn_ticket_aging_4) AS amount_pawned
                    FROM {_from} AS customer_report
                    WHERE pawn_ticket_aging_4 > 0
                )
                UNION
                (
                    SELECT
                        NEXTVAL('customer_report_groupby_ticket_aging_id_seq') AS id,
                        {uid} AS create_uid, NOW() AS create_date, NOW() AS write_date, {uid} AS write_uid,
                        {wizard_id} AS wizard_id, '> 12 เดือน' AS pawn_ticket_aging, COUNT(*) AS number_of_customer,
                        SUM(number_of_ticket_aging_5) AS number_of_ticket, SUM(pawn_ticket_aging_5) AS amount_pawned
                    FROM {_from} AS customer_report
                    WHERE pawn_ticket_aging_5 > 0
                )
            )
        """.format(
            uid=uid,
            wizard_id=wizard.id,
            _from=_from,
        )
        return sql

    def _execute_customer_report_groupby_ticket_aging(self, cr, uid, wizard):
        cr.execute("""INSERT INTO customer_report_groupby_ticket_aging {} {}""".format(
            self._get_column_insert_customer_report_groupby_ticket_aging(),
            self._get_sql_customer_report_groupby_ticket_aging(uid, wizard)
        ))
        return True

    def _get_customer_report_groupby_ticket_aging(self, cr, uid, wizard, context=None):
        # Execute the report
        self._execute_customer_report_groupby_ticket_aging(cr, uid, wizard)
        # View the report
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj._get_id(cr, uid, 'pawnshop', 'action_customer_report_groupby_ticket_aging')
        id = mod_obj.read(cr, uid, [result], ['res_id'], context=context)[0]['res_id']
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result.update({
            'name': _(result['name']),
            'domain': [('wizard_id', '=', wizard.id)],
        })
        return result

    def start_report(self, cr, uid, ids, data, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        if not wizard.groupby_pawn_ticket_aging:
            result = self._get_customer_report(cr, uid, wizard, context=context)
        else:
            result = self._get_customer_report_groupby_ticket_aging(cr, uid, wizard, context=context)
        return result
