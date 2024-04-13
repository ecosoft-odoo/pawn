# -*- coding: utf-8 -*-
# © 2024 Ecosoft (ecosoft.co.th).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.osv import osv, fields


class ResPartner(osv.osv):

    _inherit = "res.partner"

    _columns = {
        "province": fields.char(
            string="Province",
        ),
        "district": fields.char(
            string="District",
        ),
        "township": fields.char(
            string="Township",
        ),
        "is_done_address": fields.boolean(
            string="Is Done Address",
        )
    }

    def _update_address_full(self, cr, uid, partner_id, context=None):
        cr.execute("""
            SELECT
                TRIM(
                   -- Street
                   (
                    CASE WHEN TRIM(COALESCE(street, '')) = '' THEN '' ELSE
                        ' ' || TRIM(COALESCE(street, '')) END
                   ) ||
                   -- Township
                   (
                    CASE WHEN TRIM(COALESCE(township, '')) = '' THEN '' ELSE
                        ' ' || (
                            CASE
                                WHEN LEFT(TRIM(COALESCE(township, '')), 2) <> 'ต.' AND
                                     LEFT(TRIM(COALESCE(township, '')), 4) <> 'ตำบล' AND
                                     LEFT(TRIM(COALESCE(township, '')), 4) <> 'แขวง' THEN 'ตำบล' || TRIM(COALESCE(township, ''))
                                ELSE TRIM(COALESCE(township, '')) END
                        ) END
                   ) ||
                   -- District
                   (
                    CASE WHEN TRIM(COALESCE(district, '')) = '' THEN '' ELSE
                        ' ' || (
                            CASE
                                WHEN LEFT(TRIM(COALESCE(district, '')), 2) <> 'อ.' AND
                                     LEFT(TRIM(COALESCE(district, '')), 5) <> 'อำเภอ' AND
                                     LEFT(TRIM(COALESCE(district, '')), 3) <> 'เขต' THEN 'อำเภอ' || TRIM(COALESCE(district, ''))
                                ELSE TRIM(COALESCE(district, '')) END
                        ) END
                   ) ||
                   -- Province
                   (
                    CASE WHEN TRIM(COALESCE(province, '')) = '' THEN '' ELSE
                        ' ' || (
                            CASE
                                WHEN LEFT(TRIM(COALESCE(province, '')), 2) <> 'จ.' AND
                                     LEFT(TRIM(COALESCE(province, '')), 7) <> 'จังหวัด' THEN 'จังหวัด' || TRIM(COALESCE(province, ''))
                                ELSE TRIM(COALESCE(province, '')) END
                        ) END
                   ) ||
                   -- Zip
                   (
                    CASE WHEN TRIM(COALESCE(zip, '')) = '' THEN '' ELSE
                        ' ' || TRIM(COALESCE(zip, '')) END
                   )
                ) AS address_full
            FROM res_partner
            WHERE id = %s
        """ % partner_id)
        self.write(cr, uid, partner_id, {"address_full": cr.fetchone()[0]}, context=context)
        return True

    def create(self, cr, uid, vals, context=None):
        partner_id = super(ResPartner, self).create(cr, uid, vals, context=context)
        self._update_address_full(cr, uid, partner_id, context=context)
        return partner_id

    def write(self, cr, uid, ids, vals, context=None):
        res = super(ResPartner, self).write(cr, uid, ids, vals, context=context)
        if "street" in vals or "township" in vals or "district" in vals or "province" in vals or "zip" in vals:
            for partner_id in ids:
                self._update_address_full(cr, uid, partner_id, context=context)
        return res
