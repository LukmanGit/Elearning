# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Hitung ulang field tersimpan enrollment yang mungkin basi.

    Menghitung ulang ringkasan test (rata-rata & status) serta progress
    dengan logika terbaru agar status peserta konsisten.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    enrollments = env['pslearning.enrollment'].search([])
    if not enrollments:
        return
    enrollments._compute_aggregate()
    enrollments._compute_progress()
    enrollments.flush_recordset()
