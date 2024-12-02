from odoo import models, fields
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from odoo import api, fields, models
import logging
from google.cloud import channel_v1
from google.cloud import channel
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

SERVICE_ACCOUNT_FILE = 'sa-reseller.json'
GOOGLE_RESELLER_ACCOUNT_ID = 'C01bjv6i2'
GOOGLE_RESELLER_ADMIN_USER = 'bernardo@edvolution.io'

class ResellerModule(models.Model):
    _name = 'reseller.module'    
    _description = 'Reseller Contact Sync'
    
    def authenticate_service_account(self):
        """Autentica la service account para acceder a la API"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, 
                scopes=["https://www.googleapis.com/auth/apps.order"])
            
            # Set up credentials with user impersonation
            reseller_admin_user = GOOGLE_RESELLER_ADMIN_USER

            credentials_delegated = credentials.with_subject(reseller_admin_user)
            
             # Create the API client
            client = channel.CloudChannelServiceClient(credentials=credentials_delegated)
            return client
        except Exception as e:
            _logger.error(f"Error al autenticar: {e}")
            return None

    def fetch_contacts(self):
        """Obtiene la lista de contactos de la API y devuelve los datos"""
        client = self.authenticate_service_account()
        

        if not client:
            return []
        try:
            # Initialize request arguments
            request = channel_v1.ListCustomersRequest(
                parent=f"accounts/{GOOGLE_RESELLER_ACCOUNT_ID}",
            )

            # Make the request
            page_result = client.list_customers(request=request)

            return page_result
        
        except Exception as e:
            _logger.error(f"Error al obtener contactos: {e}")
            return []

        
    def sync_contacts(self):
        """Sincroniza contactos con la base de datos de Odoo"""
        try:
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
                    _logger.info("Nuevo contacto de Reseller Partner creado: %s", reseller)
                    
                else:
                    reseller = self.env['resellser.partner'].search([('cloud_identity_id', '=', cloud_identity_id)], limit=1)
                    
                    if reseller:
                        reseller.write(reseller_data)
                        _logger.info("Nuevo contacto creado: %s", reseller)
                    else:
                        reseller = self.env['reseller.partner'].create(reseller_data)
                        _logger.info("Contacto actualizado: %s", reseller)
                        
                
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
                    _logger.info("Nuevo contacto de Reseller Partner creado: %s", reseller)
                    
                else:
                    company = self.env['res.partner'].search([('name', '=', org_display_name)], limit=1)
                    
                    if company:
                        company.write(company_data)
                        _logger.info("Nuevo contacto creado: %s", company)
                    else:
                        company = self.env['res.partner'].create(company_data)
                        _logger.info("Contacto actualizado: %s", company)
                
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
                
                # Create Personal contact
                if record_count == 0:
                    personal = self.env['res.partner'].create(personal_data)
                    _logger.info("Nuevo contacto de Reseller Partner creado: %s", reseller)
                    
                else:
                    personal = self.env['res.partner'].search([('name', '=', display_name)], limit=1)
                    
                    if personal:
                        personal.write(personal_data)
                        _logger.info("Nuevo contacto creado: %s", personal)
                    else:
                        personal = self.env['res.partner'].create(personal_data)
                        _logger.info("Contacto actualizado: %s", personal)      
                            
                # Check if the relationship already exists before adding
                if personal.id not in reseller.partner_ids.ids:
                    reseller.partner_ids = [(4, personal.id)]
                    _logger.info("Relación de compañia creada con ID: %s", personal.id)
                else:
                    _logger.info("La relación ya existe para la compañía con ID: %s", personal.id)

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