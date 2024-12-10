from odoo import models, fields
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class ResellerModule(models.Model):
    
    _name = 'reseller.module'    
    _description = 'Reseller Contact Sync'

    name = fields.Char(string="Reseller Name")  # Campo para identificar el módulo
    contact_ids = fields.One2many(
        comodel_name='res.partner',  # Modelo relacionado
        inverse_name='reseller_id',  # Campo inverso en res.partner
        string='Contactos'
    )
    status = fields.Selection([
        ('vigente', 'Vigente'),
        ('vencida', 'Vencida'),
        ('por_vencer', 'Por Vencer'),
    ], string='Estado', required=True, default='vigente')
    start_date = fields.Date(string='Fecha de Inicio')
    end_date = fields.Date(string='Fecha de Fin')

    contact_total = fields.Integer(string="Total de Contactos")

    @api.model
    def default_get(self, fields_list):
        res = super(ResellerModule, self).default_get(fields_list)
        total_contacts = self.env['res.partner'].search_count([])
        res.update({'contact_total': total_contacts})
        return res

    
    # name = fields.Char('Nombre', required=True)
    # address = fields.Char('Dirección')
    # phone = fields.Char('Teléfono', required=True)
    # domain = fields.Char('Dominio')
    # email = fields.Char('Correo Electrónico')
    # additional_email = fields.Char('Correo adicional')
    # sku = fields.Char('Sku')
    # expiration = fields.Date('Vigencia') # Revisar cuál es el tipo de vigencia
    # expiration = fields.Integer('Vigencia')
    # admin_name = fields.Char('Contacto Administrador de consola')
    # admin_email = fields.Char('Correo Administrador de consola')    
    # it_name = fields.Char('Contacto de TI')
    # it_email = fields.Char('Correo de TI')
    # director_name = fields.Char('Contacto del Director / Rector')
    # director_email = fields.Char('Correo del Director / Rector')
    # type = fields.Selection(
    #     string='Tipo de contacto',
    #     selection=[('company', 'Empresa'), ('personal', 'Personal')],
    #     help="Type is used to separate Companies and Personal Opportunities")
    # sync_date = fields.Datetime(string='Fecha de sincronización', default=fields.Datetime.now)
    
    
    def authenticate_service_account(self):
        """Autentica la service account para acceder a la API"""
        credentials_path = "sa-reseller.json"  # Reemplaza con la ruta real
        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            service = build('reseller', 'v1', credentials=credentials)
            return service
        except Exception as e:
            _logger.error(f"Error al autenticar: {e}")
            return None

    def fetch_contacts(self):
        """Obtiene la lista de contactos de la API y devuelve los datos"""
        service = self.authenticate_service_account()
        if not service:
            return []
        try:
            # Reemplaza `partners().list()` con el endpoint correcto
            request = service.partners().list()
            response = request.execute()
            return response.get('contacts', [])
        except Exception as e:
            _logger.error(f"Error al obtener contactos: {e}")
            return []

    # def sync_contacts(self):
    #     """Sincroniza contactos con la base de datos de Odoo"""
    #     contacts = self.fetch_contacts()
    #     print(contacts)
    #     if not contacts:
    #         return
    #     for contact in contacts:
    #         partner = self.env['res.partner'].search([('email', '=', contact['email'])], limit=1)
    #         if partner:
    #             partner.write({
    #                 'name': contact['name'],
    #                 'phone': contact['phone'],
    #             })
    #         else:
    #             self.env['res.partner'].create({
    #                 'name': contact['name'],
    #                 'email': contact['email'],
    #                 'phone': contact['phone'],
    #             })
        
    def sync_contacts(self):
        """Sincroniza contactos con la base de datos de Odoo"""
        contacts = self.fetch_contacts()
        _logger.info("Contactos obtenidos: %s", contacts)  # Esto imprimirá los contactos en el log
        # if not contacts:
        #     return
        # for contact in contacts:
        #     _logger.info("Sincronizando contacto: %s", contact)  # Imprime cada contacto
        #     partner = self.env['res.partner'].search([('email', '=', contact['email'])], limit=1)
        #     if partner:
        #         partner.write({
        #             'name': contact['name'],
        #             'phone': contact['phone'],
        #         })
        #         _logger.info("Contacto actualizado: %s", partner)  # Imprime el contacto actualizado
        #     else:
        #         self.env['res.partner'].create({
        #             'name': contact['name'],
        #             'email': contact['email'],
        #             'phone': contact['phone'],
        #         })
        #         _logger.info("Nuevo contacto creado: %s", contact)  # Imprime el nuevo contacto creado

class ResPartner(models.Model):
    _inherit = 'res.partner'

    reseller_id = fields.Many2one(
        comodel_name='reseller.module',
        string='Reseller Module'
    )

    contactos_odoos = fields.Many2many('res.partner', string="Contactos en Odoo", compute="_compute_contactos_odoos")
    contactos_reseller_console = fields.Many2many('res.partner', string="Contactos Sincronizados", compute="_compute_contactos_reseller_console")

    def _compute_contactos_odoo(self):
        # Obtener todos los contactos en el sistema
        for partner in self:
            partner.contactos_odoo = self.env['res.partner'].search([])  # Todos los contactos

    def _compute_contactos_reseller_console(self):
        # Obtener contactos etiquetados con "reseller console"
        for partner in self:
            reseller_tag = self.env.ref('your_module.reseller_console_tag')  # Reemplaza con el ID correcto de la etiqueta
            partner.contactos_reseller_console = self.env['res.partner'].search([('category_id', 'in', reseller_tag.ids)])
    
    