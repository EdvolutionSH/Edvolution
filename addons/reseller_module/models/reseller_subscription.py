import re
from odoo import models, fields, api
import datetime
import io
import base64
import xlsxwriter
import logging
import datetime


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
            'Como se paga a google'
        ]
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header)

        visible_subscriptions = self.env['reseller.subscription'].search([('status','=', 'ACTIVE')])

        # Escribir datos
        for row_num, subscription in enumerate(visible_subscriptions, start=1):

            odooData={
                'name': [],
                'plan': [],
                'partner': [],
                'googleDiscount': [],
                'price' : [],
                'payment': [],
                'invoice' : [],
                'invoicePay' : []
            }

            related_partner_name = subscription.related_partner_names #Nombre del cliente de la suscripción
            reseller_partner = self.env['reseller.partner'].search([
                ('org_display_name', '=', related_partner_name)
            ], limit=1)  #consulta el reseller_partner q coincide con el nombre
            partner_domain = reseller_partner.domain
            if partner_domain:
                # Limpiar "http://" o "https://" del dominio
                cleaned_domain = re.sub(r'^(https?://)?(www\.)?', '', partner_domain)
                cleaned_domain = cleaned_domain.rstrip('/')
                
                # Buscar el registro en sale.order donde el campo website coincida                
                sale_orders = self.env['sale.order'].search([
                    ('partner_id.website', 'ilike', cleaned_domain),  # 'ilike' para coincidencia sin distinción de mayúsculas
                    ('is_subscription', '=', True),  # Filtro adicional para is_subscription
                    ('recurring_live', '=', True),  # Filtro adicional para estado en progreso
                    ('order_line.product_id.product_tmpl_id.x_studio_sku', '=', subscription.skuName),  # Filtro adicional para SKU
                    ('order_line.product_uom_qty', '=', subscription.numberOfSeats)  # Filtro adicional para SKU
                ], limit=1)
 
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
            translated_plan_name = plan_name_mapping.get(subscription.planName, "Desconocido")  # Usa "Desconocido" si el valor no está en el diccionario
            translated_status_name = status_name_mapping.get(subscription.status, "Desconocido")  # Usa "Desconocido" si el valor no está en el diccionario
            
            invoice = None
            if sale_orders.name:
                invoice = self.env['account.move'].search([
                    ('invoice_origin', 'like',sale_orders.name)],
                    limit=1
                )

            partner = self.env['reseller.partner'].search(
                [('cloud_identity_id', 'like', subscription.customerId)],
                limit=1
            )

            # Inicializamos el valor que vamos a buscar
            matching_order_line = None

            # Iteramos sobre las líneas de pedido
            for order_line in sale_orders.order_line:
                # Obtenemos el producto relacionado a esta línea de pedido
                product_template = order_line.product_id.product_tmpl_id

                # Comprobamos si el SKU coincide con el de la suscripción
                if product_template.x_studio_sku == subscription.skuName:
                    matching_order_line = order_line
                    break  # Salimos del bucle al encontrar el primer match

            worksheet.write(row_num, 0, partner.region_code) #País #ToDo obtener de consola o de odoo?
            worksheet.write(row_num, 1, "") #Unidad moneda #ToDo
            worksheet.write(row_num, 2, cleaned_domain) #Cliente dominio
            worksheet.write(row_num, 3, sale_orders.partner_id.name or "") #Nombre Comercial 
            worksheet.write(row_num, 4, matching_order_line.name if matching_order_line else "") #Suscripción en odoo
            worksheet.write(row_num, 5, "") #Envio de correo electronico #ToDo
            worksheet.write(row_num, 6, "") #Fecha sku anterior #ToDo
            worksheet.write(row_num, 7, "") #sku anterior
            worksheet.write(row_num, 8, sale_orders.user_id.partner_id.name or "") #school partner
            worksheet.write(row_num, 9, subscription.skuName) #sku actual
            worksheet.write(row_num, 10, translated_plan_name) #plan de pagos
            worksheet.write(row_num, 11, translated_status_name)  #estado de la suscripcion
            worksheet.write(row_num, 12, day_of_ending) #dia
            worksheet.write(row_num, 13, month_of_ending) #mes
            worksheet.write(row_num, 14, year_of_ending) #año
            worksheet.write(row_num, 15, subscription.licensedNumberOfSeats) #licencias asignadas
            worksheet.write(row_num, 16, subscription.numberOfSeats) #licencias a renovar
            worksheet.write(row_num, 17, matching_order_line.price_unit if matching_order_line else "") #precio unitario oficial google para el cliente 
            worksheet.write(row_num, 18, matching_order_line.discount if matching_order_line else "")  #descuento google para el cliente
            worksheet.write(row_num, 19, matching_order_line.price_reduce if matching_order_line else "") #precio unitario al publico con descuento
            worksheet.write(row_num, 20, matching_order_line.price_subtotal if matching_order_line else "") #monto mxn a cobrar odoo sin iva
            worksheet.write(row_num, 21, sale_orders.recurrence_id.name or "") #Cliente paga
            worksheet.write(row_num, 22, "") #costo unitario licencia consola anual
            worksheet.write(row_num, 23, "") #costo unitario licencia consola mensual
            worksheet.write(row_num, 24, "") #Monto a pagar a Google
            worksheet.write(row_num, 25, "") #Ganancia
            worksheet.write(row_num, 26, "") #Margen
            worksheet.write(row_num, 27, invoice.name if invoice else "") #factura
            worksheet.write(row_num, 28, "") #pago de la factura
            worksheet.write(row_num, 29, "") #Comentario upsell
            worksheet.write(row_num, 30, "") #Partner Advantage DR
            worksheet.write(row_num, 31, "") #como se paga a google
            
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