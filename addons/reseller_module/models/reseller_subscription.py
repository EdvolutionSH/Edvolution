from odoo import models, fields, api
from datetime import datetime

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
    formattedStartTime = fields.Char(string="Fecha Inicial Formateada", compute="_compute_formatted_date")
    formattedEndTime = fields.Char(string="Fecha Final Formateada", compute="_compute_formatted_end_date")

    @api.depends('startTime')
    def _compute_formatted_date(self):
        for record in self:
            print("Record: %s", record)
            print(record.startTime)
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