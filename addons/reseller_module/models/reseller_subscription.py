from odoo import models, fields, api
from datetime import datetime
import io
import base64
import xlsxwriter
import logging

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
                    date_obj = datetime.fromtimestamp(int(record.startTime) / 1000)
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
                    date_obj = datetime.fromtimestamp(int(record.endTime) / 1000)
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
                    date_obj = datetime.fromtimestamp(int(record.creationTime) / 1000)
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
                
    def generate_report(self):
        # Crear un buffer en memoria
        output = io.BytesIO()

        # Crear un archivo Excel
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Reporte')

        # Headers
        headers = [
            'Cliente', # subscription -> reseller_partner
            'Nombre Comercial', # subscription -> reseller_partner
            'Suscripción',
            'School Partne',
            'Contrato',
            'Producto',
            'SKU', # subscription.skuName
            'Fecha de creación (PST)', # 
            'Estado de suscripción', # subscription.status
            'Plan de pago', #subscription.planName
            'Dia', # subscription
            'Mes',
            'Año',
            'Pais',
            'Licencias asignadas', # subscription.licensedNumberOfSeats
            'Licencias a renovar',
            'Precio vta x licencia Cliente',
            'Monto mxn a cobrar Odoo',
            'Descuento Odoo',
            'Importe de descuento',
            'Total pagado sin iva',
            'Cliente paga',
            'Costo unitario licencia Consola',
            'Monto costo Mensual en factura Google',
            'Monto a pagar a Google',
            'Ganancia',
            'Margen',
            'Partner Advantage DR' #28
        ]
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header)

        subscriptions = self.env['reseller.subscription'].sudo().search([])
        
        # Escribir datos
        for row_num, subscription in enumerate(subscriptions, start=1):
            worksheet.write(row_num, 0, subscription.related_partner_names) #Cliente # subscription -> reseller_partner
            worksheet.write(row_num, 1, subscription.related_partner_names) #Nombre Comercial # subscription -> reseller_partner
            worksheet.write(row_num, 2, "") #Suscripción
            worksheet.write(row_num, 3, "") #School Partne
            worksheet.write(row_num, 4, "") #Contrato
            worksheet.write(row_num, 5, "") #Producto
            worksheet.write(row_num, 6, subscription.skuName) #SKU # subscription.skuName
            worksheet.write(row_num, 7, subscription.formattedCreationTime) #Fecha de creación (PST) # 
            worksheet.write(row_num, 8, subscription.status) #Estado de suscripción # subscription.status
            worksheet.write(row_num, 9, subscription.planName) #Plan de pago #subscription.planName
            worksheet.write(row_num, 10, "") #Dia # subscription
            worksheet.write(row_num, 11, "")  #Mes
            worksheet.write(row_num, 12, "") #Año
            worksheet.write(row_num, 13, "") #Pais
            worksheet.write(row_num, 14, subscription.licensedNumberOfSeats) #Licencias asignadas # subscription.licensedNumberOfSeats
            worksheet.write(row_num, 15, "") #Licencias a renovar
            worksheet.write(row_num, 16, "") #Precio vta x licencia Cliente
            worksheet.write(row_num, 17, "") #Monto mxn a cobrar Odoo
            worksheet.write(row_num, 18, "")  #Descuento Odoo
            worksheet.write(row_num, 19, "") #Importe de descuento
            worksheet.write(row_num, 20, "") #Total pagado sin iva
            worksheet.write(row_num, 21, "") #Cliente paga
            worksheet.write(row_num, 22, "") #Costo unitario licencia Consola
            worksheet.write(row_num, 23, "") #Monto costo Mensual en factura Google
            worksheet.write(row_num, 24, "") #Monto a pagar a Google
            worksheet.write(row_num, 25, "")  #Ganancia
            worksheet.write(row_num, 26, "") #Margen
            worksheet.write(row_num, 27, "") #Partner Advantage DR

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