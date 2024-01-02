# -*- coding: utf-8 -*-
from openerp.addons.report_xls.report_xls import report_xls
from openerp.report import report_sxw
from openerp.tools.translate import _
from dateutil.relativedelta import relativedelta
from xlwt.Style import default_style
import xlwt
import datetime

COLUMN_SIZES = [
    ('number', 10),
    ('date_order', 20),
    ('pawn_number', 20),
    ('customer_name', 50),
    ('customer_address', 80),
    ('item_description', 90),
    ('item_qty', 10),
    ('total_baht', 15),
    ('total_satang', 10),
    ('note', 20),
]

ROW_HEIGHT = 320

FONT_SIZE = 260


class PawnJo6ReportXLSParser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(PawnJo6ReportXLSParser, self).__init__(
            cr, uid, name, context=context)

        self.localcontext.update({
            'report_name': _('Jor6 Report'),
        })

    def set_context(self, objects, data, ids, report_type=None):
        # Declare Valiable
        cr, uid = self.cr, self.uid

        # Get Data
        form = data.get('form', {})
        pawn_shop_id = form.get('pawn_shop_id', False)
        journal_id = form.get('journal_id', False)
        pawn_rule_id = form.get('pawn_rule_id', False)
        report_date = form.get('report_date', False)

        # Browse Pawn Shop
        PawnShop = self.pool.get('pawn.shop')
        pawn_shop = PawnShop.browse(cr, uid, pawn_shop_id)

        # Browse Report
        Report = self.pool.get('pawn.order')
        domain = []
        if report_date:
            domain += [('date_jor6', '=', report_date)]
        if pawn_shop_id:
            domain += [('pawn_shop_id', '=', pawn_shop_id)]
        if journal_id:
            domain += [('journal_id', '=', journal_id)]
        if pawn_rule_id:
            domain += [('rule_id', '=', pawn_rule_id)]
        report_ids = Report.search(cr, uid, domain)
        report = Report.browse(cr, uid, report_ids)

        # Update Context
        self.localcontext.update({
            'pawn_shop': pawn_shop,
            'report': report,
        })

        return super(PawnJo6ReportXLSParser, self).set_context(
            objects, data, report_ids, report_type=report_type)


