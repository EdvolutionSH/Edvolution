# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class reseller_module(models.Model):
#     _name = 'reseller_module.reseller_module'
#     _description = 'reseller_module.reseller_module'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
# contact_ids = fields.One2many(
#     comodel_name='res.partner',  # Modelo relacionado
#     inverse_name='reseller_id',  # Campo inverso en res.partner
#     string='Contactos'
# )