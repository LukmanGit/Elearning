# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PasiMaterial(models.Model):
    _name = 'pslearning.material'
    _description = 'PASI E-Learning Material'
    _inherit = ['mail.thread']
    _order = 'course_id, sequence, id'

    name = fields.Char(string='Judul Materi', required=True, tracking=True)
    sequence = fields.Integer(string='Urutan', default=10)
    course_id = fields.Many2one('pslearning.course', string='Course',
                                 required=True, ondelete='cascade', tracking=True)

    # Rangkaian test per materi: Pre-Test -> Belajar -> Post-Test
    pretest_id = fields.Many2one(
        'pslearning.test', string='Pre-Test Materi',
        domain="[('course_id', '=', course_id), ('test_type', '=', 'pretest')]")
    posttest_id = fields.Many2one(
        'pslearning.test', string='Post-Test Materi',
        domain="[('course_id', '=', course_id), ('test_type', '=', 'posttest')]")

    material_type = fields.Selection([
        ('text', 'Teks/Artikel'),
        ('document', 'Dokumen (PDF/Word)'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('presentation', 'Presentasi'),
        ('mixed', 'Campuran'),
    ], string='Tipe Materi', default='text', required=True)

    content = fields.Html(string='Konten Materi')
    description = fields.Text(string='Deskripsi Singkat')

    # Attachments
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'pslearning_material_attachment_rel',
        'material_id', 'attachment_id',
        string='Lampiran (File/Audio/Video)'
    )

    # Direct file fields untuk video/audio/dokumen utama
    video_file = fields.Binary(string='File Video', attachment=True)
    video_filename = fields.Char(string='Nama File Video')
    video_url = fields.Char(string='URL Video (YouTube/Vimeo)',
                            help='URL embed video eksternal')

    audio_file = fields.Binary(string='File Audio', attachment=True)
    audio_filename = fields.Char(string='Nama File Audio')

    document_file = fields.Binary(string='File Dokumen', attachment=True)
    document_filename = fields.Char(string='Nama File Dokumen')

    duration_minutes = fields.Integer(string='Durasi (Menit)',
                                    help='Estimasi waktu untuk mempelajari materi ini')

    is_required = fields.Boolean(string='Wajib Dipelajari', default=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Dipublikasi'),
    ], string='Status', default='draft', tracking=True)

    attachment_count = fields.Integer(string='Jumlah Lampiran',
                                    compute='_compute_attachment_count')

    # Test yang dibuat dari materi ini (soal-soalnya terkait materi ini)
    test_count = fields.Integer(string='Jumlah Test', compute='_compute_test_count')

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)

    @api.depends('course_id', 'pretest_id', 'posttest_id')
    def _compute_test_count(self):
        Test = self.env['pslearning.test']
        for record in self:
            if record.id and record.course_id:
                record.test_count = Test.search_count(
                    record._related_tests_domain())
            else:
                record.test_count = 0

    def _related_tests_domain(self):
        """Domain semua test yang terkait materi ini, lewat salah satu dari:
        (1) field eksplisit pretest_id / posttest_id,
        (2) field Materi pada test (test.material_id),
        (3) soal yang 'Materi Terkait'-nya menunjuk materi ini.
        """
        self.ensure_one()
        explicit_ids = [t.id for t in (self.pretest_id, self.posttest_id) if t]
        return [
            '&', ('course_id', '=', self.course_id.id),
            '|', '|',
            ('id', 'in', explicit_ids),
            ('material_id', '=', self.id),
            ('question_ids.material_id', '=', self.id),
        ]

    def _resolve_test(self, test_type):
        """Kembalikan test (pre/post) untuk materi ini.

        Prioritas:
        1. Field eksplisit (pretest_id / posttest_id) bila diisi admin.
        2. Fallback otomatis: test PUBLISHED bertipe sama yang soal-soalnya
           terkait materi ini. Ini membuat test yang sudah dibuat lewat
           tombol 'Buat Test' langsung muncul tanpa perlu menautkan manual.
        """
        self.ensure_one()
        explicit = self.pretest_id if test_type == 'pretest' else self.posttest_id
        if explicit:
            return explicit
        if not self.course_id or not self.id:
            return self.env['pslearning.test']
        return self.env['pslearning.test'].search([
            ('course_id', '=', self.course_id.id),
            ('test_type', '=', test_type),
            ('state', '=', 'published'),
            ('question_ids.material_id', '=', self.id),
        ], order='id', limit=1)

    def action_publish(self):
        for rec in self:
            if not rec.duration_minutes or rec.duration_minutes <= 0:
                raise UserError(_(
                    'Durasi (menit) materi "%s" tidak boleh 0. '
                    'Isi estimasi durasi sebelum mempublikasikan materi.'
                ) % rec.name)
        self.write({'state': 'published'})

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_create_test(self):
        """Buat Test dari materi ini: nama & course terisi otomatis,
        admin tinggal mengisi tipe, nilai kelulusan, batas waktu, dan soal."""
        self.ensure_one()
        return {
            'name': _('Buat Test untuk: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'pslearning.test',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_name': self.name,
                'default_course_id': self.course_id.id,
                'default_material_id': self.id,
                'default_question_ids': [(0, 0, {
                    'material_id': self.id,
                    'question_type': 'multiple_choice',
                })],
            },
        }

    def action_view_tests(self):
        self.ensure_one()
        return {
            'name': _('Test terkait: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'pslearning.test',
            'view_mode': 'tree,form',
            'domain': self._related_tests_domain(),
            'context': {'default_course_id': self.course_id.id,
                        'default_material_id': self.id},
        }

    # NOTE: Diaktifkan setelah model ps.enrollment dibuat.
    # def action_mark_completed(self):
    #     """Tandai materi sebagai selesai oleh user yang sedang login"""
    #     self.ensure_one()
    #     enrollment = self.env['ps.enrollment'].search([
    #         ('course_id', '=', self.course_id.id),
    #         ('user_id', '=', self.env.user.id),
    #     ], limit=1)
    #
    #     if enrollment and self not in enrollment.completed_material_ids:
    #         enrollment.write({
    #             'completed_material_ids': [(4, self.id)]
    #         })
    #         enrollment._compute_progress()
    #
    #     return True