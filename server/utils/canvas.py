from canvasapi import Canvas

from server import app
from flask import session
from server.models import Offering
from server.utils.stub import get_dev_user, get_dev_course, get_dev_user_courses


def _get_client(key=None):
    if not key:
        key = session['access_token']
    return Canvas(app.config['CANVAS_SERVER_URL'], key)


def is_mock_canvas():
    return app.config['MOCK_CANVAS'] and app.config['FLASK_ENV'] == 'development'


def get_user(canvas_id, key=None):
    if is_mock_canvas():
        return get_dev_user(canvas_id)
    return _get_client(key).get_user(canvas_id)


def get_course(canvas_id, key=None):
    if is_mock_canvas():
        return get_dev_course(canvas_id)
    return _get_client(key).get_course(canvas_id)


def get_user_courses(user):
    if is_mock_canvas():
        return get_dev_user_courses(user.id)
    return user.get_courses(enrollment_status='active')


def is_course_valid(c):
    return not (not c) and \
        hasattr(c, 'id') and \
        hasattr(c, 'enrollments') and \
        hasattr(c, 'name') and \
        hasattr(c, 'course_code')


def get_user_courses_categorized(user):
    courses_raw = get_user_courses(user)
    staff_courses, student_courses, other = [], [], []
    for c in courses_raw:
        if not is_course_valid(c):
            continue
        for e in c.enrollments:
            if e["type"] == 'ta' or e["type"] == 'teacher':
                staff_courses.append(c)
            elif e["type"] == 'student':
                student_courses.append(c)
            else:
                other.append(c)
    # do not repeat
    staff_courses = list(set(staff_courses))
    student_courses = list(set(student_courses) - set(staff_courses))
    other = list(set(other) - set(staff_courses) - set(student_courses))
    return staff_courses, student_courses, other


def api_course_to_model(course):
    return Offering(
        canvas_id=course.id,
        name=course.name,
        code=course.course_code
    )
