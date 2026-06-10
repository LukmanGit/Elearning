# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Isi publish_date untuk course yang sudah dipublikasi sebelum field ini ada.

    Tanpa publish_date, ribbon "New" pada kanban tidak akan pernah muncul untuk
    course lama. Kita gunakan write_date (atau create_date) sebagai perkiraan
    waktu publikasi terakhir.
    """
    cr.execute("""
        UPDATE pslearning_course
           SET publish_date = COALESCE(publish_date, write_date, create_date)
         WHERE state = 'published'
           AND publish_date IS NULL
    """)
