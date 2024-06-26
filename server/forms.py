import re

from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, SelectField, ValidationError, BooleanField, FileField, SelectMultipleField, StringField, \
    SubmitField, TextAreaField, DateTimeField, IntegerField, widgets
from wtforms import Form as NoCsrfForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms.validators import Email, InputRequired, URL, Optional, DataRequired
from server.controllers import exam_regex
from server.typings.enum import AssignmentImportStrategy, NewRowImportStrategy, UpdatedRowImportStrategy, MissingRowImportStrategy


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class ChooseCourseOfferingForm(FlaskForm):
    submit = SubmitField('import')
    offerings = MultiCheckboxField('select_offerings')

    def __init__(self, offering_list=None, *args, **kwargs):
        super(ChooseCourseOfferingForm, self).__init__(*args, **kwargs)
        if offering_list is not None:
            self.offerings.choices = [(o.canvas_id, str(o)) for o in offering_list]  # (value, label)


class ExamFormBase(FlaskForm):
    display_name = StringField('display_name', [InputRequired()], render_kw={
                               "placeholder": "Midterm 1"})
    active = BooleanField('active', default=True)

    cancel = SubmitField('cancel')


class ExamForm(ExamFormBase):
    name = StringField('name', [InputRequired()], render_kw={"placeholder": "midterm1"})
    submit = SubmitField('create')

    def validate_name(form, field):
        pattern = '^{}$'.format(exam_regex)
        if not re.match(pattern, field.data):
            raise ValidationError('Exam name must be match pattern {}'.format(pattern))


class EditExamForm(ExamFormBase):
    submit = SubmitField('make edits')


class RoomFormBase(FlaskForm):
    start_at = DateTimeField('start_at', [Optional()], format='%Y-%m-%dT%H:%M')
    duration_minutes = IntegerField('duration_minutes', [Optional()])


class RoomForm(RoomFormBase):
    display_name = StringField('display_name', [InputRequired()])
    sheet_url = StringField('sheet_url', [URL(), InputRequired()])
    sheet_range = StringField('sheet_range', [InputRequired()])
    preview_room = SubmitField('preview')
    create_room = SubmitField('create')


class ChooseRoomForm(RoomFormBase):
    submit = SubmitField('import')
    rooms = MultiCheckboxField('select_rooms')

    def __init__(self, room_list=None, *args, **kwargs):
        super(ChooseRoomForm, self).__init__(*args, **kwargs)
        if room_list is not None:
            self.rooms.choices = [(item, item) for item in room_list]  # (value, label)


class UploadRoomForm(RoomFormBase):
    submit = SubmitField('upload')
    file = FileField('Choose File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    display_name = StringField('display_name', [InputRequired()])


class MovableSeatSubForm(NoCsrfForm):
    attributes = StringField('attributes', default='', render_kw={"placeholder": "Righty, Aisle"})
    count = IntegerField('count', [InputRequired()], default=1, render_kw={"placeholder": "1"})


class EditRoomForm(RoomFormBase):
    display_name = StringField('display_name', [InputRequired()])
    movable_seats = FieldList(FormField(MovableSeatSubForm), min_entries=0)
    submit = SubmitField('make edits')
    cancel = SubmitField('cancel')


class ImportStudentFormBase(FlaskForm):
    revalidate_existing_assignments = BooleanField('revalidate_existing_assignments', default=True)
    assignment_import_strategy = SelectField('assignment_import_strategy', choices=[
        (e.value, e.name) for e in AssignmentImportStrategy],
        default=AssignmentImportStrategy.REVALIDATE.value,
        validators=[DataRequired()])
    updated_student_info_import_strategy = SelectField('updated_student_info_import_strategy', choices=[
        (e.value, e.name) for e in UpdatedRowImportStrategy],
        default=UpdatedRowImportStrategy.MERGE.value,
        validators=[DataRequired()])
    updated_preference_import_strategy = SelectField('updated_preference_import_strategy', choices=[
        (e.value, e.name) for e in UpdatedRowImportStrategy],
        default=UpdatedRowImportStrategy.OVERWRITE.value,
        validators=[DataRequired()])
    new_student_import_strategy = SelectField('new_student_import_strategy', choices=[
        (e.value, e.name) for e in NewRowImportStrategy],
        default=NewRowImportStrategy.APPEND.value,
        validators=[DataRequired()])
    missing_student_import_strategy = SelectField('missing_student_import_strategy', choices=[
        (e.value, e.name) for e in MissingRowImportStrategy],
        default=MissingRowImportStrategy.IGNORE.value,
        validators=[DataRequired()])
    submit = SubmitField('import')


class ImportStudentFromSheetForm(ImportStudentFormBase):
    sheet_url = StringField('sheet_url', [URL()])
    sheet_range = StringField('sheet_range', [InputRequired()])


class ImportStudentFromCanvasRosterForm(ImportStudentFormBase):
    pass


class ImportStudentFromCsvUploadForm(ImportStudentFormBase):
    file = FileField('Choose File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])


class ImportStudentFromManualInputForm(ImportStudentFormBase):
    text = TextAreaField('text', [InputRequired()], render_kw={
                         "placeholder": "canvas id,email,name\n123456,x@y.z,John\n..."})


class EditStudentsFormBase(FlaskForm):
    wants = StringField('wants')
    avoids = StringField('avoids')
    room_wants = MultiCheckboxField('room_wants')
    room_avoids = MultiCheckboxField('room_avoids')
    submit = SubmitField('make edits')
    cancel = SubmitField('cancel')

    def __init__(self, room_list=None, *args, **kwargs):
        super(EditStudentsFormBase, self).__init__(*args, **kwargs)
        if room_list is not None:
            self.room_wants.choices = [(str(item.id), item.name_and_start_at_time_display()) for item in room_list]
            self.room_avoids.choices = [(str(item.id), item.name_and_start_at_time_display()) for item in room_list]


class EditStudentForm(EditStudentsFormBase):
    new_email = StringField('email', [Email()])

    def __init__(self, room_list=None, *args, **kwargs):
        super(EditStudentForm, self).__init__(room_list=room_list, *args, **kwargs)


class EditStudentsForm(EditStudentsFormBase):
    emails = TextAreaField('emails')
    use_all_emails = BooleanField('use_all_emails')

    def __init__(self, room_list=None, *args, **kwargs):
        super(EditStudentsForm, self).__init__(room_list=room_list, *args, **kwargs)


class DeleteStudentForm(FlaskForm):
    emails = TextAreaField('emails')
    use_all_emails = BooleanField('use_all_emails')
    submit = SubmitField('delete by emails')


class AssignForm(FlaskForm):
    submit = SubmitField('assign')
    delete_all = SubmitField('delete all assignments')
    reassign_all = SubmitField('reassign all assignments')


class AssignSingleForm(FlaskForm):
    ignore_restrictions = BooleanField('ignore restrictions')
    seat_id = StringField('seat_id')
    just_delete = SubmitField('just delete')
    submit = SubmitField('assign')


class EmailForm(FlaskForm):
    from_addr = StringField('from_addr', [Email(), InputRequired()])
    to_addr = StringField('to_addr', [InputRequired()])
    cc_addr = StringField('cc_addr', [])
    bcc_addr = StringField('bcc_addr', [])
    subject = StringField('subject', [InputRequired()])
    body = TextAreaField('body', [InputRequired()])
    body_html = BooleanField('body_html', default=True)
    submit = SubmitField('send')


class DevLoginForm(FlaskForm):
    user_id = StringField('user_id', [InputRequired()], render_kw={"placeholder": "123456"})
    submit = SubmitField('login')
