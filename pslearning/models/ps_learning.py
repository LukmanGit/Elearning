# -*- coding: utf-8 -*-
from datetime import timedelta

from markupsafe import Markup, escape

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


class PasiCourse(models.Model):
    _name = 'pslearning.course'
    _description = 'PASI E-Learning Course'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Nama Mata Pelajaran', required=True, tracking=True)
    code = fields.Char(
        string='Kode Course',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    sequence = fields.Integer(string='Urutan', default=10)
    description = fields.Html(string='Deskripsi')
    image = fields.Image(string='Gambar Course', max_width=1024, max_height=1024)

    instructor_id = fields.Many2one(
        'res.users', string='Pengajar',
        default=lambda self: self.env.user, tracking=True,
    )
    category = fields.Selection([
        ('beginner', 'Pemula'),
        ('intermediate', 'Menengah'),
        ('advanced', 'Lanjutan'),
    ], string='Tingkat', default='beginner', required=True)

    duration = fields.Float(
        string='Durasi (Jam)',
        help='Estimasi total durasi pembelajaran',
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('upcoming', 'Segera Datang'),
        ('published', 'Dipublikasi'),
        ('archived', 'Diarsipkan'),
    ], string='Status', default='draft', tracking=True)
    publish_date = fields.Datetime(
        string='Tanggal Publikasi', readonly=True, copy=False, tracking=True,
        help='Tanggal course terakhir dipublikasikan. Dipakai untuk menandai course baru.')
    is_new = fields.Boolean(
        string='Course Baru', compute='_compute_is_new',
        help='True bila course dipublikasikan dalam 7 hari terakhir.')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Kode Course harus unik.'),
    ]

    material_ids = fields.One2many('pslearning.material', 'course_id', string='Materi Pembelajaran')
    enrollment_ids = fields.One2many('pslearning.enrollment', 'course_id', string='Peserta')
    enrollment_count = fields.Integer(string='Jumlah Peserta', compute='_compute_enrollment_count')
    pretest_id = fields.Many2one('pslearning.test', string='Pre-Test',
                                  domain="[('course_id', '=', id), ('test_type', '=', 'pretest')]")
    posttest_id = fields.Many2one('pslearning.test', string='Post-Test',
                                   domain="[('course_id', '=', id), ('test_type', '=', 'posttest')]")
    material_count = fields.Integer(string='Jumlah Materi', compute='_compute_material_count')

    # --- Kesiapan publikasi (materi + soal & jawaban pre/post-test) ---
    publish_ready = fields.Boolean(
        string='Siap Dipublikasi', compute='_compute_publish_state')
    publish_blocker = fields.Html(
        string='Syarat Publikasi Belum Terpenuhi',
        compute='_compute_publish_state', sanitize=False)

    @api.depends('material_ids')
    def _compute_material_count(self):
        for rec in self:
            rec.material_count = len(rec.material_ids)

    @api.depends('enrollment_ids')
    def _compute_enrollment_count(self):
        for rec in self:
            rec.enrollment_count = len(rec.enrollment_ids)

    @api.depends('state', 'publish_date')
    def _compute_is_new(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_new = bool(
                rec.state == 'published' and rec.publish_date
                and (now - rec.publish_date) <= timedelta(days=7)
            )

    # ------------------------------------------------------------------
    # Kesiapan publikasi
    # ------------------------------------------------------------------
    def _get_publish_issues(self):
        """Prasyarat publikasi: minimal satu materi, dan setiap test
        per-materi (Pre/Post-Test) yang dipasang harus lengkap soal & jawaban."""
        self.ensure_one()
        issues = []
        if not self.code or self.code == _('New'):
            issues.append(_('Kode Course belum tergenerate. Simpan course terlebih dahulu.'))
        if not self.material_ids:
            issues.append(_('Belum ada materi pembelajaran. Tambahkan minimal satu materi.'))

        def _check_test(label, test, material_name):
            if not test.question_ids:
                issues.append(_('%s materi "%s" (%s) belum memiliki soal.')
                              % (label, material_name, test.name))
                return
            mc = test.question_ids.filtered(lambda q: q.question_type == 'multiple_choice')
            if mc.filtered(lambda q: not q.answer_ids):
                issues.append(_('%s materi "%s" memiliki soal pilihan ganda tanpa pilihan jawaban.')
                              % (label, material_name))
            if mc.filtered(lambda q: q.answer_ids and not q.answer_ids.filtered('is_correct')):
                issues.append(_('%s materi "%s" memiliki soal pilihan ganda tanpa jawaban yang benar.')
                              % (label, material_name))

        for material in self.material_ids:
            if material.pretest_id:
                _check_test(_('Pre-Test'), material.pretest_id, material.name)
            if material.posttest_id:
                _check_test(_('Post-Test'), material.posttest_id, material.name)
        return issues

    @api.depends('code', 'material_ids',
                 'material_ids.pretest_id', 'material_ids.posttest_id',
                 'material_ids.pretest_id.question_ids',
                 'material_ids.pretest_id.question_ids.question_type',
                 'material_ids.pretest_id.question_ids.answer_ids',
                 'material_ids.pretest_id.question_ids.answer_ids.is_correct',
                 'material_ids.posttest_id.question_ids',
                 'material_ids.posttest_id.question_ids.question_type',
                 'material_ids.posttest_id.question_ids.answer_ids',
                 'material_ids.posttest_id.question_ids.answer_ids.is_correct')
    def _compute_publish_state(self):
        for rec in self:
            issues = rec._get_publish_issues()
            rec.publish_ready = not issues
            if issues:
                items = Markup('').join(
                    Markup('<li>%s</li>') % escape(i) for i in issues)
                rec.publish_blocker = Markup('<ul class="mb-0 ps-3">%s</ul>') % items
            else:
                rec.publish_blocker = False

    def action_enroll(self):
        self.ensure_one()
        if self.state != 'published':
            raise UserError(_('Course harus dipublikasi sebelum bisa didaftari.'))
        existing = self.env['pslearning.enrollment'].search([
            ('course_id', '=', self.id),
            ('user_id', '=', self.env.user.id),
        ], limit=1)
        if existing:
            raise UserError(_('Anda sudah terdaftar di course ini.'))
        self.env['pslearning.enrollment'].create({
            'course_id': self.id,
            'user_id': self.env.user.id,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Berhasil'),
                'message': _('Anda berhasil mendaftar ke course %s. '
                            'Course terdaftar dapat dicek pada dashboard anda.') % self.name,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_open_enrollments(self):
        self.ensure_one()
        return {
            'name': _('Peserta: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'pslearning.enrollment',
            'view_mode': 'tree,form',
            'domain': [('course_id', '=', self.id)],
            'context': {'default_course_id': self.id},
        }

    def action_open_materials(self):
        self.ensure_one()
        return {
            'name': _('Materi: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'pslearning.material',
            'view_mode': 'tree,form',
            'domain': [('course_id', '=', self.id)],
            'context': {'default_course_id': self.id},
        }

    # ------------------------------------------------------------------
    # CRUD Overrides
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') or vals.get('code') == _('New'):
                vals['code'] = self.env['ir.sequence'].next_by_code(
                    'pslearning.course'
                ) or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Action Buttons
    # ------------------------------------------------------------------
    def action_publish(self):
        for rec in self:
            issues = rec._get_publish_issues()
            if issues:
                raise UserError(_(
                    'Course "%s" belum dapat dipublikasikan. '
                    'Lengkapi hal berikut terlebih dahulu:\n\n- %s'
                ) % (rec.name, '\n- '.join(issues)))
            rec.write({
                'state': 'published',
                'publish_date': fields.Datetime.now(),
            })

    def action_set_upcoming(self):
        for rec in self:
            if not html2plaintext(rec.description or '').strip():
                raise UserError(_(
                    'Deskripsi course wajib diisi terlebih dahulu sebelum '
                    'course ditandai "Segera Datang".'
                ))
        self.write({'state': 'upcoming'})

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_archive_course(self):
        self.write({'state': 'archived'})