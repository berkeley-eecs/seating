import re

from flask import abort, redirect, render_template, request, send_file, url_for, flash
from flask_login import current_user, login_required

from server import app
from server.models import db, Offering, Exam, Room, Seat, Student
from server.form import ExamForm, RoomForm, ChooseRoomForm, StudentForm, DeleteStudentForm, \
    AssignForm, EmailForm
from server.utils.auth import google_oauth
import server.utils.canvas as canvas_client
from server.utils.data import validate_room, validate_students
from server.utils.exception import DataValidationError
from server.utils.url import apply_converter
from server.utils.assign import assign_students
from server.utils.email import email_students

apply_converter()

# region Offering CRUDI


@app.route('/')
@login_required
def index():
    """
    Path: /
    Home page, which needs to be logged in to access.
    After logging in, fetch and present a list of course offerings.
    """

    user = canvas_client.get_user(current_user.canvas_id)
    staff_course_dics, student_course_dics, others = canvas_client.get_user_courses_categorized(
        user)
    staff_offerings = [canvas_client.api_course_to_model(c) for c in staff_course_dics]
    student_offerings = [canvas_client.api_course_to_model(c) for c in student_course_dics]
    return render_template("select_offering.html.j2",
                           title="Select a Course Offering",
                           staff_offerings=staff_offerings,
                           student_offerings=student_offerings,
                           other_offerings=others)


@app.route('/<offering:offering>/')
def offering(offering):
    """
    Path: /offerings/<canvas_id>
    Shows all exams created for a course offering.
    """
    is_staff = str(offering.canvas_id) in current_user.staff_offerings
    return render_template("select_exam.html.j2",
                           exams=offering.exams, offering=offering, is_staff=is_staff)

# endregion

# region Exam CRUDI


@app.route("/<offering:offering>/exams/new/", methods=["GET", "POST"])
def new_exam(offering):
    """
    Path: /offerings/<canvas_id>/exams/new
    Creates a new exam for a course offering.
    """
    # offering urls only checks login but does not check staff status
    # this is exam creation route but still handled by offering converter
    # it does need to check staff status, so we do it here
    if str(offering.canvas_id) not in current_user.staff_offerings:
        abort(403, "You are not a staff member in this offering.")
    form = ExamForm()
    if form.validate_on_submit():
        Exam.query.filter_by(offering_canvas_id=offering.canvas_id).update({"is_active": False})
        try:
            exam = Exam(offering_canvas_id=offering.canvas_id,
                        name=form.name.data,
                        display_name=form.display_name.data,
                        is_active=True)
            db.session.add(exam)
            db.session.commit()
            return redirect(url_for('offering', offering=offering))
        except Exception as e:
            db.session.rollback()
            abort(400, "An error occurred when inserting exam of name={}\n{}".format(
                form.name.data, str(e)))
            return redirect(url_for('offering', offering=offering))
    return render_template("new_exam.html.j2",
                           title="Create an Exam for {}".format(offering.name),
                           form=form)


@app.route("/<exam:exam>/delete/", methods=["GET", "DELETE"])
def delete_exam(exam):
    """
    Path: /offerings/<canvas_id>/exams/<exam_name>/delete
    Deletes an exam for a course offering.
    """
    db.session.delete(exam)
    db.session.commit()
    return redirect(url_for('offering', offering=exam.offering))


@app.route("/<exam:exam>/toggle/", methods=["GET", "PATCH"])
def toggle_exam(exam):
    """
    Path: /offerings/<canvas_id>/exams/<exam_name>/toggle
    Toggles an exam for a course offering.
    """
    if exam.is_active:
        exam.is_active = False
    else:
        # only one exam can be active at a time, so deactivate all others first
        Exam.query.filter_by(offering_canvas_id=exam.offering_canvas_id).update(
            {"is_active": False})
        exam.is_active = True
    db.session.commit()
    return redirect(url_for('offering', offering=exam.offering))


