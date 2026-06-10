# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Hitung ulang progress & status enrollment dengan logika baru.

    Memperbaiki data lama yang berstatus 'Selesai' padahal progress < 100%
    (mis. karena materi baru dipublikasikan setelah course selesai).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    enrollments = env['pslearning.enrollment'].search([])
    if not enrollments:
        return
    enrollments._compute_aggregate()
    enrollments._compute_progress()
    enrollments.flush_recordset()
