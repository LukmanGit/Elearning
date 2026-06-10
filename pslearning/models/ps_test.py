# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PsTest(models.Model):
    _name = 'pslearning.test'
    _description = 'PS Learning Test'
    _inherit = ['mail.thread']
    _order = 'course_id, test_type'

    name = fields.Char(string='Nama Test', required=True, tracking=True)
    course_id = fields.Many2one('pslearning.course', string='Course',
                                required=True, ondelete='cascade', tracking=True)
    material_id = fields.Many2one(
        'pslearning.material', string='Materi',
        domain="[('course_id', '=', course_id)]",
        help='Materi acuan test ini. Otomatis menjadi nilai default '
             '"Materi Terkait" untuk setiap soal baru, agar tidak salah pilih.')
    test_type = fields.Selection([
        ('pretest', 'Pre-Test'),
        ('posttest', 'Post-Test'),
    ], string='Tipe', required=True, default='pretest', tracking=True)
    time_limit = fields.Integer(string='Batas Waktu (Menit)', default=0,
                                help='0 = tidak ada batas waktu')
    passing_score = fields.Float(string='Nilai Kelulusan (%)', default=70.0)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Dipublikasi'),
    ], string='Status', default='draft', tracking=True)
    question_ids = fields.One2many('pslearning.question', 'test_id', string='Soal')
    question_count = fields.Integer(string='Jumlah Soal', compute='_compute_question_count')

    @api.depends('question_ids')
    def _compute_question_count(self):
        for rec in self:
            rec.question_count = len(rec.question_ids)

    def action_publish(self):
        for rec in self:
            if not rec.question_ids:
                raise UserError(_('Test harus memiliki minimal 1 soal sebelum dipublikasi.'))
            if not rec.time_limit or rec.time_limit <= 0:
                raise UserError(_(
                    'Batas Waktu (menit) test "%s" tidak boleh 0. '
                    'Isi batas waktu sebelum mempublikasikan test.'
                ) % rec.name)
            rec.state = 'published'

    def action_set_draft(self):
        self.write({'state': 'draft'})


class PsQuestion(models.Model):
    _name = 'pslearning.question'
    _description = 'PS Learning Question'
    _order = 'test_id, sequence, id'

    test_id = fields.Many2one('pslearning.test', string='Test',
                               required=True, ondelete='cascade')
    material_id = fields.Many2one('pslearning.material', string='Materi Terkait',
                                   domain="[('course_id', '=', parent.course_id)]",
                                   help='Opsional: soal ini berkaitan dengan materi tertentu')
    sequence = fields.Integer(string='Urutan', default=10)
    question_text = fields.Html(string='Pertanyaan', required=True)
    question_type = fields.Selection([
        ('multiple_choice', 'Pilihan Ganda'),
        ('essay', 'Esai'),
    ], string='Tipe Soal', default='multiple_choice', required=True)
    answer_ids = fields.One2many('pslearning.answer', 'question_id', string='Pilihan Jawaban')
    score = fields.Float(string='Poin', default=1.0)

    @api.constrains('answer_ids', 'question_type')
    def _check_answers(self):
        for rec in self:
            if rec.question_type == 'multiple_choice':
                correct = rec.answer_ids.filtered('is_correct')
                if rec.answer_ids and not correct:
                    raise UserError(
                        _('Soal "%s" harus memiliki minimal 1 jawaban yang benar.') % rec.question_text
                    )


class PsAnswer(models.Model):
    _name = 'pslearning.answer'
    _description = 'PS Learning Answer Choice'
    _order = 'question_id, sequence'

    question_id = fields.Many2one('pslearning.question', string='Pertanyaan',
                                   required=True, ondelete='cascade')
    sequence = fields.Integer(string='Urutan', default=10)
    answer_text = fields.Char(string='Pilihan Jawaban', required=True)
    is_correct = fields.Boolean(string='Jawaban Benar')
