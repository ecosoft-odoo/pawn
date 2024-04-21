# -*- coding: utf-8 -*-
# © 2024 Ecosoft (ecosoft.co.th).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.osv import osv, fields


ADDRESS_FIELDS = ["street", "township", "district", "province", "zip"]

PREFIX_TOWNSHIP = ["ต.", "ข.", "ตำบล.", "แขวง.", "ตำบล", "แขวง"]

PREFIX_DISTRICT = ["อ.", "ข.", "อำเภอ.", "เขต.", "อำเภอ", "เขต"]

PREFIX_PROVINCE = ["จ.", "จังหวัด.", "จังหวัด"]


def encode_utf8(val):
    return val.encode("utf-8")


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
    }

    def _remove_whitespaces_address_field(self, vals):
        for field in ADDRESS_FIELDS:
            if vals.get(field):
                vals[field] = vals[field].strip()
        return vals

    def _remove_prefix_address_field(self, address_field, prefix=[]):
        af = address_field
        for pf in prefix:
            if address_field.startswith(pf):
                af = address_field[len(pf):].strip()
                break
        return af

    def _update_address_full(self, cr, uid, partner_id, context=None):
        partner = self.browse(cr, uid, partner_id, context=context)
        address_list = []
        for field in ADDRESS_FIELDS:
            if partner[field]:
                address_field = encode_utf8(partner[field])
                if field in ["street", "zip"]:
                    address_list.append(address_field)
                elif field == "township":
                    township = self._remove_prefix_address_field(address_field, prefix=PREFIX_TOWNSHIP)
                    prefix = "ต."
                    if partner["province"] and any([x in encode_utf8(partner["province"]) for x in ["กทม", "กรุงเทพ"]]):
                        prefix = "แขวง"
                    address_list.append("{}{}".format(prefix, township))
                elif field == "district":
                    district = self._remove_prefix_address_field(address_field, prefix=PREFIX_DISTRICT)
                    prefix = "อ."
                    if partner["province"] and any([x in encode_utf8(partner["province"]) for x in ["กทม", "กรุงเทพ"]]):
                        prefix = "เขต"
                    address_list.append("{}{}".format(prefix, district))
                elif field == "province":
                    province = self._remove_prefix_address_field(address_field, prefix=PREFIX_PROVINCE)
                    prefix = "จ."
                    if partner["province"] and any([x in encode_utf8(partner["province"]) for x in ["กทม", "กรุงเทพ"]]):
                        prefix = ""
                    address_list.append("{}{}".format(prefix, province))
        address_full = " ".join(address_list) or False
        self.write(cr, uid, [partner_id], {"address_full": address_full}, context=context)
        return True

    def create(self, cr, uid, vals, context=None):
        # Remove leading and trailing whitespaces on address field
        vals = self._remove_whitespaces_address_field(vals)
        # Remove prefix on address field
        if vals.get("township"):
            vals["township"] = self._remove_prefix_address_field(encode_utf8(vals["township"]), prefix=PREFIX_TOWNSHIP)
        if vals.get("district"):
            vals["district"] = self._remove_prefix_address_field(encode_utf8(vals["district"]), prefix=PREFIX_DISTRICT)
        if vals.get("province"):
            vals["province"] = self._remove_prefix_address_field(encode_utf8(vals["province"]), prefix=PREFIX_PROVINCE)
            # Replace province if province is bangkok
            if any([x in vals["province"] for x in ["กทม", "กรุงเทพ"]]):
                vals["province"] = "กทม"
        # Create partner
        partner_id = super(ResPartner, self).create(cr, uid, vals, context=context)
        # Update address full
        self._update_address_full(cr, uid, partner_id, context=context)
        return partner_id

    def write(self, cr, uid, ids, vals, context=None):
        # Remove leading and trailing whitespaces on address field
        vals = self._remove_whitespaces_address_field(vals)
        # Remove prefix on address field
        if vals.get("township"):
            vals["township"] = self._remove_prefix_address_field(encode_utf8(vals["township"]), prefix=PREFIX_TOWNSHIP)
        if vals.get("district"):
            vals["district"] = self._remove_prefix_address_field(encode_utf8(vals["district"]), prefix=PREFIX_DISTRICT)
        if vals.get("province"):
            vals["province"] = self._remove_prefix_address_field(encode_utf8(vals["province"]), prefix=PREFIX_PROVINCE)
            # Replace province if province is bangkok
            if any([x in vals["province"] for x in ["กทม", "กรุงเทพ"]]):
                vals["province"] = "กทม"
        # Update partner
        res = super(ResPartner, self).write(cr, uid, ids, vals, context=context)
        # Update address full
        if any([field in vals for field in ADDRESS_FIELDS]):
            for partner_id in ids:
                self._update_address_full(cr, uid, partner_id, context=context)
        return res

    def view_full_address(self, cr, uid, partner_ids, context=None):
        partner = self.browse(cr, uid, partner_ids[0], context=context)
        mod_obj = self.pool.get("ir.model.data")
        act_obj = self.pool.get("ir.actions.act_window")
        result = mod_obj.get_object_reference(cr, uid, "pawn_l10n_th_address", "action_partner_full_address_wizard")
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result["context"] = {"default_address_full": partner.address_full}
        return result
