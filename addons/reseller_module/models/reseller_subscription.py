from odoo import models, fields

class ResellerSubscription(models.Model):
    _name = 'reseller.subscription'  # Nombre técnico del modelo
    _description = 'Suscripciones de Reseller'  # Descripción del modelo

    name = fields.Char(string='Nombre de la Suscripción', required=True)
    status = fields.Selection([
        ('vigente', 'Vigente'),
        ('vencida', 'Vencida'),
        ('por_vencer', 'Por Vencer'),
    ], string='Estado', required=True, default='vigente')
    start_date = fields.Date(string='Fecha de Inicio')
    end_date = fields.Date(string='Fecha de Fin')