@app.route('/<exam:exam>/')
def exam(exam):
    """
    Path: /offerings/<canvas_id>/exams/<exam_name>
    Front page for an exam, which essentially shows all rooms created for an exam.
    """
    return render_template('exam.html.j2', exam=exam)
# endregion

# region Room CRUDI


@app.route('/<exam:exam>/rooms/import/')
@google_oauth.required(scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
def import_room(exam):
    """
    Path: /offerings/<canvas_id>/exams/<exam_name>/rooms/import
    """
    new_form = RoomForm()
    choose_form = ChooseRoomForm()
    return render_template('new_room.html.j2',
                           exam=exam, new_form=new_form, choose_form=choose_form)


@app.route('/<exam:exam>/rooms/import/new/', methods=['GET', 'POST'])
@google_oauth.required(scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
def new_room(exam):
    """
    Path: /offerings/<canvas_id>/exams/<exam_name>/rooms/import/new
    """
    new_form = RoomForm()
    choose_form = ChooseRoomForm()
    room = None
    if new_form.validate_on_submit():
        try:
            room = validate_room(exam, new_form)
        except Exception as e:
            new_form.sheet_url.errors.append(str(e))
        if new_form.create_room.data:
            try:
                db.session.add(room)
                db.session.commit()
                # TODO: proper error handling
            except:
                new_form.sheet_url.errors.append(
                    "Room name {} already exists for this exam.".format(room.name))
            return redirect(url_for('exam', exam=exam))
    return render_template('new_room.html.j2',
                           exam=exam, new_form=new_form, choose_form=choose_form, room=room)


MASTER_ROOM_SHEET = 'https://docs.google.com/spreadsheets/d/' + \
    '1cHKVheWv2JnHBorbtfZMW_3Sxj9VtGMmAUU2qGJ33-s/edit?usp=sharing'


@app.route('/<exam:exam>/rooms/import/choose/', methods=['GET', 'POST'])
@google_oauth.required(scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
def choose_room(exam):
    """
    Path: /offerings/<canvas_id>/exams/<exam_name>/rooms/import/choose
    """
    new_form = RoomForm()
    choose_form = ChooseRoomForm()
    if choose_form.validate_on_submit():
        for r in choose_form.rooms.data:
            f = RoomForm(
                display_name=r,
                sheet_url=MASTER_ROOM_SHEET, sheet_range=r)
            room = None
            try:
                room = validate_room(exam, f)
                # TODO: proper error handling
            except Exception as e:
                choose_form.rooms.errors.append(str(e))
            if room:
                db.session.add(room)
                db.session.commit()
        return redirect(url_for('exam', exam=exam))
    return render_template('new_room.html.j2',
                           exam=exam, new_form=new_form, choose_form=choose_form)


@app.route('/<exam:exam>/rooms/<string:name>/delete', methods=['GET', 'DELETE'])
def delete_room(exam, name):
    """
    Path: /offerings/<canvas_id>/exams/<exam_name>/rooms/<room_name>/delete
    Deletes a room for an exam.
    """
    room = Room.query.filter_by(exam_id=exam.id, name=name).first_or_404()
    if room:
        db.session.delete(room)
        db.session.commit()
    return render_template('exam.html.j2', exam=exam)


@app.route('/<exam:exam>/rooms/<string:name>/')
def room(exam, name):
    """
    Path: /offerings/<canvas_id>/exams/<exam_name>/rooms/<room_name>
    Displays the room diagram, with an optional seat highlighted.
    """
    room = Room.query.filter_by(exam_id=exam.id, name=name).first_or_404()
    seat = request.args.get('seat')
    return render_template('room.html.j2', exam=exam, room=room, seat=seat)
# endregion

# region Student CRUDI


@app.route('/<exam:exam>/students/import/', methods=['GET', 'POST'])
@google_oauth.required(scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
def new_students(exam):
    form = StudentForm()
    if form.validate_on_submit():
        try:
            students = validate_students(exam, form)
            db.session.add_all(students)
            db.session.commit()
            return redirect(url_for('students', exam=exam))
        except DataValidationError as e:
            form.sheet_url.errors.append(str(e))
    return render_template('new_students.html.j2', exam=exam, form=form)


@app.route('/<exam:exam>/students/delete/', methods=['GET', 'POST'])
def delete_students(exam):
    form = DeleteStudentForm()
    deleted, did_not_exist = set(), set()
    if form.validate_on_submit():
        if not form.use_all_emails.data:
            emails = [x for x in re.split(r'\s|,', form.emails.data) if x]
            students = Student.query.filter(
                Student.email.in_(emails) & Student.exam_id == exam.id)
        else:
            students = Student.query.filter_by(exam_id=exam.id)
        deleted = {student.email for student in students}
        did_not_exist = set()
        if not form.use_all_emails.data:
            did_not_exist = set(emails) - deleted
        students.delete()
        db.session.commit()
        if not deleted and not did_not_exist:
            abort(404, "No change has been made.")
    return render_template('delete_students.html.j2',
                           exam=exam, form=form, deleted=deleted, did_not_exist=did_not_exist)


@app.route('/<exam:exam>/students/')
def students(exam):
    # TODO load assignment and seat at the same time?
    return render_template('students.html.j2', exam=exam, students=exam.students)


@app.route('/<exam:exam>/students/<string:canvas_id>/')
def student(exam, canvas_id):
    student = Student.query.filter_by(
        exam_id=exam.id, canvas_id=canvas_id).first_or_404()
    return render_template('student.html.j2', exam=exam, student=student)


@app.route('/<exam:exam>/students/<string:canvas_id>/delete', methods=['GET', 'DELETE'])
def delete_student(exam, canvas_id):
    student = Student.query.filter_by(
        exam_id=exam.id, canvas_id=canvas_id).first_or_404()
    if student:
        db.session.delete(student)
        db.session.commit()
    return redirect(url_for('students', exam=exam))


@app.route('/<exam:exam>/students/assign/', methods=['GET', 'POST'])
def assign(exam):
    form = AssignForm()
    if form.validate_on_submit():
        success, payload = assign_students(exam)
        if not success:
            return payload
        db.session.add_all(payload)
        db.session.commit()
        return redirect(url_for('students', exam=exam))
    return render_template('assign.html.j2', exam=exam, form=form)


@app.route('/<exam:exam>/students/email/', methods=['GET', 'POST'])
def email(exam):
    form = EmailForm()
    if form.validate_on_submit():
        email_students(exam, form)
        return redirect(url_for('students', exam=exam))
    return render_template('email.html.j2', exam=exam, form=form)
# endregion

# region Misc


@app.route('/help/')
@login_required
def help():
    return render_template('help.html.j2', title="Help")


@app.route('/favicon.ico')
def favicon():
    return send_file('static/img/favicon.ico')


@app.route('/students-template.png')
def students_template():
    return send_file('static/img/students-template.png')
# endregion

# region Student-facing pages


@app.route('/seats/<int:seat_id>/')
def student_single_seat(seat_id):
    seat = Seat.query.filter_by(id=seat_id).first_or_404()
    return render_template('seat.html.j2', room=seat.room, seat=seat)
# endregion


@app.route('/<exam:exam>/students/photos/', methods=['GET', 'POST'])
def new_photos(exam):
    return render_template('new_photos.html.j2', exam=exam)


@app.route('/<exam:exam>/students/<string:email>/photo')
def photo(exam, email):
    student = Student.query.filter_by(
        exam_id=exam.id, email=email).first_or_404()
    photo_path = '{}/{}/{}.jpeg'.format(app.config['PHOTO_DIRECTORY'],
                                        exam.offering_canvas_id, student.canvas_id)
    return send_file(photo_path, mimetype='image/jpeg')
