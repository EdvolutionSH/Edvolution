from odoo import models, fields

class ResellerPartner(models.Model):
    _inherit = 'reseller.partner'

    reseller_subscription_ids = fields.Many2many(
        'reseller.subscription',  # Nombre del modelo relacionado
        'reseller_subscription_reseller_partner_rel',  # Nombre de la tabla intermedia
        'reseller_id',        # Nombre del campo en la tabla intermedia que apunta a 'reseller.partner'
        'reseller_subscription_id',  # Nombre del campo en la tabla intermedia que apunta a 'reseller.subscription'
        string='Reseller Partners'
    )