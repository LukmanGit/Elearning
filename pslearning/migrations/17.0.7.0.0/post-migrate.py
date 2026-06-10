# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Hitung ulang ringkasan test enrollment.

    Toggle "Semua Pre-Test/Post-Test Selesai" kini hanya hijau bila memang
    ada test wajib dan semuanya sudah dikerjakan (tidak lagi hijau secara
    otomatis ketika materi belum memiliki test).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    enrollments = env['pslearning.enrollment'].search([])
    if not enrollments:
        return
    enrollments._compute_aggregate()
    enrollments._compute_progress()
    enrollments.flush_recordset()
