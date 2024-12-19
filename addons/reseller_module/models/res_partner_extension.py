from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    reseller_partner_ids = fields.Many2many(
        'reseller.partner',  # Nombre del modelo relacionado
        'reseller_partner_res_partner_rel',  # Nombre de la tabla intermedia
        'partner_id',        # Nombre del campo en la tabla intermedia que apunta a 'res.partner'
        'reseller_partner_id',  # Nombre del campo en la tabla intermedia que apunta a 'reseller.partner'
        string='Reseller Partners'
    )
    name = fields.Char(default='Sin nombre')
    phone = fields.Char(default=None)

