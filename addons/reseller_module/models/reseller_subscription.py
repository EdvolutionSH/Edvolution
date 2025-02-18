import re
import os
from odoo import models, fields, api
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import datetime
import io
import base64
import xlsxwriter
import logging
import json



_logger = logging.getLogger(__name__)

class ResellerSubscription(models.Model):
    _name = 'reseller.subscription'  # Nombre técnico del modelo
    _description = 'Suscripciones de Reseller'  # Descripción del modelo

    kind = fields.Char('Tipo de recurso') # Identifica el recurso como una suscripción. Valor: reseller#subscription
    customerId = fields.Char('Identificador de la organización')
    subscriptionId = fields.Char('Identificador de la suscripción')
    skuId = fields.Char('Identificador del SKU del producto')
    billingMethod = fields.Char('Método de facturación')
    creationTime = fields.Char('Fecha de creación de la suscripción')
    planName = fields.Char('Nombre del plan')
    isCommitmentPlan = fields.Boolean('Plan de compromiso anual') #true: El plan de la suscripción es un plan de compromiso anual. false: El plan no es un plan de compromiso anual.
    startTime = fields.Char('Inicio del intervalo de un plan de compromiso anual')
    endTime = fields.Char('Fin del intervalo de un plan de compromiso anual')
    """" Esta es una propiedad obligatoria y exclusiva para las suscripciones con los planes ANNUAL_MONTHLY_PAY y ANNUAL_YEARLY_PAY. 
        Esta propiedad establece la cantidad máxima de licencias que se pueden asignar a los usuarios en una suscripción"""
    numberOfSeats = fields.Integer('Número máximo de licencias')
    licensedNumberOfSeats = fields.Integer('Usuarios a los que se les asignó licencia')
    """" Determina si el plan de la suscripción está en una prueba gratuita de 30 días """
    isInTrial = fields.Boolean('Es prueba gratuita')
    """ Configuración de renovación del plan de compromiso anual """
    renewalType = fields.Char('Configuración de la renovación')
    """" Esta propiedad es opcional. La información de esta orden de compra (PO) es para que los revendedores la utilicen para hacer un seguimiento del uso que hacen la empresa """
    purchaseOrderId = fields.Char('Orden de compra')
    status = fields.Char('Estatus')
    """ URL de la página Suscripciones del cliente en la Consola del administrador """
    resourceUiUrl = fields.Char('URL consola suscripciones')
    """" Es el nombre visible externo de solo lectura para el SKU de un producto asignado a un cliente en la suscripción """
    skuName = fields.Char('Nombre del SKU del producto')
    reseller_ids = fields.Many2many(
        'reseller.partner',  # Nombre del modelo relacionado
        'reseller_subscription_reseller_partner_rel',  # Nombre de la tabla intermedia
        'reseller_subscription_id',  # Nombre del campo en la tabla intermedia que apunta a 'reseller.subscription'
        'reseller_id',           # Nombre del campo en la tabla intermedia que apunta a 'reseller.partner'
        string='Related Partners'
    )
    formattedStartTime = fields.Char(string="Fecha Inicial", compute="_compute_formatted_date")
    formattedEndTime = fields.Char(string="Fecha Final", compute="_compute_formatted_end_date")
    formattedCreationTime = fields.Char(string="Fecha creación", compute="_compute_formatted_creation_date")
    unit = fields.Char('Unidad', default='USD')

    @api.depends('startTime')
    def _compute_formatted_date(self):
        for record in self:
            if record.startTime:
                try:
                    # Convertir milisegundos a fecha
                    date_obj = datetime.datetime.fromtimestamp(int(record.startTime) / 1000)
                    record.formattedStartTime = date_obj.strftime('%d/%m/%Y')
                except (ValueError, TypeError):
                    record.formattedStartTime = 'Fecha no válida'
            else:
                # Manejar casos donde el campo es None o vacío
                record.formattedStartTime = 'Fecha no disponible'
                
    @api.depends('endTime')
    def _compute_formatted_end_date(self):
        for record in self:
            if record.endTime:
                try:
                    # Convertir milisegundos a fecha
                    date_obj = datetime.datetime.fromtimestamp(int(record.endTime) / 1000)
                    record.formattedEndTime = date_obj.strftime('%d/%m/%Y')
                except (ValueError, TypeError):
                    record.formattedEndTime = 'Fecha no válida'
            else:
                # Manejar casos donde el campo es None o vacío
                record.formattedEndTime = 'Fecha no disponible'
                
    @api.depends('creationTime')
    def _compute_formatted_creation_date(self):
        for record in self:
            if record.creationTime:
                try:
                    # Convertir milisegundos a fecha
                    date_obj = datetime.datetime.fromtimestamp(int(record.creationTime) / 1000)
                    record.formattedCreationTime = date_obj.strftime('%d/%m/%Y')
                except (ValueError, TypeError):
                    record.formattedCreationTime = 'Fecha no válida'
            else:
                # Manejar casos donde el campo es None o vacío
                record.formattedCreationTime = 'Fecha no disponible'

    related_partner_names = fields.Char(
        string="Nombres de Partners Relacionados",
        compute="_compute_related_partner_names",
        store=True)

    @api.depends('reseller_ids')
    def _compute_related_partner_names(self):
        for record in self:
            if record.reseller_ids:
                record.related_partner_names = ", ".join(record.reseller_ids.mapped('org_display_name'))
            else:
                record.related_partner_names = "Sin socios relacionados"

    def name_get(self):
        result = []
        for record in self:
            # Name and sku
            display_name = f"{record.related_partner_names} - {record.skuName}"
            result.append((record.id, display_name))
        return result

    def subscription_details(self, subscription_id=None):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        SERVICE_ACCOUNT_FILE = os.path.join(current_dir, '..', 'service', 'sa-reseller.json')
        PARTNER_ID = 'C01bjv6i2'

        # Crear credenciales desde el archivo del servicio
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/paymentsresellersubscription']  # Scope correcto
        )

        # Refrescar el token
        credentials.refresh(Request())
        # print(dir(credentials))
        # print("Token:", credentials.project_id)
        # print("¿Credenciales válidas?:", credentials.valid)
        # print("¿Credenciales expiradas?:", credentials.expired)

        # credentials = service_account.Credentials.from_service_account_file(
        #     SERVICE_ACCOUNT_FILE,
        #     scopes=['https://www.googleapis.com/auth/cloud-platform',]
        # )

        # Refrescar las credenciales (opcional)
        # credentials.refresh(Request())

        # Imprimir información clave
        print("Token:", credentials.token)
        print("Expira el:", credentials.expiry)
        print("¿Credenciales válidas?:", credentials.valid)
        print("¿Credenciales expiradas?:", credentials.expired)
        print("Cuenta de servicio:", credentials.service_account_email)
        print("ID del proyecto:", credentials.project_id)
        print("Scopes:", credentials.scopes)


        # Verificación y actualización del token de acceso si ha expirado
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        # Asegúrate de que las credenciales tienen un token de acceso válido
        if not credentials.valid:
            print("Error: Las credenciales no son válidas. Intenta refrescarlas.")
            return

        # Mostrar el token de acceso (para ver si está siendo obtenido correctamente)
        print(f"Token de acceso: {credentials.token}")

        # Construcción del cliente de la API
        service = build('paymentsresellersubscription', 'v1', credentials=credentials)
        subscription_name = f"partners/{PARTNER_ID}/subscriptions/{subscription_id}"

        try:
            # Llamada a la API para obtener detalles de la suscripción
            response = service.partners().subscriptions().get(name=subscription_name).execute()

            # Imprime los detalles del plan y facturación
            print("Detalles de la suscripción:")
            print(f"ID: {response['name']}")
            print(f"Estado: {response['state']}")
            print("Productos asociados:")
            for product in response.get('products', []):
                print(f"- Producto ID: {product['productId']}")
                print(f"  Nombre del plan: {product['plan']['planName']}")
                print(f"  Ciclo de facturación: {product['plan']['billingCycleDuration']['count']} "
                    f"{product['plan']['billingCycleDuration']['unit']}")
                print(f"  Precio: {int(product['price']['amountMicros']) / 1_000_000} "
                    f"{product['price']['currencyCode']}")
            return response
        except Exception as e:
            print(f"Error al obtener los detalles de la suscripción: {e}")
        

    def generate_report(self):
        # Crear un buffer en memoria
        output = io.BytesIO()

        # Crear un archivo Excel
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Reporte')

        # Headers
        headers = [
            'País',
            'Unidad',
            'Cliente', # subscription -> reseller_partner
            'Nombre Comercial', # subscription -> reseller_partner
            'Suscripción',
            'Envió de correo',
            'Fecha SKU anterior',
            'SKU anterior',
            'School Partner',
            'SKU actual',
            'Plan de pagos',
            'Estado de la suscripción',
            'Día',
            'Mes',
            'Año',
            'Licencias asignadas',
            'Licencias a renovar',
            'Precio unitario oficial google para el cliente',
            'Descuento google para el cliente',
            'Precio unitario al publico con descuento',
            'Monto mxn a cobrar Odoo sin iva',
            'Cliente paga',
            'Costo unitario licencia consola anual',
            'Costo unitario licencia consola mensual',
            'Monto a pagar a google',
            'Ganancia',
            'Margen',
            'Factura',
            'Pago de la factura',
            'Comentarios (Upsell, cambio de SKU)',
            'Partner Advantage DR',
            'Como se paga a google',
            'Suscripción consola',
            'Data'
        ]
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header)

        visible_subscriptions = self.env['reseller.subscription'].search([
            ('status', '=', 'ACTIVE'),           # Estado igual a 'ACTIVE'
            ('planName', '!=', 'FREE'),         # Plan distinto de 'FREE'
            ('skuName', 'not ilike', '%Staff%')  # skuName no contiene 'Staff' en ninguna parte
        ])
        # Escribir datos
        for row_num, subscription in enumerate(visible_subscriptions, start=1):
            related_partner_name = subscription.related_partner_names #Nombre del cliente de la suscripción
            reseller_partner = self.env['reseller.partner'].search([
                ('org_display_name', '=', related_partner_name)
            ], limit=1)  #consulta el reseller_partner q coincide con el nombre
            partner_domain = reseller_partner.domain
            # print(partner_domain)
            result={}
            result['unit'] = subscription.unit
            if partner_domain:
                # Limpiar "http://" o "https://" del dominio
                cleaned_domain = re.sub(r'^(https?://)?(www\.)?', '', partner_domain)
                cleaned_domain = cleaned_domain.rstrip('/')

                # Buscar las órdenes de venta de contactos con el dominio especificado
                sale_orders = self.env['sale.order'].search([
                    ('partner_id.website', 'ilike', f"%{cleaned_domain}"),  # Filtro por dominio del cliente
                    ('state', "=", "sale")
                ])
                partner_names = sale_orders.mapped('partner_id.name')
                result['partner_names'] = partner_names
                # result['partner_name'] = sale_orders.partner_id.name
                
                latest_sale_order = None
                # Si no se encuentran órdenes de venta, terminar
                if sale_orders:
                    matching_sale_orders = sale_orders.filtered(
                        lambda order: any(
                            line.product_id.product_tmpl_id.x_studio_sku == subscription.skuName
                            for line in order.order_line
                        )
                    )
                    
                    SOproduct = None
                    if matching_sale_orders:
                        # Si se encuentran órdenes de venta, buscar la primera que coincida con sku
                        latest_sale_order = matching_sale_orders.sorted(key=lambda inv: inv.write_date or inv.create_date, reverse=True)[0]
                        result['partner_name'] = latest_sale_order.partner_id.name
                        SOproduct = self.env['sale.order.line'].search([
                            ('order_id', '=', latest_sale_order.id),  # Relacionar facturas con las órdenes de venta
                            ('product_id.product_tmpl_id.x_studio_sku', '=', subscription.skuName)
                        ],limit=1)
                        result['invoice_subscription'] = SOproduct.name
                        result['school_partner'] = latest_sale_order.user_id.partner_id.name
                        result['cost']=SOproduct.x_studio_costo_1
                        result['price'] = SOproduct.price_unit
                        result['discount'] = SOproduct.discount
                        result['unit_price'] = (SOproduct.price_unit * (1 - (SOproduct.discount / 100)))
                        
                        if latest_sale_order:
                            result['recurrence'] = latest_sale_order.recurrence_id.name
                            result['invoice_name'] = latest_sale_order.name
                        else:
                            result['recurrence'] = ""
                            result['invoice_name'] = ""
                        
                        latest_sale_orders = matching_sale_orders.sorted(key=lambda inv: inv.write_date or inv.create_date, reverse=True)
                        if len(latest_sale_orders) > 1:  # Verificar que haya al menos dos elementos
                            
                            penultimate_sale_order = latest_sale_orders[-2]
                            last_order_product = self.env['sale.order.line'].search([
                                ('order_id', '=', penultimate_sale_order.id),  # Relacionar facturas con las órdenes de venta
                                ('product_id.product_tmpl_id.x_studio_sku', '=', subscription.skuName)
                            ],limit=1)
                            
                            result['last_sku'] = last_order_product.name
                            date_obj = last_order_product.write_date
                            result['last_sku_date'] = date_obj.strftime('%d/%m/%Y')
                            
                        else:
                            result['last_sku'] = ""
                            result['last_sku_date'] = ""
                    # Buscar las facturas relacionadas con las órdenes de venta
                    invoices = self.env['account.move'].search([
                        ('invoice_origin', 'in', sale_orders.mapped('name')),  # Relacionar facturas con las órdenes de venta
                        ('state', '=', 'posted')
                    ])

                    # Si no se encuentran facturas, terminar
                    if invoices:

                        # Filtrar las facturas que contengan el producto con el SKU especificado
                        matching_invoices = invoices.filtered(
                            lambda inv: any(
                                line.product_id.product_tmpl_id.x_studio_sku == subscription.skuName
                                for line in inv.invoice_line_ids
                            )
                        )
                        # Si no se encuentran facturas que coincidan con el SKU, terminar
                        if  matching_invoices:
                            # Obtener la factura más reciente
                            latest_invoice = matching_invoices.sorted(key=lambda inv: inv.invoice_date or inv.create_date, reverse=True)[0]
                            
                            invoice_state_mapping = {
                                "posted" : "En proceso de pago",
                                "draft"  : "Borrador",
                                "cancel" : "Cancelada"
                            }
                            product = self.env['account.move.line'].search([
                                ('move_id', '=', latest_invoice.id),  # Relacionar facturas con las órdenes de venta
                                ('product_id.product_tmpl_id.x_studio_sku', '=', subscription.skuName),  # Filtrar facturas publicadas
                            ],limit=1)

                            so=self.env['sale.order'].search([
                                ('name', '=', latest_invoice.invoice_origin),  # Relacionar facturas con las órdenes de venta
                            ],limit=1)
                            # Obtener los datos necesarios
                            result['price'] = product.price_unit
                            result['discount'] = product.discount
                            result['unit_price'] = (product.price_unit * (1 - (product.discount / 100)))
                            result['total'] = product.price_total
                            result['recurrence'] = so.recurrence_id.name
                            result['invoice_name'] = latest_invoice.name
                            result['invoice_state'] = invoice_state_mapping.get(latest_invoice.state, "")
                            
                    else:
                        if SOproduct:
                            result['price'] = SOproduct.price_unit
                            result['discount'] = SOproduct.discount
                            result['unit_price'] = SOproduct.price_unit
                            result['total'] = SOproduct.price_total
                        else:
                            result['price'] = 0
                            result['discount'] = 0
                            result['unit_price'] = 0
                            result['total'] = 0

                        # result['recurrence'] = latest_sale_order.recurrence_id.name
                        # result['invoice_name'] = latest_sale_order.name
                        result['invoice_state'] = ""

            recurrence_mapping = {
                "Yearly" : "Anual",
                "Monthly"  : "Mensual",
                "Daily" : "Diario",
                "Weekly"  : "Semanal",
                "3 years"  : "3 Años",
                "5 Years"  : "5 Años",
                "Quarterly"  : "Trimestral",
                "6 month"  : "Semestral",
                "12 month"  : "Anual",
                "12month"  : "Anual",
            }
            # print(cleaned_domain)
            # print(recurrence_mapping.get(result.get('recurrence', '') or ""))
            #data calculada o procesada
            if subscription.endTime:
                endTime = int(subscription.endTime) / 1000
                date = datetime.datetime.fromtimestamp(endTime)
                day_of_ending = date.day
                month_of_ending = date.month
                year_of_ending = date.year
            else:
                day_of_ending = ""
                month_of_ending = ""
                year_of_ending = ""
            plan_name_mapping = {
                "FREE": "Gratis",
                "ANNUAL": "Anual",
                "ANNUAL_YEARLY_PAY": "Pago anual",
                "FLEXIBLE": "Flexible",
                "TRIAL" : "Prueba"
            }
            status_name_mapping = {
                "ACTIVE": "Activo",
                "SUSPENDED": "Suspendido",
            }

            partner = self.env['reseller.partner'].search(
                [('cloud_identity_id', 'like', subscription.customerId)],
                limit=1
            )
            cost_value = result.get('cost', 0)  # Si no existe, usa 0
            worksheet.write(row_num, 0, partner.region_code) #País #ToDo obtener de consola o de odoo?
            worksheet.write(row_num, 1, result.get('unit', '') if result else "") #Unidad moneda #ToDo
            worksheet.write(row_num, 2, cleaned_domain) #Cliente dominio
            worksheet.write(row_num, 3, result.get('partner_name', '') or "")  # Nombre Comercial
            worksheet.write(row_num, 4, result.get('invoice_subscription', '') if result else "")  # Suscripción en odoo
            worksheet.write(row_num, 5, "") #Envio de correo electronico #ToDo
            worksheet.write(row_num, 6, result.get('last_sku_date', '') if result else "") #Fecha sku anterior 
            worksheet.write(row_num, 7, result.get('last_sku', '') if result else "") #sku anterior
            worksheet.write(row_num, 8, result.get('school_partner', '') if result else "")  # school partner
            worksheet.write(row_num, 9, subscription.skuName) #sku actual
            worksheet.write(row_num, 10, plan_name_mapping.get(subscription.planName, "Desconocido")) #plan de pagos
            worksheet.write(row_num, 11, status_name_mapping.get(subscription.status, "Desconocido"))  #estado de la suscripcion
            worksheet.write(row_num, 12, day_of_ending) #dia
            worksheet.write(row_num, 13, month_of_ending) #mes
            worksheet.write(row_num, 14, year_of_ending) #año
            worksheet.write(row_num, 15, subscription.licensedNumberOfSeats) #licencias asignadas
            worksheet.write(row_num, 16, subscription.numberOfSeats) #licencias a renovar
            worksheet.write(row_num, 17, result.get('price', '') if result else "") # precio unitario oficial google para el cliente
            worksheet.write(row_num, 18, result.get('discount', '') if result else "") # descuento google para el cliente
            worksheet.write(row_num, 19, result.get('unit_price', '') if result else "") # precio unitario al publico con descuento
            if recurrence_mapping.get(result.get('recurrence', '')) == "Anual":               
                worksheet.write(row_num, 20, f"=T{row_num+1} * Q{row_num+1}") # monto mxn a cobrar odoo sin iva
            if recurrence_mapping.get(result.get('recurrence', '')) == "Mensual":
                worksheet.write(row_num, 20, f"=(T{row_num+1} * Q{row_num+1})*12") # monto mxn a cobrar odoo sin iva
            worksheet.write(row_num, 21, recurrence_mapping.get(result.get('recurrence', '') or ""), "") # Cliente paga
            worksheet.write(row_num, 22, float(cost_value)) #costo unitario licencia consola anual
            if recurrence_mapping.get(result.get('recurrence', '')) == "Anual":
                worksheet.write(row_num, 23, f"=(Q{row_num+1} * W{row_num+1})/12") #costo unitario licencia consola mensual
            if recurrence_mapping.get(result.get('recurrence', '')) == "Mensual":
                worksheet.write(row_num, 23, f"=(Q{row_num+1} * W{row_num+1})") #costo unitario licencia consola mensual
            if recurrence_mapping.get(result.get('recurrence', '')) == "Anual":
                worksheet.write(row_num, 24, f"=Q{row_num+1} * W{row_num+1}") #Monto a pagar a Google
            if recurrence_mapping.get(result.get('recurrence', '')) == "Mensual":
                worksheet.write(row_num, 24, f"=(X{row_num+1} * 12)") #Monto a pagar a Google
            worksheet.write(row_num, 25, f"=U{row_num+1} - Y{row_num+1}") #Ganancia
            worksheet.write(row_num, 26, f"=Z{row_num+1} / U{row_num+1}") #Margen
            worksheet.write(row_num, 27, result.get('invoice_name', '') if result else "")  # factura
            worksheet.write(row_num, 28, result.get('invoice_state', '') if result else "")  # pago de la factura
            worksheet.write(row_num, 29, "") #Comentario upsell
            worksheet.write(row_num, 30, "") #Partner Advantage DR
            worksheet.write(row_num, 31, "") #como se paga a google
            worksheet.write(row_num, 32, subscription.resourceUiUrl)
            worksheet.write(row_num, 33, json.dumps(result, ensure_ascii=False, indent=2))

        # Cerrar el archivo Excel
        workbook.close()
        output.seek(0)

        # Codificar el archivo en base64
        file_data = base64.b64encode(output.read())
        output.close()

        # Crear un registro adjunto para el archivo
        attachment = self.env['ir.attachment'].create({
            'name': 'Reporte_Márgenes.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'res.partner',
            'res_id': self.id,
        })

        # Retornar una acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }