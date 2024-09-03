# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp


class account_account(osv.osv):
    
    _inherit = 'account.account'
    
    def manual_compute(self, cr, uid, ids, fields_names, context=None):
        return self.__compute(cr, uid, ids, fields_names, None, context=context)
    
    # Method overwrite, to make sure that the 'pawn_shop_id' and 'profit_center' is included
    def __compute(self, cr, uid, ids, field_names, arg=None, context=None,
                  query='', query_params=()):
        """ compute the balance, debit and/or credit for the provided
        account ids
        Arguments:
        `ids`: account ids
        `field_names`: the fields to compute (a list of any of
                       'balance', 'debit' and 'credit')
        `arg`: unused fields.function stuff
        `query`: additional query filter (as a string)
        `query_params`: parameters for the provided query string
                        (__compute will handle their escaping) as a
                        tuple
        """
        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
            'debit': "COALESCE(SUM(l.debit), 0) as debit",
            'credit': "COALESCE(SUM(l.credit), 0) as credit",
            # by convention, foreign_balance is 0 when the account has no secondary currency, because the amounts may be in different currencies
            'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
        }
        
        # kittiu:
        pawn_shop_id = context.get('pawn_shop_id', False)
        profit_center = context.get('profit_center', False)
        # --
        
        #get all the necessary accounts
        children_and_consolidated = self._get_children_and_consol(cr, uid, ids, context=context)
        #compute for each account the balance/debit/credit from the move lines
        accounts = {}
        res = {}
        null_result = dict((fn, 0.0) for fn in field_names)
        if children_and_consolidated:
            aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)

            wheres = [""]
            if query.strip():
                wheres.append(query.strip())
            if aml_query.strip():
                wheres.append(aml_query.strip())
            # kittiu:
            if pawn_shop_id:
                wheres.append("pawn_shop_id = %s" % pawn_shop_id)
            if profit_center:
                wheres.append("profit_center = %s" % profit_center)
            # --
            filters = " AND ".join(wheres)
            # --
            # IN might not work ideally in case there are too many
            # children_and_consolidated, in that case join on a
            # values() e.g.:
            # SELECT l.account_id as id FROM account_move_line l
            # INNER JOIN (VALUES (id1), (id2), (id3), ...) AS tmp (id)
            # ON l.account_id = tmp.id
            # or make _get_children_and_consol return a query and join on that
            request = ("SELECT l.account_id as id, " +\
                       ', '.join(mapping.values()) +
                       " FROM account_move_line l" \
                       " WHERE l.account_id IN %s " \
                            + filters +
                       " GROUP BY l.account_id")
            params = (tuple(children_and_consolidated),) + query_params
            cr.execute(request, params)

            for row in cr.dictfetchall():
                accounts[row['id']] = row

            # consolidate accounts with direct children
            children_and_consolidated.reverse()
            brs = list(self.browse(cr, uid, children_and_consolidated, context=context))
            sums = {}
            currency_obj = self.pool.get('res.currency')
            while brs:
                current = brs.pop(0)