class PawnJo6ReportXLS(report_xls):
    column_sizes = [x[1] for x in COLUMN_SIZES]

    def xls_write_row(self, ws, row_pos, row_data,
                      row_style=default_style, set_column_size=False, row_merge=1):
        r = ws.row(row_pos)
        for col, size, spec in row_data:
            data = spec[4]
            formula = spec[5].get('formula') and \
                xlwt.Formula(spec[5]['formula']) or None
            style = spec[6] and spec[6] or row_style
            if not data:
                # if no data, use default values
                data = report_xls.xls_types_default[spec[3]]
            if size != 1 or row_merge != 1:
                if formula:
                    ws.write_merge(
                        row_pos, row_pos + row_merge - 1, col, col + size - 1, data, style)
                else:
                    ws.write_merge(
                        row_pos, row_pos + row_merge - 1, col, col + size - 1, data, style)
            else:
                if formula:
                    ws.write(row_pos, col, formula, style)
                else:
                    spec[5]['write_cell_func'](r, col, data, style)
            if set_column_size:
                ws.col(col).width = spec[2] * 256
        return row_pos + row_merge

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        ws = wb.add_sheet(_p.report_name[:31])
        ws.panes_frozen = True
        ws.remove_splits = True
        ws.portrait = 0  # Landscape
        ws.fit_width_to_pages = 1
        row_pos = 0

        # set print header/footer
        ws.header_str = self.xls_headers['standard']
        ws.footer_str = self.xls_footers['standard']

        # Header
        header_style = xlwt.easyxf('font: name Helvetica, bold true, height {};align: vert center;'.format(FONT_SIZE) + _xs['center'])
        c_specs = [
            ('header_1', 10, 0, 'text', _('บัญชีทรัพย์จำนำที่ผู้จำนำขาดส่งดอกเบี้ยเป็นเวลาเกินสี่เดือน')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=header_style)
        c_specs = [
            ('header_2', 10, 0, 'text', _('โรงรับจำนำ {} {}'.decode('utf-8')).format(_p.pawn_shop.name, _p.pawn_shop.company_id.name)),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=header_style)
        c_specs = [
            ('header_3', 10, 0, 'text', _('ใบอนุญาต เล่มที่ {} เลขที่ {}'.decode('utf-8')).format(_p.pawn_shop.reg_book, _p.pawn_shop.reg_number)),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=header_style)

        # Set Column Size
        c_sizes = self.column_sizes
        c_specs = [('empty_{}'.format(i + 1), 1, c_sizes[i], 'text', None)
                   for i in range(0, len(c_sizes))]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, set_column_size=True)
        for i in range(row_pos + 1):
            ws.row(i).height_mismatch = True
            ws.row(i).height = ROW_HEIGHT
        ws.set_horz_split_pos(row_pos + 2)

        # Column Header
        border_style = 'borders: left thin, right thin, top thin, bottom thin, left_colour black, right_colour black, top_colour black, bottom_colour black;'
        col_header_style = xlwt.easyxf('font: name Helvetica, height {};align: vert center;'.format(FONT_SIZE) + border_style + _xs['center'])
        c_specs = [
            ('number', 1, 0, 'text', _('เลขที่'), None, col_header_style),
            ('date_order', 1, 0, 'text', _('วัน เดือน ปี ที่รับจำนำ'), None, col_header_style),
            ('pawn_number', 1, 0, 'text', _('หมายเลข ตั๋วรับจำนำ'), None, col_header_style),
            ('customer_name', 1, 0, 'text', _('ชื่อผู้จำนำ'), None, col_header_style),
            ('customer_address', 1, 0, 'text', _('ที่อยู่ของผู้จำนำ'), None, col_header_style),
            ('item_description', 1, 0, 'text', _('ทรัพย์จำนำ'), None, col_header_style),
            ('item_qty', 1, 0, 'text', _('จำนวน'), None, col_header_style),
            ('total_baht', 1, 0, 'text', _('บาท'), None, col_header_style),
            ('total_satang', 1, 0, 'text', _('ส.ต.'), None, col_header_style),
            ('note', 1, 0, 'text', _('หมายเหตุ'), None, col_header_style),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_merge=2)

        # Column Detail
        col_detail_format = 'font: name Helvetica, height {};alignment: wrap True;'.format(FONT_SIZE) + border_style + _xs['top']
        col_center_detail_style = xlwt.easyxf(col_detail_format + _xs['center'])
        col_right_detail_style = xlwt.easyxf(col_detail_format + _xs['right'])
        col_left_detail_style = xlwt.easyxf(col_detail_format + _xs['left'])
        col_center_date_detail_style = xlwt.easyxf(col_detail_format + _xs['center'], num_format_str='DD/MM/YYYY')
        pawn_orders = sorted(_p.report, key=lambda x: (x.date_expired, x.name))
        for i, po in enumerate(pawn_orders):
            po_lines = sorted(po.order_line, key=lambda x: x.id)
            ws.row(i).height_mismatch = True
            ws.row(row_pos).height = ROW_HEIGHT * len(po_lines)
            item_description_list = []
            item_qty_list = []
            for po_line in po_lines:
                # Item Description
                item_desc = '{} {:.3f} {}'.decode('utf-8').format(po_line.name, po_line.product_qty, po_line.product_uom.name)
                if po_line.carat:
                    item_desc = '{} {:.2f} กะรัต'.decode('utf-8').format(item_desc, po_line.carat)
                if po_line.gram:
                    item_desc = '{} {:.2f} กรัม'.decode('utf-8').format(item_desc, po_line.gram)
                item_description_list.append(item_desc)
                # Item QTY
                item_qty_list.append(po_line.product_qty)
            item_description = '\n'.join(item_description_list)
            item_qty = sum(item_qty_list)
            c_specs = [
                ('number', 1, 0, 'number', i + 1, None, col_center_detail_style),
                ('date_order', 1, 0, 'date', (
                    datetime.datetime.strptime(po.date_order, '%Y-%m-%d').date() + relativedelta(years=543)), None, col_center_date_detail_style),
                ('pawn_number', 1, 0, 'number', po.name[2:], None, col_right_detail_style),
                ('customer_name', 1, 0, 'text', po.partner_id.name, None, col_left_detail_style),
                ('customer_address', 1, 0, 'text', po.partner_id.address_full or None, None, col_left_detail_style),
                ('item_description', 1, 0, 'text', item_description, None, col_left_detail_style),
                ('item_qty', 1, 0, 'number', item_qty, None, col_center_detail_style),
                ('total_baht', 1, 0, 'number', int(po.amount_pawned), None, col_right_detail_style),
                ('total_satang', 1, 0, 'number', int(round(po.amount_pawned - int(po.amount_pawned), 2) * 100), None, col_center_detail_style),
                ('note', 1, 0, 'text', None, None, col_left_detail_style),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)


PawnJo6ReportXLS(
    'report.pawn_jor6_report_xls',
    'pawn.order',
    parser=PawnJo6ReportXLSParser,
)
