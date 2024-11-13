# -*- coding: utf-8 -*-
# from odoo import http


# class ResellerModule(http.Controller):
#     @http.route('/reseller_module/reseller_module', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/reseller_module/reseller_module/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('reseller_module.listing', {
#             'root': '/reseller_module/reseller_module',
#             'objects': http.request.env['reseller_module.reseller_module'].search([]),
#         })

#     @http.route('/reseller_module/reseller_module/objects/<model("reseller_module.reseller_module"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('reseller_module.object', {
#             'object': obj
#         })
