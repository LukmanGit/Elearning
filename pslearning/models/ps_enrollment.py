# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PsEnrollment(models.Model):
    _name = 'pslearning.enrollment'
    _description = 'PS Learning Enrollment'
    _inherit = ['mail.thread']
    _order = 'enrollment_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    course_id = fields.Many2one('pslearning.course', string='Course',
                                required=True, ondelete='cascade', tracking=True)
    user_id = fields.Many2one('res.users', string='Peserta',
                              required=True, default=lambda self: self.env.user, tracking=True)

    enrollment_date = fields.Datetime(string='Tanggal Daftar',
                                      default=fields.Datetime.now, tracking=True)
    completion_date = fields.Datetime(string='Tanggal Selesai', tracking=True)

    state = fields.Selection([
        ('enrolled', 'Terdaftar'),
        ('in_progress', 'Sedang Belajar'),
        ('completed', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ], string='Status', default='enrolled', tracking=True)

    completed_material_ids = fields.Many2many(
        'pslearning.material',
        'pslearning_enrollment_material_rel',
        'enrollment_id', 'material_id',
        string='Materi yang Sudah Dipelajari'
    )

    progress = fields.Float(string='Progress (%)', compute='_compute_progress', store=True)

    # Relasi tanpa domain: dipakai sebagai trigger compute yang andal.
    attempt_ids = fields.One2many('pslearning.test.attempt', 'enrollment_id',
                                  string='Semua Percobaan Test')
    pretest_attempt_ids = fields.One2many('pslearning.test.attempt', 'enrollment_id',
                                           string='Percobaan Pre-Test',
                                           domain=[('test_type', '=', 'pretest')])
    posttest_attempt_ids = fields.One2many('pslearning.test.attempt', 'enrollment_id',
                                            string='Percobaan Post-Test',
                                            domain=[('test_type', '=', 'posttest')])

    # Ringkasan agregat (semua materi)
    is_pretest_done = fields.Boolean(string='Semua Pre-Test Selesai',
                                     compute='_compute_aggregate', store=True)
    is_posttest_done = fields.Boolean(string='Semua Post-Test Selesai',
                                      compute='_compute_aggregate', store=True)
    pretest_score = fields.Float(string='Rata-rata Pre-Test',
                                 compute='_compute_aggregate', store=True)
    posttest_score = fields.Float(string='Rata-rata Post-Test',
                                  compute='_compute_aggregate', store=True)
    notes = fields.Text(string='Catatan')

    _sql_constraints = [
        ('user_course_unique', 'UNIQUE(user_id, course_id)',
         'User hanya boleh terdaftar sekali di setiap course!'),
    ]

    @api.depends('user_id', 'course_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.user_id and rec.course_id:
                rec.display_name = '%s - %s' % (rec.user_id.name, rec.course_id.name)
            else:
                rec.display_name = _('Pendaftaran Baru')

    # ------------------------------------------------------------------
    # Helper jalur pembelajaran per materi
    # ------------------------------------------------------------------
    def _published_materials(self):
        self.ensure_one()
        return self.course_id.material_ids.filtered(
            lambda m: m.state == 'published'
        ).sorted(lambda m: (m.sequence, m.id))

    def _test_done(self, test, material):
        """True bila ada attempt 'done' untuk test+material ini."""
        return any(
            a.state == 'done' and a.test_id.id == test.id
            and a.material_id.id == material.id
            for a in self.attempt_ids
        )

    def _test_best_score(self, test, material):
        done = self.attempt_ids.filtered(
            lambda a: a.state == 'done' and a.test_id.id == test.id
            and a.material_id.id == material.id)
        return max(done.mapped('score')) if done else 0.0

    def _material_step_status(self, material):
        """Status satu materi: pre-test, belajar, post-test, lengkap."""
        self.ensure_one()
        pre = material._resolve_test('pretest')
        post = material._resolve_test('posttest')
        pre_required = bool(pre)
        post_required = bool(post)
        pre_done = (not pre_required) or self._test_done(pre, material)
        learned = material.id in self.completed_material_ids.ids
        post_done = (not post_required) or self._test_done(post, material)
        return {
            'pre_required': pre_required,
            'pre_done': pre_done,
            'pre_score': self._test_best_score(pre, material) if pre else 0.0,
            'learned': learned,
            'post_required': post_required,
            'post_done': post_done,
            'post_score': self._test_best_score(post, material) if post else 0.0,
            'complete': pre_done and learned and post_done,
        }

    def _is_material_unlocked(self, material):
        """Materi terbuka bila SEMUA materi sebelumnya sudah lengkap."""
        self.ensure_one()
        mats = self._published_materials()
        if material not in mats:
            return False
        idx = list(mats).index(material)
        return all(self._material_step_status(m)['complete'] for m in mats[:idx])

    def get_learning_path(self):
        """Daftar materi berurutan beserta status & status terkunci.
        Dipakai oleh halaman belajar dan report."""
        self.ensure_one()
        path = []
        prev_complete = True
        for index, m in enumerate(self._published_materials(), start=1):
            st = self._material_step_status(m)
            st.update({
                'index': index,
                'material': m,
                'unlocked': prev_complete,
            })
            path.append(st)
            prev_complete = prev_complete and st['complete']
        return path

    def _learning_done(self):
        self.ensure_one()
        mats = self._published_materials()
        return all(self._material_step_status(m)['complete'] for m in mats) if mats else True

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('attempt_ids.state', 'attempt_ids.test_id', 'attempt_ids.material_id',
                 'completed_material_ids', 'course_id.material_ids',
                 'course_id.material_ids.state', 'course_id.material_ids.pretest_id',
                 'course_id.material_ids.posttest_id')
    def _compute_progress(self):
        for rec in self:
            mats = rec._published_materials()
            total_steps = 0
            done_steps = 0
            for m in mats:
                st = rec._material_step_status(m)
                if st['pre_required']:
                    total_steps += 1
                    done_steps += 1 if st['pre_done'] else 0
                total_steps += 1  # langkah belajar materi
                done_steps += 1 if st['learned'] else 0
                if st['post_required']:
                    total_steps += 1
                    done_steps += 1 if st['post_done'] else 0
            rec.progress = (100.0 * done_steps / total_steps) if total_steps else 0.0

            if rec.state == 'cancelled':
                continue
            if rec.progress >= 100.0:
                if rec.state != 'completed':
                    rec.state = 'completed'
                    rec.completion_date = fields.Datetime.now()
            else:
                if rec.state == 'completed':
                    rec.state = 'in_progress'
                    rec.completion_date = False
                elif rec.progress > 0.0 and rec.state == 'enrolled':
                    rec.state = 'in_progress'

    @api.depends('attempt_ids.state', 'attempt_ids.score', 'attempt_ids.test_id',
                 'attempt_ids.material_id', 'completed_material_ids',
                 'course_id.material_ids', 'course_id.material_ids.state',
                 'course_id.material_ids.pretest_id', 'course_id.material_ids.posttest_id')
    def _compute_aggregate(self):
        for rec in self:
            mats = rec._published_materials()
            statuses = [rec._material_step_status(m) for m in mats]
            pre_mats = [s for s in statuses if s['pre_required']]
            post_mats = [s for s in statuses if s['post_required']]
            # Hanya hijau bila memang ADA test wajib dan semuanya sudah selesai.
            # Bila tidak ada test sama sekali, jangan tampilkan sebagai "selesai".
            rec.is_pretest_done = bool(pre_mats) and all(s['pre_done'] for s in pre_mats)
            rec.is_posttest_done = bool(post_mats) and all(s['post_done'] for s in post_mats)
            rec.pretest_score = (
                sum(s['pre_score'] for s in pre_mats) / len(pre_mats)
            ) if pre_mats else 0.0
            rec.posttest_score = (
                sum(s['post_score'] for s in post_mats) / len(post_mats)
            ) if post_mats else 0.0

    @api.constrains('completed_material_ids')
    def _check_pretest_before_learning(self):
        for rec in self:
            for m in rec.completed_material_ids:
                pre = m._resolve_test('pretest')
                if pre and not rec._test_done(pre, m):
                    raise ValidationError(_(
                        'Selesaikan Pre-Test materi "%s" terlebih dahulu '
                        'sebelum menandainya selesai.'
                    ) % m.name)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_start_learning(self):
        self.ensure_one()
        if self.state == 'enrolled':
            self.state = 'in_progress'
        return {
            'type': 'ir.actions.act_url',
            'url': '/pslearning/learn/%d' % self.id,
            'target': 'self',
        }

    def open_material_test(self, material, kind):
        """Mulai/lanjutkan Pre/Post-Test untuk satu materi. Return URL attempt."""
        self.ensure_one()
        test = material._resolve_test(kind)
        if not test:
            raise UserError(_('Materi ini belum memiliki %s.') % (
                _('Pre-Test') if kind == 'pretest' else _('Post-Test')))
        if test.state != 'published':
            raise UserError(_('Test untuk materi ini belum dipublikasi.'))
        if not self._is_material_unlocked(material):
            raise UserError(_(
                'Materi "%s" masih terkunci. Selesaikan materi sebelumnya '
                'terlebih dahulu.'
            ) % material.name)
        if kind == 'posttest':
            st = self._material_step_status(material)
            if not (st['pre_done'] and st['learned']):
                raise UserError(_(
                    'Selesaikan Pre-Test dan pelajari materi "%s" sebelum '
                    'mengerjakan Post-Test.'
                ) % material.name)

        existing = self.env['pslearning.test.attempt'].search([
            ('enrollment_id', '=', self.id),
            ('test_id', '=', test.id),
            ('material_id', '=', material.id),
            ('state', 'in', ['draft', 'in_progress']),
        ], limit=1)
        attempt = existing or self.env['pslearning.test.attempt'].create({
            'enrollment_id': self.id,
            'test_id': test.id,
            'material_id': material.id,
            'user_id': self.env.user.id,
        })
        if not existing:
            attempt._setup_attempt()
        return {
            'type': 'ir.actions.act_url',
            'url': '/pslearning/pretest/%d' % attempt.id,
            'target': 'self',
        }

    def action_view_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/pslearning/report/%d' % self.id,
            'target': 'self',
        }

    def action_cancel(self):
        for rec in self:
            if rec.state == 'completed':
                raise UserError(_(
                    'Enrollment yang sudah selesai tidak dapat dibatalkan.'
                ))
        self.write({'state': 'cancelled'})

    def action_reactivate(self):
        for rec in self:
            rec.state = 'in_progress' if rec.completed_material_ids else 'enrolled'
