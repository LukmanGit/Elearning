# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Hitung ulang progress & ringkasan enrollment setelah perubahan
    model ke jalur pembelajaran per-materi (Pre-Test -> Belajar -> Post-Test).

    Catatan: Pre/Post-Test kini diatur per-materi (material.pretest_id /
    material.posttest_id). Test course-level lama tidak lagi dipakai oleh
    alur; admin perlu menetapkan test pada masing-masing materi.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    enrollments = env['pslearning.enrollment'].search([])
    if not enrollments:
        return
    enrollments._compute_aggregate()
    enrollments._compute_progress()
    enrollments.flush_recordset()
