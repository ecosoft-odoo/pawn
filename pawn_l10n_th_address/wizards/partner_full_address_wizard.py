# -*- coding: utf-8 -*-
# © 2024 Ecosoft (ecosoft.co.th).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.osv import osv, fields


class PartnerFullAddressWizard(osv.osv_memory):
    _name = "partner.full.address.wizard"

    _columns = {
        "address_full": fields.text(
            string="Full Address",
            readonly=True,
        )
    }
