import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from odoo import api, fields, models
import logging
from google.cloud import channel_v1
from google.cloud import channel
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError

_logger = logging.getLogger(__name__)

SERVICE_ACCOUNT_FILE = 'sa-reseller.json'
GOOGLE_RESELLER_ACCOUNT_ID = 'C01bjv6i2'
GOOGLE_RESELLER_ADMIN_USER = 'bernardo@edvolution.io'

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

    contact_total = fields.Integer(string="Contactos en Odoo", readonly=True)
    contact_synced = fields.Integer(string="Contactos Sincronizados", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(ResellerModule, self).default_get(fields_list)
        
        # Asegurarse de que res es un diccionario
        if not isinstance(res, dict):
            res = {}

        # Obtener el total de contactos
        total_contacts = self.env['res.partner'].search_count([])

        # Inicializar contactos sincronizados
        contacts_count = 0
        
        # Buscar la categoría y contar los contactos asociados
        partner_sales_category = self.env['res.partner.category'].search(
            [('name', '=', 'Partner Sales Console')], limit=1
        )
        if partner_sales_category:  
            contacts_count = self.env['res.partner'].search_count(
                [('category_id', '=', partner_sales_category.id)]
            )
        
        # Actualizar valores predeterminados
        res.update({
            'contact_total': total_contacts,
            'contact_synced': contacts_count,
        })
        return res

    
    def create_channel_service(self):
        """Autentica la service account para acceder a la API"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, 
                scopes=["https://www.googleapis.com/auth/apps.order"])
            
            # Set up credentials with user impersonation
            reseller_admin_user = GOOGLE_RESELLER_ADMIN_USER

            delegated_credentials = credentials.with_subject(reseller_admin_user)
            
            # Create the API client
            channel_service = channel.CloudChannelServiceClient(credentials=delegated_credentials)

            return channel_service

        except Exception as e:
            _logger.error(f"Error al autenticar: {e}")
            return None
        
    def create_admin_service(self):
        """Autentica la service account para acceder a la API"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, 
                scopes=["https://www.googleapis.com/auth/admin.directory.user"])
            
            # Set up credentials with user impersonation
            admin_user = GOOGLE_RESELLER_ADMIN_USER

            delegated_credentials = credentials.with_subject(admin_user)
            
            # Create the API client
            admin_service = build(
                serviceName='admin',
                version='directory_v1',
                credentials=delegated_credentials
            )
            
            return admin_service

        except Exception as e:
            _logger.error(f"Error al autenticar: {e}")
            return None
        
    def create_reseller_service(self):
        """Autentica la service account para acceder a la API"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, 
                scopes=["https://www.googleapis.com/auth/apps.order"])
            
            # Set up credentials with user impersonation
            reseller_admin_user = GOOGLE_RESELLER_ADMIN_USER

            delegated_credentials = credentials.with_subject(reseller_admin_user)
            
            # Create the API client
            reseller_service = build(
                serviceName='reseller',
                version='v1',
                credentials=delegated_credentials
            )

            return reseller_service

        except Exception as e:
            _logger.error(f"Error al autenticar: {e}")
            return None


    def fetch_contacts(self):
        """Obtiene la lista de contactos de la API y devuelve los datos"""
        service = self.create_channel_service()
        
        if not service:
            return []
        try:
            # Initialize request arguments
            request = channel_v1.ListCustomersRequest(
                parent=f"accounts/{GOOGLE_RESELLER_ACCOUNT_ID}",
            )

            # Make the request
            page_result = service.list_customers(request=request)

            return page_result
        
        except Exception as e:
            _logger.error(f"Error al obtener contactos: {e}")
            return []

        
    def sync_contacts(self):
        """Sincroniza contactos con la base de datos de Odoo"""
        try:
            # self.sync_subscriptions('C00qonywf')
            # return
            contacts = list(self.fetch_contacts())
            contact = contacts[0]

            record_count = self.env['reseller.partner'].search_count([])
            
            if not contacts:
                return

            category_ids = self.create_labels()
                
            for contact in contacts:
                name = getattr( contact, 'name', None)
                org_display_name = getattr( contact, 'org_display_name', None)            
                org_postal_address = getattr(contact, 'org_postal_address', None)
                
                if org_postal_address:
                    region_code = getattr(org_postal_address, 'region_code', None)
                    postal_code = getattr(org_postal_address, 'postal_code', None)
                    administrative_area = getattr(org_postal_address, 'administrative_area', None)
                    locality = getattr(org_postal_address, 'locality', None)
                    sublocality = getattr(org_postal_address, 'sublocality', None)
                    
                    address_lines = list(getattr(org_postal_address, 'address_lines', []))
                    
                    if len(address_lines) > 0:
                        address_line_1 = address_lines[0] if len(address_lines) > 0 else ""
                        address_line_2 = address_lines[1] if len(address_lines) > 1 else ""
                        address_line_3 = address_lines[2] if len(address_lines) > 2 else ""
                    else:
                        address_line_1 = ""
                        address_line_2 = ""
                        address_line_3 = ""
                
                    organization = getattr(org_postal_address, 'organization', None)
                else:
                    print("No se encontró información de contacto principal para este registro")
                
                primary_contact_info = getattr(contact, 'primary_contact_info', None)

                if primary_contact_info:
                    display_name = getattr(primary_contact_info, 'display_name', None)
                    first_name = getattr(primary_contact_info, 'first_name', None)
                    last_name = getattr(primary_contact_info, 'last_name', None)
                    email = getattr(primary_contact_info, 'email', None)
                    phone = getattr(primary_contact_info, 'phone', None)
                
                else:
                    print("No se encontró información de contacto principal para este registro")
                    
                alternate_email = getattr( contact, 'alternate_email', None)
                domain = getattr( contact, 'domain', None)
                cloud_identity_id = getattr( contact, 'cloud_identity_id', None)
                language_code = getattr( contact, 'language_code', None)        
                full_address_lines = address_line_1 + ' ' + address_line_2 + address_line_3
                
                full_address = address_line_1 + ' ' + address_line_2 + address_line_3 + ' ' + locality + ' ' + administrative_area + ' ' + postal_code + ' ' + region_code
                
                reseller_vals = {
                    'name': name,
                    'org_display_name': org_display_name,
                    'region_code': region_code,
                    'postal_code': postal_code,
                    'administrative_area': administrative_area,
                    'locality': locality,
                    'sublocality': sublocality,
                    'address': full_address_lines,
                    'address_line_1': address_line_1,
                    'address_line_2': address_line_2,
                    'address_line_3': address_line_3,
                    'organization': organization,
                    'first_name': first_name,
                    'last_name': last_name,
                    'display_name': display_name,
                    'email': email,
                    'phone': phone,
                    'alternate_email': alternate_email,
                    'domain': domain,
                    'cloud_identity_id': cloud_identity_id,
                    'language_code': language_code,
                }
                
                reseller_data = {k: v for k, v in reseller_vals.items() if v != ''}
                
                if record_count == 0:
                    reseller = self.env['reseller.partner'].create(reseller_data)
                    _logger.info("Nuevo contacto en tabla reseller_partner creado: %s", reseller)
                    
                else:
                    reseller = self.env['reseller.partner'].search([('name', '=', name)], limit=1)
                    
                    if reseller:
                        reseller.write(reseller_data)
                        _logger.info("Contacto en tabla reseller_partner actualizado: %s", reseller)
                    else:
                        reseller = self.env['reseller.partner'].create(reseller_data)
                        _logger.info("Nuevo contacto en tabla reseller_partner creado: %s", reseller)

                self.sync_subscriptions(reseller)
                # return
                
                # Company contact
                company_vals = {
                    'contact_address': full_address.strip(),
                    'country_code': region_code,
                    'date': '',
                    'display_name': org_display_name,
                    'name': org_display_name,
                    'commercial_company_name': org_display_name,
                    # 'lang': language_code,
                    'lang': 'en_US',
                    # 'phone': phone,
                    'website': domain,
                    'type': 'contact',
                    'is_company': True,
                    'zip': postal_code,
                    'street': address_line_1,
                    'street2': address_line_2,
                    'category_id': [(6, 0, category_ids)],
                }
                
                company_data = {k: v for k, v in company_vals.items() if v != ''}
                
                # Create company contact
                if record_count == 0:
                    company = self.env['res.partner'].create(company_data)
                    _logger.info("Nuevo contacto de compañia en tabla res_partner creado: %s", reseller)
                    
                else:
                    company = self.env['res.partner'].search([('name', '=', org_display_name)], limit=1)
                    
                    if company:
                        company.write(company_data)
                        _logger.info("Contacto de compañía en tabla res_partner actualizado: %s", company)
                    else:
                        company = self.env['res.partner'].create(company_data)
                        _logger.info("Contacto de compañia en tabla res_partner creado: %s", company)
                
                # Check if the relationship already exists before adding
                if company.id not in reseller.partner_ids.ids:
                    reseller.partner_ids = [(4, company.id)]
                    _logger.info("Relación de compañia creada con ID: %s", company.id)
                else:
                    _logger.info("La relación ya existe para la compañía con ID: %s", company.id)
                    
                # Personal contact
                personal_vals = {
                    'contact_address': full_address.strip(),
                    'country_code': region_code,
                    'date': '',
                    'display_name': display_name,
                    'name': display_name,
                    'email': email,
                    # 'lang': language_code,
                    'lang': 'en_US',
                    'phone': phone,
                    'website': domain,
                    'parent_id': company.id,
                    'type': 'contact',
                    'is_company': False,
                    'zip': postal_code,
                    'street': address_line_1,
                    'street2': address_line_2,
                    'email_formatted': display_name + ' ' + email,
                    'category_id': [(6, 0, category_ids)],
                }
                
                personal_data = {k: v for k, v in personal_vals.items() if v != ''}
                personal = None
                # Create Personal contact
                if record_count == 0:
                    personal = self.env['res.partner'].create(personal_data)
                    _logger.info("Nuevo contacto de persona en tabla res_partner creado: %s", reseller)
                    
                else:
                    if email: 
                        personal = self.env['res.partner'].search([('email', '=', email)], limit=1)
                        
                        if personal and email:
                            personal.write(personal_data)
                            _logger.info("Contacto de persona en tabla res_partner actualizado: %s", personal)
                        else:
                            personal = self.env['res.partner'].create(personal_data)
                            _logger.info("Contacto de persona en tabla res_partner creado: %s", personal)      
                            
                if personal: 
                    # Check if the relationship already exists before adding
                    if personal.id not in reseller.partner_ids.ids:
                        reseller.partner_ids = [(4, personal.id)]
                        _logger.info("Relación de persona creada con ID: %s", personal.id)
                    else:
                        _logger.info("La relación ya existe para la persona con ID: %s", personal.id)

                self.complement_contacts(reseller, company.id, category_ids)

        except ValueError as e:
            _logger.error("Error al procesar la respuesta de la API: %s", e)

        except Exception as e:
            _logger.error("Se produjo un error inesperado: %s", e)
        

        _logger.info("Todos los contactos fueron sincronizados")
    
            
    def create_labels(self):
        # Obtener o crear etiquetas
        etiquetas = ['Contacto Actualizado', 'Partner Sales Console']  
        category_ids = []
        for etiqueta in etiquetas:
            category = self.env['res.partner.category'].search([('name', '=', etiqueta)], limit=1)
            if not category:
                # Si no existe, crea la etiqueta
                category = self.env['res.partner.category'].create({'name': etiqueta, 'color': 4})
            category_ids.append(category.id)
        
        return category_ids

    def complement_contacts(self, reseller, company_id, category_ids):
        try:
            
            """Obtiene la lista de contactos de la API y devuelve los datos"""
            service = self.create_admin_service()
            
            if not service:
                return []
                
            users = []
            try:
                if reseller.cloud_identity_id != False:
                    # Intenta obtener los usuarios
                    results = service.users().list(customer=reseller.cloud_identity_id, query='isAdmin=true', maxResults=15).execute()
                    users = results.get('users', [])
            except HttpError as error:
                if int(error.resp.get('status', 0)) == 403:  # Error de permisos
                    _logger.warning("Error de permisos al obtener usuarios para reseller %s: %s", reseller.cloud_identity_id, error)
                elif int(error.resp.get('status', 0)) == 404:  # Reseller no encontrado
                    _logger.warning("Cliente no encontrado: %s", reseller.cloud_identity_id)
                else:
                    _logger.error("Error inesperado al obtener usuarios para cliente %s: %s", reseller.cloud_identity_id, error)
            except Exception as e:
                _logger.error("Error desconocido al obtener usuarios: %s", e)
            
            # Si no hay usuarios, return
            if not users:
                _logger.info("No se encontraron usuarios para el cliente %s.", reseller.cloud_identity_id)
                return []
        
            record_count = self.env['reseller.partner'].search_count([])
            
            for user in users:
                
                name_data = user.get('name', {})
                full_name = name_data.get('fullName', 'Sin nombre')
                email = user.get('primaryEmail')

                # Personal contact
                contact_vals = {
                    'contact_address': reseller.address,
                    'country_code': reseller.region_code,
                    'date': '',
                    'display_name': full_name,
                    'name': full_name,
                    'email': email,
                    # 'lang': language_code,
                    # 'lang': 'en_US',
                    # 'phone': reseller.phone,
                    'website': reseller.domain,
                    'parent_id': company_id,
                    'type': 'contact',
                    'is_company': False,
                    'zip': reseller.postal_code,
                    'street': reseller.address_line_1,
                    'street2': reseller.address_line_2,
                    'email_formatted': full_name + ' ' + email,
                    'category_id': [(6, 0, category_ids)],
                }
                
                contact_data = {k: v for k, v in contact_vals.items() if v not in [False, '']}                
                
                # Create Personal contact
                if record_count == 0:
                    contact = self.env['res.partner'].create(contact_data)
                    _logger.info("Nuevo contacto complementario en tabla res_partner creado: %s", reseller)
                    
                else:
                    contact = self.env['res.partner'].search([('email', '=', email)], limit=1)
                    
                    if contact:
                        contact.write(contact_data)
                        _logger.info("Contacto complementario en tabla res_partner actualizado: %s", contact)
                    else:
                        contact = self.env['res.partner'].create(contact_data)
                        _logger.info("Contacto complementario en tabla res_partner creado: %s", contact)      

                # Check if the relationship already exists before adding
                if contact.id not in reseller.partner_ids.ids:
                    reseller.partner_ids = [(4, contact.id)]
                    _logger.info("Relación complementaria creada con ID: %s", contact.id)
                else:
                    _logger.info("La relación complementaria ya existe para la compañía con ID: %s", contact.id)
                    
        except Exception as e:
            _logger.error(f"Error al obtener contactos: {e}")
            return []
    

    def sync_subscriptions(self, reseller):
        """Sincroniza contactos con la base de datos de Odoo"""
        try:
            reseller_service = self.create_reseller_service()
            
            # if subscriptions:
            #     for subscription in subscriptions:
            #         print("Suscripción: ", subscription)
            # else:
            #     print(f"No subscriptions found for customer ID: C00qonywf")

            subscriptions = []
            try:
                # response = reseller_service.subscriptions().list(customerId=reseller).execute()
                response = reseller_service.subscriptions().list(customerId=reseller.cloud_identity_id).execute()
        
                # Verifica si el cliente tiene suscripciones
                subscriptions = response.get('subscriptions', [])

            except HttpError as error:
                if int(error.resp.get('status', 0)) == 403:  # Error de permisos
                    _logger.warning("Error de permisos al obtener suscripciones para cliente %s: %s", reseller.cloud_identity_id, error)
                    # _logger.warning("Error de permisos al obtener suscripciones para cliente %s: %s", reseller, error)
                elif int(error.resp.get('status', 0)) == 404:  # Reseller no encontrado
                    _logger.warning("Cliente no encontrado: %s", reseller.cloud_identity_id)
                    # _logger.warning("Cliente no encontrado: %s", reseller)
                else:
                    _logger.error("Error inesperado al obtener suscripciones para cliente %s: %s", reseller.cloud_identity_id, error)
                    # _logger.error("Error inesperado al obtener suscripciones para cliente %s: %s", reseller, error)
            except Exception as e:
                _logger.error("Error desconocido al obtener suscripciones: %s", e)
            
            # Si no hay suscripciones, return
            if not subscriptions:
                _logger.info("No se encontraron suscripciones para el cliente %s.", reseller.cloud_identity_id)
                # _logger.info("No se encontraron suscripciones para el cliente %s.", reseller)
                return []

            for subscription in subscriptions:
                # print(subscription)
                kind = subscription.get('kind', None)            
                customerId = subscription.get('customerId', None)
                subscriptionId = subscription.get('subscriptionId', None)
                skuId = subscription.get('skuId', None)
                billingMethod = subscription.get('billingMethod', None)
                creationTime = subscription.get('creationTime', None)
                purchaseOrderId = subscription.get('purchaseOrderId', None)
                status = subscription.get('status', None)
                resourceUiUrl = subscription.get('resourceUiUrl', None)
                skuName = subscription.get('skuName', None)
                
                plan = subscription.get('plan', {})
                planName = plan.get('planName', None)
                isCommitmentPlan = plan.get('isCommitmentPlan', None)
                
                # Inicializa las variables por defecto
                startTime = None
                endTime = None
                
                commitmentInterval = plan.get('commitmentInterval', {})
                if commitmentInterval:
                    startTime = commitmentInterval.get('startTime', None)
                    endTime = commitmentInterval.get('endTime', None)
                
                trialSettings = subscription.get('trialSettings', {})
                isInTrial = trialSettings.get('isInTrial', None)

                seats = subscription.get('seats', {})
                numberOfSeats = seats.get('numberOfSeats', None)
                licensedNumberOfSeats = seats.get('licensedNumberOfSeats', None)

                renewalSettings = subscription.get('renewalSettings', {})
                renewalType = renewalSettings.get('renewalType', None)
                
                subscription_vals = {
                    'kind': kind,
                    'customerId': customerId,
                    'subscriptionId': subscriptionId,
                    'skuId': skuId,
                    'billingMethod': billingMethod,
                    'creationTime': creationTime,
                    'purchaseOrderId': purchaseOrderId,
                    'status': status,
                    'resourceUiUrl': resourceUiUrl,
                    'skuName': skuName,
                    'planName': planName,
                    'isCommitmentPlan': isCommitmentPlan,
                    'startTime': startTime,
                    'endTime': endTime,
                    'isInTrial': isInTrial,
                    'numberOfSeats': numberOfSeats,
                    'licensedNumberOfSeats': licensedNumberOfSeats,
                    'renewalType': renewalType,
                }
                
                subscription_data = {k: v for k, v in subscription_vals.items() if v != ''}
                # print(subscription_data)
                subscription = self.env['reseller.subscription'].search([('subscriptionId', '=', subscriptionId)], limit=1)
                
                # TODO actualizar subscriptionId al momento de actualizar los datos de una suscripción, i.e. después de actualizar y regresar el objeto, actualizar el valor
                
                if subscription:
                    subscription.write(subscription_data)
                    _logger.info("Contacto en tabla reseller_subscription actualizado: %s", subscription)
                else:
                    subscription = self.env['reseller.subscription'].create(subscription_data)
                    _logger.info("Nuevo contacto en tabla reseller_subscription creado: %s", subscription)
                    
                 # Check if the relationship already exists before adding
                if subscription.id not in reseller.reseller_subscription_ids.ids:
                    reseller.reseller_subscription_ids = [(4, subscription.id)]
                    _logger.info("Relación de persona creada con ID: %s", subscription.id)
                else:
                    _logger.info("La relación ya existe para la persona con ID: %s", subscription.id)
                

        except ValueError as e:
            _logger.error("Error al procesar la respuesta de la API: %s", e)

        except Exception as e:
            _logger.error("Se produjo un error inesperado: %s", e)
        

        _logger.info("Todos los contactos fueron sincronizados")
        

class ResPartner(models.Model):
    _inherit = 'res.partner'

    reseller_id = fields.Many2one(
        comodel_name='reseller.module',
        string='Reseller Module'
    )

    contactos_odoos = fields.Many2many('res.partner', string="Contactos en Odoo", compute="_compute_contactos_odoos")

    def _compute_contactos_odoo(self):
        # Obtener todos los contactos en el sistema
        for partner in self:
            partner.contactos_odoo = self.env['res.partner'].search([])  # Todos los contactos

