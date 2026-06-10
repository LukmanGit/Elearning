# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pslearning_hide_login_chrome = fields.Boolean(
        string='Sembunyikan Header/Footer Halaman Login',
        default=True,
        config_parameter='pslearning.hide_login_chrome',
        help='Jika aktif, header dan footer website disembunyikan di halaman '
             'login, signup, dan reset password. Berlaku untuk SELURUH sistem '
             '(semua pengguna), bukan hanya peserta e-learning.',
    )
