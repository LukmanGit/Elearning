# -*- coding: utf-8 -*-
import random
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PsTestAttempt(models.Model):
    _name = 'pslearning.test.attempt'
    _description = 'PS Learning Test Attempt'
    _inherit = ['mail.thread']
    _order = 'start_time desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    enrollment_id = fields.Many2one('pslearning.enrollment', string='Enrollment',
                                    required=True, ondelete='cascade')
    test_id = fields.Many2one('pslearning.test', string='Test',
                               required=True, ondelete='cascade')
    material_id = fields.Many2one('pslearning.material', string='Materi',
                                  ondelete='cascade',
                                  help='Materi yang rangkaian test-nya sedang dikerjakan.')
    user_id = fields.Many2one('res.users', string='Peserta',
                               required=True, default=lambda self: self.env.user)
    course_id = fields.Many2one(related='test_id.course_id', store=True, string='Course')
    test_type = fields.Selection(related='test_id.test_type', store=True)

    start_time = fields.Datetime(string='Waktu Mulai')
    end_time = fields.Datetime(string='Waktu Selesai')
    score = fields.Float(string='Nilai (%)', digits=(5, 2))
    state = fields.Selection([
        ('draft', 'Belum Dimulai'),
        ('in_progress', 'Sedang Dikerjakan'),
        ('done', 'Selesai'),
    ], string='Status', default='draft', tracking=True)

    attempt_answer_ids = fields.One2many('pslearning.attempt.answer', 'attempt_id',
                                          string='Jawaban')
    passing_score = fields.Float(related='test_id.passing_score', string='Nilai Kelulusan')
    is_passed = fields.Boolean(string='Lulus', compute='_compute_is_passed', store=True)

    material_names = fields.Char(string='Judul Materi',
                                 compute='_compute_material_info')
    question_count = fields.Integer(string='Total Soal',
                                    compute='_compute_material_info')
    answered_count = fields.Integer(string='Soal Dikerjakan',
                                    compute='_compute_material_info')

    @api.depends('material_id', 'attempt_answer_ids', 'attempt_answer_ids.selected_answer_id',
                 'attempt_answer_ids.answer_text', 'attempt_answer_ids.material_id')
    def _compute_material_info(self):
        for rec in self:
            if rec.material_id:
                rec.material_names = rec.material_id.name
            else:
                names = [n for n in rec.attempt_answer_ids.mapped('material_id.name') if n]
                rec.material_names = ', '.join(names) or _('Umum')
            rec.question_count = len(rec.attempt_answer_ids)
            rec.answered_count = len(rec.attempt_answer_ids.filtered(
                lambda a: a.selected_answer_id or (a.answer_text and a.answer_text.strip())
            ))

    @api.depends('user_id', 'test_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.user_id and rec.test_id:
                rec.display_name = '%s - %s' % (rec.user_id.name, rec.test_id.name)
            else:
                rec.display_name = _('Percobaan Baru')

    @api.depends('score', 'passing_score')
    def _compute_is_passed(self):
        for rec in self:
            rec.is_passed = rec.score >= rec.passing_score

    def _setup_attempt(self):
        if self.state != 'draft':
            raise UserError(_('Test sudah dimulai atau selesai.'))
        # Acak urutan soal dan simpan di display_order agar konsisten saat refresh
        questions = list(self.test_id.question_ids.sorted('sequence'))
        random.shuffle(questions)
        for order, question in enumerate(questions, start=1):
            self.env['pslearning.attempt.answer'].create({
                'attempt_id': self.id,
                'question_id': question.id,
                'display_order': order,
            })
        self.write({
            'state': 'in_progress',
            'start_time': fields.Datetime.now(),
        })

    def action_start(self):
        self.ensure_one()
        self._setup_attempt()
        return {
            'type': 'ir.actions.act_url',
            'url': '/pslearning/pretest/%d' % self.id,
            'target': 'self',
        }

    def action_submit(self):
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('Test tidak sedang dikerjakan.'))

        mc_answers = self.attempt_answer_ids.filtered(
            lambda a: a.question_id.question_type == 'multiple_choice'
        )
        total_score = sum(self.test_id.question_ids.mapped('score'))
        earned_score = sum(
            a.question_id.score for a in mc_answers if a.is_correct
        )
        self.write({
            'state': 'done',
            'end_time': fields.Datetime.now(),
            'score': (earned_score / total_score * 100) if total_score else 0.0,
        })

        # Setelah pre-test selesai, peserta resmi masuk fase belajar
        if self.enrollment_id and self.enrollment_id.state == 'enrolled':
            self.enrollment_id.state = 'in_progress'

    # ------------------------------------------------------------------
    # Timer helpers
    # ------------------------------------------------------------------
    def _get_deadline(self):
        """Batas waktu absolut = start_time + time_limit (menit).
        Return False jika tidak ada batas waktu."""
        self.ensure_one()
        if not self.start_time or not self.test_id.time_limit:
            return False
        return self.start_time + timedelta(minutes=self.test_id.time_limit)

    def _get_remaining_seconds(self):
        """Sisa detik. -1 = tanpa batas waktu, 0 = sudah habis."""
        self.ensure_one()
        deadline = self._get_deadline()
        if not deadline:
            return -1
        remaining = (deadline - fields.Datetime.now()).total_seconds()
        return int(remaining) if remaining > 0 else 0

    def _check_and_expire(self):
        """Jika attempt sedang dikerjakan tapi sudah lewat batas waktu,
        otomatis submit dengan jawaban yang sudah tersimpan. Return True
        jika baru saja di-submit karena kadaluarsa."""
        self.ensure_one()
        if self.state == 'in_progress':
            deadline = self._get_deadline()
            if deadline and fields.Datetime.now() >= deadline:
                self.action_submit()
                return True
        return False

    def _open_form(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pslearning.test.attempt',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }


class PsAttemptAnswer(models.Model):
    _name = 'pslearning.attempt.answer'
    _description = 'PS Learning Attempt Answer'
    _order = 'attempt_id, display_order, question_id'

    attempt_id = fields.Many2one('pslearning.test.attempt', string='Percobaan',
                                  required=True, ondelete='cascade')
    question_id = fields.Many2one('pslearning.question', string='Soal',
                                   required=True, ondelete='cascade')
    display_order = fields.Integer(string='Urutan Tampil', default=0)
    question_text = fields.Html(related='question_id.question_text', string='Pertanyaan')
    question_type = fields.Selection(related='question_id.question_type')
    material_id = fields.Many2one(related='question_id.material_id', string='Materi')

    selected_answer_id = fields.Many2one(
        'pslearning.answer', string='Jawaban Dipilih',
        domain="[('question_id', '=', question_id)]"
    )
    answer_text = fields.Text(string='Jawaban Esai')
    is_correct = fields.Boolean(string='Benar', compute='_compute_is_correct', store=True)

    @api.depends('selected_answer_id')
    def _compute_is_correct(self):
        for rec in self:
            rec.is_correct = bool(
                rec.selected_answer_id and rec.selected_answer_id.is_correct
            )