# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Isi otomatis field 'Materi' (material_id) pada test lama.

    Field pslearning.test.material_id baru ditambahkan, sehingga test yang
    dibuat sebelumnya masih kosong. Backfill dilakukan dari dua sumber agar
    smart button 'Test Terkait' dan auto-resolve test berjalan konsisten:

    1. Dari link eksplisit di materi (pretest_id / posttest_id).
    2. Dari 'Materi Terkait' pada soal, bila seluruh soal test menunjuk ke
       satu materi yang sama.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1. Dari link eksplisit pada materi.
    materials = env['pslearning.material'].search([])
    for mat in materials:
        for test in (mat.pretest_id, mat.posttest_id):
            if test and not test.material_id:
                test.material_id = mat.id

    # 2. Dari materi soal (hanya bila tunggal & konsisten).
    pending = env['pslearning.test'].search([('material_id', '=', False)])
    for test in pending:
        mats = test.question_ids.mapped('material_id')
        if len(mats) == 1:
            test.material_id = mats.id

    env['pslearning.test'].flush_model(['material_id'])
