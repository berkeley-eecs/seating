from __future__ import annotations
import json

FAKE_USERS = None
FAKE_COURSES = None
FAKE_ENROLLMENTS = None


class FakeCanvas:
    def __init__(self) -> None:
        global FAKE_USERS, FAKE_COURSES, FAKE_ENROLLMENTS
        with open('server/services/canvas/fake_data/fake_users.json', 'r') as f:
            FAKE_USERS = json.load(f)
        with open('server/services/canvas/fake_data/fake_courses.json', 'r') as f:
            FAKE_COURSES = json.load(f)
        with open('server/services/canvas/fake_data/fake_enrollments.json', 'r') as f:
            FAKE_ENROLLMENTS = json.load(f)

    def get_user(self, canvas_id) -> FakeUser:
        return FakeUser(canvas_id)

    def get_course(self, canvas_id) -> FakeCourse:
        return FakeCourse(canvas_id)


class FakeUser:
    def __init__(self, canvas_id):
        self.id = canvas_id
        self.name = FAKE_USERS[str(canvas_id)]['name']
        self.short_name = FAKE_USERS[str(canvas_id)]['short_name']
        self.email = FAKE_USERS[str(canvas_id)]['email']
        self.sis_user_id = FAKE_USERS[str(canvas_id)]['sis_user_id']
        self.login_id = FAKE_USERS[str(canvas_id)]['login_id']

    def get_courses(self, *, enrollment_status="active") -> list[FakeCourse]:
        dic = FAKE_ENROLLMENTS[str(self.id)]
        return [FakeCourse(course_id, course["enrollments"]) for course_id, course in dic.items() if (
            not enrollment_status or any(
                [e["enrollment_state"] == enrollment_status for e in course["enrollments"]])
        )]


class FakeCourse:
    def __init__(self, canvas_id, enrollments=[]):
        self.id = canvas_id
        self.name = FAKE_COURSES[str(canvas_id)]['name']
        self.course_code = FAKE_COURSES[str(canvas_id)]['course_code']
        self.sis_course_id = FAKE_COURSES[str(canvas_id)]['sis_course_id']
        self.enrollments = enrollments

    def get_users(self, *, enrollment_type) -> list[FakeUser]:
        users = []
        for user, dic in FAKE_ENROLLMENTS.items():
            if str(self.id) in dic:
                for enrollment in dic[str(self.id)]["enrollments"]:
                    if enrollment["type"] == enrollment_type:
                        users.append(FakeUser(user))
                        break
        return users
