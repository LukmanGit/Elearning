# -*- coding: utf-8 -*-
{
    'name': 'PS Learning',
    'version': '17.0.14.0.0',
    'category': 'Human Resources/Learning',
    'summary': 'Platform E-Learning Internal',
    'description': """
PS Learning
===========
Modul custom untuk mengelola course, materi pembelajaran, pre-test,
post-test, dan pelacakan progress peserta.
    """,
    'author': 'Your Name',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'website',
    ],
    'data': [
        'security/pslearning_security.xml',
        'security/ir.model.access.csv',
        'data/pslearning_data.xml',
        'views/ps_learning_view.xml',
        'views/ps_material_view.xml',
        'views/ps_enrollment_view.xml',
        'views/ps_test_view.xml',
        'views/ps_test_attempt_view.xml',
        'views/pslearning_templates.xml',
        'views/login_templates.xml',
        'views/res_config_settings_views.xml',
        'views/pslearning_menus.xml',
    ],
    'demo': [
        # 'demo/pslearning_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'pslearning/static/src/css/pslearning.css',
            # 'pslearning/static/src/js/pslearning.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}