# -*- coding: utf-8 -*-
{
    'name': "reseller_module",

    'summary': """
        Modulo diseñado para la administración visual de las suscripciones y datos provenientes de la consola de revendedor""",

    'description': """
        Modulo diseñado para la administración visual de las suscripciones y datos provenientes de la consola de revendedor
    """,

    'author': "Edvolution by Alinka and Fer",
    'website': "https://www.edvolution.io",

    # Categories  can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        
        'security/ir.model.access.csv',
        'views/reseller_module_view.xml',
        'views/reseller_subscription_view.xml',
        'views/reseller_subscription_view.xml',
        'views/reseller_subscription_details_view.xml'
    ],
    'installable': True,
    'application': True,
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
}
