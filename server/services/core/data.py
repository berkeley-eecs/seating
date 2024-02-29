from server.services.canvas import get_student_roster_for_offering
from server.services.csv import parse_csv
from server.services.google import get_spreadsheet_tab_content

from server.services.core.room import prepare_room, prepare_seat
from server.services.core.student import prepare_students


def get_room_from_google_spreadsheet(exam, room_form):
    room = prepare_room(exam, room_form)
    headers, rows = get_spreadsheet_tab_content(room_form.sheet_url.data,
                                                room_form.sheet_range.data)
    seats = prepare_seat(headers, rows)
    room.seats = seats
    return room


def get_room_from_csv(exam, room_form):
    room = prepare_room(exam, room_form)
    headers, rows = parse_csv(room_form.file.data)
    seats = prepare_seat(headers, rows)
    room.seats = seats
    return room


def get_room_from_manual_input(exam, room_form, manual_input_dict):
    room = prepare_room(exam, room_form)
    headers, rows = _get_seats_from_manual_input(manual_input_dict)
    seats = prepare_seat(headers, rows)
    room.seats = seats
    return room


def update_room_from_manual_input(room, manual_input_dict):
    headers, rows = _get_seats_from_manual_input(manual_input_dict)
    seats = prepare_seat(headers, rows)
    room.update_movable_seats(seats)  # manual input only handles movable seats


def _get_seats_from_manual_input(manual_input_dict):
    headers = set(['row', 'seat', 'x', 'y'])
    for attr_set in manual_input_dict:
        headers.union(attr_set)
    headers = list(headers)
    rows = []
    for attr_set, count in manual_input_dict.items():
        row_dic = {
            k.lower(): 'true' for k in attr_set
        }
        row_dic['count'] = count
        rows.append(row_dic)
    return headers, rows


def get_students_from_google_spreadsheet(exam, student_form):
    headers, rows = get_spreadsheet_tab_content(student_form.sheet_url.data,
                                                student_form.sheet_range.data)
    return prepare_students(exam, headers, rows)


def get_students_from_csv(exam, student_form):
    headers, rows = parse_csv(student_form.file.data)
    return prepare_students(exam, headers, rows)


def get_students_from_canvas(exam):
    headers, rows = get_student_roster_for_offering(exam.offering_canvas_id)
    return prepare_students(exam, headers, rows)
