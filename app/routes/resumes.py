import json

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, abort, send_file, Response)
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Resume, Application
from ..utils import storage
from ..utils.extract import allowed_file, extract_text, save_upload
from ..utils.parser import analyze_resume_text
from ..utils.analyzer import health_checklist, score_band
from ..utils.proofread import proofread
from ..utils import diff

resumes_bp = Blueprint("resumes", __name__, url_prefix="/resumes")


def get_own_resume(resume_id):
    r = db.session.get(Resume, resume_id)
    if r is None or r.user_id != current_user.id:
        abort(404)
    return r


def rebuild_analysis(resume):
    """Re-run the pipeline from stored raw text (no re-upload needed)."""
    return analyze_resume_text(resume.raw_text)


@resumes_bp.route("/")
@login_required
def index():
    active = Resume.query.filter_by(user_id=current_user.id, is_archived=False)\
                         .order_by(Resume.created_at.desc()).all()
    archived = Resume.query.filter_by(user_id=current_user.id, is_archived=True)\
                           .order_by(Resume.created_at.desc()).all()
    used = {}
    for r in active + archived:
        used[r.id] = Application.query.filter_by(resume_id=r.id).count()
    return render_template("resumes.html", active=active, archived=archived, used=used)


@resumes_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    title = request.form.get("title", "").strip()
    file = request.files.get("file")
    if not title:
        flash("Give this resume version a title, e.g. 'Backend Resume v4'.", "error")
        return redirect(url_for("resumes.index"))
    if not file or not allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        flash("Please upload a PDF or DOCX file.", "error")
        return redirect(url_for("resumes.index"))

    data = file.read()
    stored, ext = save_upload(data, file.filename, current_user.id)
    try:
        text = extract_text(stored, ext)
    except Exception:
        flash("Could not read that file (scanned/image PDFs are not supported).", "error")
        return redirect(url_for("resumes.index"))
    if not text or len(text.split()) < 30:
        flash("Extracted text was too short — is this a scanned PDF? Try a text-based file.", "error")
        return redirect(url_for("resumes.index"))

    resume = Resume(
        user_id=current_user.id, title=title,
        original_filename=file.filename, stored_filename=stored, file_ext=ext,
        raw_text=text, word_count=len(text.split()),
    )
    analysis = analyze_resume_text(text)
    resume.sections_json = json.dumps(analysis["sections"])
    resume.skills_json = json.dumps(analysis["skills"])
    resume.contact_json = json.dumps(analysis["contact"])
    resume.education_json = json.dumps(analysis["education"])
    resume.experience_json = json.dumps(analysis["experience"])
    resume.projects_json = json.dumps(analysis["projects"])
    resume.certifications_json = json.dumps(analysis["certifications"])
    health = health_checklist(analysis, text)
    resume.health_score = health["score"]

    db.session.add(resume)
    db.session.commit()
    flash(f"'{title}' uploaded and analyzed. Checklist score: {health['score']}/100.", "success")
    return redirect(url_for("resumes.detail", resume_id=resume.id))


@resumes_bp.route("/<int:resume_id>")
@login_required
def detail(resume_id):
    resume = get_own_resume(resume_id)
    analysis = rebuild_analysis(resume)
    health = health_checklist(analysis, resume.raw_text)
    apps = Application.query.filter_by(resume_id=resume.id).all()
    report = proofread(resume.raw_text)
    return render_template("resume_detail.html", resume=resume, analysis=analysis,
                           health=health, band=score_band(health["score"]), apps=apps,
                           report=report)


@resumes_bp.route("/<int:resume_id>/rename", methods=["POST"])
@login_required
def rename(resume_id):
    resume = get_own_resume(resume_id)
    title = request.form.get("title", "").strip()
    if title:
        resume.title = title
        db.session.commit()
        flash("Version renamed.", "success")
    return redirect(url_for("resumes.detail", resume_id=resume.id))


@resumes_bp.route("/<int:resume_id>/archive", methods=["POST"])
@login_required
def archive(resume_id):
    resume = get_own_resume(resume_id)
    resume.is_archived = not resume.is_archived
    db.session.commit()
    flash(f"Version {'archived' if resume.is_archived else 'restored'}.", "success")
    return redirect(url_for("resumes.index"))


@resumes_bp.route("/<int:resume_id>/delete", methods=["POST"])
@login_required
def delete(resume_id):
    resume = get_own_resume(resume_id)
    stored = resume.stored_filename
    for a in Application.query.filter_by(resume_id=resume.id).all():
        a.resume_id = None
    db.session.delete(resume)
    db.session.commit()
    storage.delete_file(stored)
    flash("Resume version deleted.", "success")
    return redirect(url_for("resumes.index"))


@resumes_bp.route("/compare")
@login_required
def compare_form():
    resumes = Resume.query.filter_by(user_id=current_user.id, is_archived=False)\
                          .order_by(Resume.created_at.desc()).all()
    return render_template("compare.html", resumes=resumes)


@resumes_bp.route("/compare/results")
@login_required
def compare_results():
    a_id = request.args.get("a", type=int)
    b_id = request.args.get("b", type=int)
    ra, rb = get_own_resume(a_id), get_own_resume(b_id)
    result = diff.compare_versions(ra, rb)
    return render_template("compare.html", resumes=Resume.query.filter_by(
        user_id=current_user.id, is_archived=False).all(),
        ra=ra, rb=rb, result=result)


@resumes_bp.route("/<int:resume_id>/download")
@login_required
def download(resume_id):
    resume = get_own_resume(resume_id)
    if not storage.exists(resume.stored_filename):
        abort(404)
    return send_file(storage.open_file(resume.stored_filename),
                     as_attachment=True, download_name=resume.original_filename)


@resumes_bp.route("/<int:resume_id>/export")
@login_required
def export_txt(resume_id):
    resume = get_own_resume(resume_id)
    analysis = rebuild_analysis(resume)
    health = health_checklist(analysis, resume.raw_text)
    lines = [
        f"RESUME ANALYSIS REPORT", "=" * 40, f"Version: {resume.title}",
        f"Words: {resume.word_count}", f"Checklist score: {health['score']}/100 "
        f"(transparent heuristic, not an objective ranking)", "",
    ]
    for c in health["checks"]:
        lines.append(f"[{'x' if c['passed'] else ' '}] {c['label']} ({c['points']}/{c['max']}) {c['note']}")
    lines += ["", "SKILLS DETECTED", "-" * 40]
    for s in analysis["skills"][:30]:
        lines.append(f"{s['name']:<25} x{s['count']}  in: {', '.join(s['in_section']) or '-'}")
    return Response("\n".join(lines), mimetype="text/plain",
                    headers={"Content-Disposition": f"attachment; filename=analysis_{resume.id}.txt"})
