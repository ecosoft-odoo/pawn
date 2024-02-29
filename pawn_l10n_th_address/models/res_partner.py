# -*- coding: utf-8 -*-
# © 2024 Ecosoft (ecosoft.co.th).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.osv import osv, fields


class ResPartner(osv.osv):

    _inherit = "res.partner"

    _columns = {
        "province_id": fields.many2one(
            "res.country.province",
            domain="[('country_id','=',country_id)]",
            ondelete="restrict",
        ),
        "district_id": fields.many2one(
            "res.country.district",
            domain="[('province_id','=',province_id)]",
            ondelete="restrict",
        ),
        "township_id": fields.many2one(
            "res.country.township",
            domain="[('district_id','=',district_id)]",
            ondelete="restrict",
        ),
    }

    def onchange_country_id(self, cr, uid, ids, country_id, context=None):
        return {"value": {"province_id": False}}

    def onchange_province_id(self, cr, uid, ids, province_id, context=None):
        return {"value": {"district_id": False}}

    def onchange_district_id(self, cr, uid, ids, district_id, context=None):
        return {"value": {"township_id": False}}

    def onchange_township_id(self, cr, uid, ids, township_id, context=None):
        if township_id:
            township = self.pool.get("res.country.township").browse(cr, uid, township_id, context=context)
            return {"value": {"zip": township.zip}}
        return {"value": {"zip": False}}

    def create(self, cr, uid, vals, context=None):
        address_list = []
        if vals.get("street"):
            address_list.append(vals["street"])
        if vals.get("township_id"):
            township = self.pool.get("res.country.township").browse(cr, uid, vals["township_id"], context=context)
            address_list.append(township.name)
        if vals.get("district_id"):
            district = self.pool.get("res.country.district").browse(cr, uid, vals["district_id"], context=context)
            address_list.append(district.name)
        if vals.get("province_id"):
            province = self.pool.get("res.country.province").browse(cr, uid, vals["province_id"], context=context)
            address_list.append(province.name)
        if vals.get("zip"):
            address_list.append(vals["zip"])
        vals["address_full"] = " ".join(address_list)
        return super(ResPartner, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        res = super(ResPartner, self).write(cr, uid, ids, vals, context=context)
        if vals.get("street") or vals.get("township_id") or vals.get("district_id") or vals.get("province_id") or vals.get("zip"):
            partners = self.browse(cr, uid, ids, context=context)
            for partner in partners:
                address_list = []
                if partner.street:
                    address_list.append(partner.street)
                if partner.township_id:
                    address_list.append(partner.township_id.name)
                if partner.district_id:
                    address_list.append(partner.district_id.name)
                if partner.province_id:
                    address_list.append(partner.province_id.name)
                if partner.zip:
                    address_list.append(partner.zip)
                self.write(cr, uid, [partner.id], {"address_full": " ".join(address_list)}, context=context)
        return res