#                can_compute = True
#                for child in current.child_id:
#                    if child.id not in sums:
#                        can_compute = False
#                        try:
#                            brs.insert(0, brs.pop(brs.index(child)))
#                        except ValueError:
#                            brs.insert(0, child)
#                if can_compute:
                for fn in field_names:
                    sums.setdefault(current.id, {})[fn] = accounts.get(current.id, {}).get(fn, 0.0)
                    for child in current.child_id:
                        if child.company_id.currency_id.id == current.company_id.currency_id.id:
                            sums[current.id][fn] += sums[child.id][fn]
                        else:
                            sums[current.id][fn] += currency_obj.compute(cr, uid, child.company_id.currency_id.id, current.company_id.currency_id.id, sums[child.id][fn], context=context)

                # as we have to relay on values computed before this is calculated separately than previous fields
                if current.currency_id and current.exchange_rate and \
                            ('adjusted_balance' in field_names or 'unrealized_gain_loss' in field_names):
                    # Computing Adjusted Balance and Unrealized Gains and losses
                    # Adjusted Balance = Foreign Balance / Exchange Rate
                    # Unrealized Gains and losses = Adjusted Balance - Balance
                    adj_bal = sums[current.id].get('foreign_balance', 0.0) / current.exchange_rate
                    sums[current.id].update({'adjusted_balance': adj_bal, 'unrealized_gain_loss': adj_bal - sums[current.id].get('balance', 0.0)})

            for id in ids:
                res[id] = sums.get(id, null_result)
        else:
            for id in ids:
                res[id] = null_result
        return res

    # Method overwrite, to make sure that the 'pawn_shop_id' and 'profit_center' is included
    def _set_credit_debit(self, cr, uid, account_id, name, value, arg, context=None):
        if context.get('config_invisible', True):
            return True
        # kittiu:
        pawn_shop_id = context.get('pawn_shop_id', False)
        profit_center = context.get('profit_center', False)
        # --
        account = self.browse(cr, uid, account_id, context=context)
        diff = value - getattr(account,name)
        if not diff:
            return True

        journal_obj = self.pool.get('account.journal')
        jids = journal_obj.search(cr, uid, [('type','=','situation'),('centralisation','=',1),('company_id','=',account.company_id.id)], context=context)
        if not jids:
            raise osv.except_osv(_('Error!'),_("You need an Opening journal with centralisation checked to set the initial balance."))

        period_obj = self.pool.get('account.period')
        pids = period_obj.search(cr, uid, [('special','=',True),('company_id','=',account.company_id.id)], context=context)
        if not pids:
            raise osv.except_osv(_('Error!'),_("There is no opening/closing period defined, please create one to set the initial balance."))

        move_obj = self.pool.get('account.move.line')
        # kittiu:
        filters = [
                ('journal_id','=',jids[0]),
                ('period_id','=',pids[0]),
                ('account_id','=', account_id),
                (name,'>', 0.0),
                ('name','=', _('Opening Balance'))
            ]
        if pawn_shop_id:
            filters.append(('pawn_shop_id','=',pawn_shop_id))
        if profit_center:
            filters.append(('profit_center','=',profit_center))
        # --
        move_id = move_obj.search(cr, uid, filters, context=context)
        if move_id:
            move = move_obj.browse(cr, uid, move_id[0], context=context)
            move_obj.write(cr, uid, move_id[0], {
                name: diff+getattr(move,name)
            }, context=context)
        else:
            if diff<0.0:
                raise osv.except_osv(_('Error!'),_("Unable to adapt the initial balance (negative value)."))
            nameinv = (name=='credit' and 'debit') or 'credit'
            move_id = move_obj.create(cr, uid, {
                'name': _('Opening Balance'),
                'account_id': account_id,
                'journal_id': jids[0],
                'period_id': pids[0],
                name: diff,
                nameinv: 0.0,
                # kittiu:
                'pawn_shop_id': pawn_shop_id,
                'profit_center': profit_center,
                # --
            }, context=context)
        return True
    
    _columns = {
        'balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Balance', multi='balance'),
        'credit': fields.function(__compute, fnct_inv=_set_credit_debit, digits_compute=dp.get_precision('Account'), string='Credit', multi='balance'),
        'debit': fields.function(__compute, fnct_inv=_set_credit_debit, digits_compute=dp.get_precision('Account'), string='Debit', multi='balance'),
        'foreign_balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Foreign Balance', multi='balance',
                                           help="Total amount (in Secondary currency) for transactions held in secondary currency for this account."),
        'adjusted_balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Adjusted Balance', multi='balance',
                                            help="Total amount (in Company currency) for transactions held in secondary currency for this account."),
        'unrealized_gain_loss': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Unrealized Gain or Loss', multi='balance',
                                                help="Value of Loss or Gain due to changes in exchange rate when doing multi-currency transactions."),
    }

    
account_account()

class account_journal(osv.osv):

    _inherit = 'account.journal'

    _columns = {
        'profit_center': fields.selection([(1, '1'), (2, '2')], 'Profit Center', help="Profit Center will be posted in account move line"),
        'pawn_journal': fields.boolean('Pawn Journal'),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'active': True,
    }

account_journal()

class account_move(osv.osv):
    
    _inherit = 'account.move'

    def _get_shop(self, cr, uid, ids, name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for move in self.browse(cr, uid, ids, context=context):
            for line in move.line_id:
                res[move.id] = line.pawn_shop_id and line.pawn_shop_id.id or False
                if res[move.id]:
                    break;
        return res
 
    def _search_shop(self, cr, uid, obj, name, args, context=None):
        if not len(args):
            return []
        key = isinstance(args[0][2], int) and 'id' or 'name'
        shop_ids = self.pool.get('pawn.shop').search(cr, uid, [(key, args[0][1], args[0][2])])
        if not shop_ids:
            shop_ids = [0]
        cr.execute("""
            select m.id from account_move m
            join account_move_line ml on m.id = ml.move_id
            where pawn_shop_id in %s;
        """, (tuple(shop_ids),))
        res = cr.fetchall()
        ids = [('id', 'in', map(lambda x: x[0], res))]
        return ids

    _columns={
        'pawn_shop_id' : fields.function(_get_shop, fnct_search=_search_shop, string='Shop', type='many2one', relation='pawn.shop'),
        'adjustment': fields.selection([('pawn', 'Pawn'), ('redeem', 'Redeem'), ('sale_receipt', 'Sale Receipt')], 'Adjustment'),
    }

account_move()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
