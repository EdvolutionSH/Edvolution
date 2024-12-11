from odoo import models, fields

class ResellerPartner(models.Model):
    _name = 'reseller.partner'    
    _description = 'Reseller Contact Table'
    
    name = fields.Char('Nombre consola')
    org_display_name = fields.Char('Nombre de la Organización')
    region_code = fields.Char('Código del país')
    postal_code = fields.Char('Código Postal')
    administrative_area = fields.Char('Estado')
    locality = fields.Char('Ciudad')
    sublocality = fields.Char('')
    address = fields.Char('Dirección')
    address_line_1 = fields.Char('Dirección línea 1')
    address_line_2 = fields.Char('Dirección línea 2')
    address_line_3 = fields.Char('Dirección línea 3')
    organization = fields.Char('Organización')
    first_name = fields.Char('Nombre del contacto')
    last_name = fields.Char('Apellido del contacto')
    display_name = fields.Char('Nombre')
    email = fields.Char('Correo Electrónico')
    phone = fields.Char('Teléfono')
    alternate_email = fields.Char('Correo adicional')
    domain = fields.Char('Dominio')
    created_at = fields.Datetime(string='Fecha de creación', default=fields.Datetime.now)
    cloud_identity_id = fields.Char('ID de identidad')
    language_code = fields.Char('Código de idioma')
    sync_date = fields.Datetime(string='Fecha de sincronización', default=fields.Datetime.now)
    partner_ids = fields.Many2many(
        'res.partner',  # Nombre del modelo relacionado
        'reseller_partner_res_partner_rel',  # Nombre de la tabla intermedia
        'reseller_partner_id',  # Nombre del campo en la tabla intermedia que apunta a 'reseller.partner'
        'partner_id',           # Nombre del campo en la tabla intermedia que apunta a 'res.partner'
        string='Related Partners'
    )
