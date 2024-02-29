# -*- coding: utf-8 -*-
# © 2024 Ecosoft (ecosoft.co.th).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Pawnshop :: Partner Address in Thai",
    "version": "7.0.1.0.0",
    "category": "Hidden",
    "author": "Ecosoft",
    "website": "https://ecosoft.co.th/",
    "depends": ["pawnshop"],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "data/res.country.province.csv",
        "data/res.country.district.csv",
        "data/res.country.township.csv",
        "views/res_country_view.xml",
        "views/res_partner_view.xml",
    ],
    "installable": True,
    "auto_install": False,
}
