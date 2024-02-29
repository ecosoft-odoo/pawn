# -*- coding: utf-8 -*-
# © 2024 Ecosoft (ecosoft.co.th).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.osv import osv, fields


class ResCountryProvince(osv.osv):

    _name = "res.country.province"
    _description = "Provinces"

    _columns = {
        "name": fields.char(
            string="Province",
            required=True,
        ),
        "country_id": fields.many2one(
            "res.country",
            string="Country",
            required=True,
        ),
    }


class ResCountryDistrict(osv.osv):

    _name = "res.country.district"
    _description = "Districts"

    _columns = {
        "name": fields.char(
            string="District",
            required=True,
        ),
        "province_id": fields.many2one(
            "res.country.province",
            string="Province",
            required=True,
        ),
    }


class ResCountryTownship(osv.osv):

    _name = "res.country.township"
    _description = "Township"

    _columns = {
        "name": fields.char(
            string="Township",
            required=True,
        ),
        "district_id": fields.many2one(
            "res.country.district",
            string="District",
            required=True,
        ),
        "zip": fields.char(
            string="Zip",
        ),
        "province_id": fields.related(
            "district_id",
            "province_id",
            type="many2one",
            relation="res.country.province",
            string="Province",
            readonly=True,
            store=True,
        ),
        "country_id": fields.related(
            "district_id",
            "province_id",
            "country_id",
            type="many2one",
            relation="res.country",
            string="Country",
            readonly=True,
            store=True,
        ),
    }
