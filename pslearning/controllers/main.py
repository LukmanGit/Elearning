# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class PsLearningController(http.Controller):

    def _get_attempt(self, attempt_id):
        attempt = request.env['pslearning.test.attempt'].browse(attempt_id)
        if not attempt.exists() or attempt.user_id != request.env.user:
            raise AccessError("Akses ditolak.")
        return attempt

    def _get_enrollment(self, enrollment_id):
        enrollment = request.env['pslearning.enrollment'].browse(enrollment_id)
        if not enrollment.exists() or enrollment.user_id != request.env.user:
            raise AccessError("Akses ditolak.")
        return enrollment

    def _after_test_url(self, attempt):
        """Setelah test materi, kembali ke halaman belajar; selain itu ke form."""
        if attempt.material_id:
            return '/pslearning/learn/%d' % attempt.enrollment_id.id
        return '/web#id=%d&model=pslearning.enrollment&view_type=form' % attempt.enrollment_id.id

    # ==================================================================
    # HALAMAN TEST (PRE / POST per materi)
    # ==================================================================
    @http.route('/pslearning/pretest/<int:attempt_id>', auth='user', website=True)
    def pretest_page(self, attempt_id, **kwargs):
        try:
            attempt = self._get_attempt(attempt_id)
        except AccessError:
            return request.not_found()

        if attempt._check_and_expire():
            return request.redirect(self._after_test_url(attempt))

        if attempt.state == 'done':
            return request.redirect('/pslearning/pretest/result/%d' % attempt_id)

        if attempt.state != 'in_progress':
            return request.not_found()

        return request.render('pslearning.pretest_page', {
            'attempt': attempt,
            'questions': attempt.attempt_answer_ids.sorted('display_order'),
            'remaining_seconds': attempt._get_remaining_seconds(),
        })

    @http.route('/pslearning/pretest/<int:attempt_id>/save',
                type='json', auth='user', methods=['POST'])
    def pretest_save(self, attempt_id, question_id=None,
                     answer_id=None, essay_text=None, **kw):
        try:
            attempt = self._get_attempt(attempt_id)
        except AccessError:
            return {'error': 'access'}

        if attempt._check_and_expire():
            return {'expired': True}

        if attempt.state != 'in_progress':
            return {'error': 'not_in_progress'}

        rec = attempt.attempt_answer_ids.filtered(
            lambda a: a.question_id.id == int(question_id)
        )
        if not rec:
            return {'error': 'no_question'}

        if rec.question_type == 'multiple_choice':
            rec.selected_answer_id = int(answer_id) if answer_id else False
        else:
            rec.answer_text = (essay_text or '').strip()

        return {'ok': True, 'remaining': attempt._get_remaining_seconds()}

    @http.route('/pslearning/pretest/<int:attempt_id>/submit',
                auth='user', website=True, methods=['POST'], csrf=True)
    def pretest_submit(self, attempt_id, **post):
        try:
            attempt = self._get_attempt(attempt_id)
        except AccessError:
            return request.not_found()

        if attempt.state != 'in_progress':
            return request.redirect('/pslearning/pretest/result/%d' % attempt_id)

        for answer_rec in attempt.attempt_answer_ids:
            qid = answer_rec.question_id.id
            if answer_rec.question_type == 'multiple_choice':
                selected = post.get('answer_%d' % qid)
                answer_rec.selected_answer_id = int(selected) if selected else False
            else:
                answer_rec.answer_text = post.get('essay_%d' % qid, '').strip()

        attempt.action_submit()
        return request.redirect('/pslearning/pretest/result/%d' % attempt_id)

    @http.route('/pslearning/pretest/result/<int:attempt_id>', auth='user', website=True)
    def pretest_result(self, attempt_id, **kwargs):
        try:
            attempt = self._get_attempt(attempt_id)
        except AccessError:
            return request.not_found()

        if attempt.state != 'done':
            return request.redirect('/pslearning/pretest/%d' % attempt_id)

        return request.render('pslearning.pretest_result', {
            'attempt': attempt,
            'back_url': self._after_test_url(attempt),
        })

    # ==================================================================
    # HALAMAN BELAJAR (JALUR MATERI BERURUTAN)
    # ==================================================================
    @http.route('/pslearning/learn/<int:enrollment_id>', auth='user', website=True)
    def learn_page(self, enrollment_id, **kwargs):
        try:
            enrollment = self._get_enrollment(enrollment_id)
        except AccessError:
            return request.not_found()

        if enrollment.state == 'enrolled':
            enrollment.state = 'in_progress'

        return request.render('pslearning.learn_page', {
            'enrollment': enrollment,
            'path': enrollment.get_learning_path(),
            'all_done': enrollment._learning_done(),
        })

    @http.route('/pslearning/learn/<int:enrollment_id>/material/<int:material_id>/<string:kind>',
                auth='user', website=True)
    def learn_material_test(self, enrollment_id, material_id, kind, **kwargs):
        """Mulai Pre-Test / Post-Test sebuah materi."""
        try:
            enrollment = self._get_enrollment(enrollment_id)
        except AccessError:
            return request.not_found()
        if kind not in ('pretest', 'posttest'):
            return request.not_found()
        material = request.env['pslearning.material'].browse(material_id)
        if not material.exists() or material.course_id != enrollment.course_id:
            return request.not_found()
        try:
            action = enrollment.open_material_test(material, kind)
        except UserError:
            return request.redirect('/pslearning/learn/%d' % enrollment_id)
        return request.redirect(action['url'])

    @http.route('/pslearning/learn/<int:enrollment_id>/study/<int:material_id>',
                auth='user', website=True)
    def learn_material_view(self, enrollment_id, material_id, **kwargs):
        """Halaman materi penuh (konten + media). Tombol Tandai Selesai
        ada di bawah halaman ini, bukan di daftar materi."""
        try:
            enrollment = self._get_enrollment(enrollment_id)
        except AccessError:
            return request.not_found()

        material = request.env['pslearning.material'].browse(material_id)
        if not material.exists() or material.course_id != enrollment.course_id:
            return request.not_found()

        # Materi harus sudah terbuka (materi sebelumnya lengkap)
        if not enrollment._is_material_unlocked(material):
            return request.redirect('/pslearning/learn/%d' % enrollment_id)

        status = enrollment._material_step_status(material)
        # Pre-Test (jika ada) cukup SUDAH DIKERJAKAN, nilai berapa pun boleh lanjut
        if status['pre_required'] and not status['pre_done']:
            return request.redirect('/pslearning/learn/%d' % enrollment_id)

        return request.render('pslearning.material_detail', {
            'enrollment': enrollment,
            'material': material,
            'status': status,
        })

    @http.route('/pslearning/learn/<int:enrollment_id>/study/<int:material_id>/done',
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def learn_material_done(self, enrollment_id, material_id, **post):
        """Tandai materi selesai dari halaman materi, lalu kembali ke daftar
        agar Post-Test / materi berikutnya ikut terbuka."""
        try:
            enrollment = self._get_enrollment(enrollment_id)
        except AccessError:
            return request.not_found()

        material = request.env['pslearning.material'].browse(material_id)
        if not material.exists() or material.course_id != enrollment.course_id:
            return request.not_found()

        if enrollment._is_material_unlocked(material):
            status = enrollment._material_step_status(material)
            # Hanya boleh tandai selesai bila Pre-Test (jika ada) sudah dikerjakan
            if not (status['pre_required'] and not status['pre_done']):
                enrollment.completed_material_ids = [(4, material.id)]

        return request.redirect('/pslearning/learn/%d' % enrollment_id)

    @http.route('/pslearning/learn/<int:enrollment_id>/toggle',
                type='json', auth='user', methods=['POST'])
    def learn_toggle(self, enrollment_id, material_id=None, done=False, **kw):
        """Tandai / batal-tandai materi selesai (dengan gating berurutan)."""
        try:
            enrollment = self._get_enrollment(enrollment_id)
        except AccessError:
            return {'error': 'access'}

        material = request.env['pslearning.material'].browse(int(material_id))
        if not material.exists() or material.course_id != enrollment.course_id:
            return {'error': 'invalid'}

        if not enrollment._is_material_unlocked(material):
            return {'error': 'locked'}
        status = enrollment._material_step_status(material)
        if done and status['pre_required'] and not status['pre_done']:
            return {'error': 'pretest_required'}

        if done:
            enrollment.completed_material_ids = [(4, material.id)]
        else:
            enrollment.completed_material_ids = [(3, material.id)]

        return {
            'ok': True,
            'reload': True,
            'progress': round(enrollment.progress, 1),
        }

    @http.route('/pslearning/report/<int:enrollment_id>', auth='user', website=True)
    def learn_report(self, enrollment_id, **kwargs):
        try:
            enrollment = self._get_enrollment(enrollment_id)
        except AccessError:
            return request.not_found()

        if enrollment.progress < 100:
            return request.redirect('/pslearning/learn/%d' % enrollment_id)

        improvement = enrollment.posttest_score - enrollment.pretest_score
        return request.render('pslearning.learn_report', {
            'enrollment': enrollment,
            'path': enrollment.get_learning_path(),
            'improvement': improvement,
        })
