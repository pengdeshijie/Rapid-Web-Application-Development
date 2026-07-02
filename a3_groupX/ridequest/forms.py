"""WTForms definitions for RideQuest."""

from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    FieldList,
    FormField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
    TimeField,
)
from wtforms.form import Form
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)


IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "svg"]


class EmptyForm(FlaskForm):
    """A CSRF-protected form for POST-only actions."""

    submit = SubmitField("Submit")


class LoginForm(FlaskForm):
    email = StringField(
        "Email address",
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me signed in")
    submit = SubmitField("Sign in")


class RegisterForm(FlaskForm):
    first_name = StringField(
        "First name", validators=[DataRequired(), Length(min=2, max=80)]
    )
    surname = StringField(
        "Surname", validators=[DataRequired(), Length(min=2, max=80)]
    )
    email = StringField(
        "Email address",
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    contact_number = StringField(
        "Contact number",
        validators=[DataRequired(), Length(min=8, max=30)],
    )
    street_address = StringField(
        "Street address",
        validators=[DataRequired(), Length(min=5, max=255)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, max=128)],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Create account")


class SupplyPointEntryForm(Form):
    name = StringField("Name", validators=[Optional(), Length(max=120)])
    location_description = StringField(
        "Location", validators=[Optional(), Length(max=255)]
    )
    distance_from_start_km = DecimalField(
        "Distance from start (km)",
        validators=[Optional(), NumberRange(min=0, max=1000)],
        places=1,
    )
    services = StringField(
        "Services", validators=[Optional(), Length(max=500)]
    )


class EventForm(FlaskForm):
    name = StringField(
        "Event name", validators=[DataRequired(), Length(min=4, max=120)]
    )
    category_id = SelectField(
        "Category", coerce=int, validators=[DataRequired()]
    )
    description = TextAreaField(
        "Event description",
        validators=[DataRequired(), Length(min=30, max=3000)],
    )
    event_image = FileField(
        "Event image",
        validators=[Optional(), FileAllowed(IMAGE_EXTENSIONS, "Images only.")],
    )
    event_date = DateField(
        "Event date", validators=[DataRequired()], format="%Y-%m-%d"
    )
    start_time = TimeField("Start time", validators=[DataRequired()])
    end_time = TimeField("End time", validators=[DataRequired()])
    price = DecimalField(
        "Entry price (AUD)",
        validators=[InputRequired(), NumberRange(min=0, max=100000)],
        places=2,
    )
    capacity = IntegerField(
        "Rider capacity",
        validators=[DataRequired(), NumberRange(min=1, max=2000)],
    )
    meeting_location = StringField(
        "Meeting location",
        validators=[DataRequired(), Length(min=4, max=255)],
    )
    route_start = StringField(
        "Route start", validators=[DataRequired(), Length(min=3, max=255)]
    )
    route_finish = StringField(
        "Route finish", validators=[DataRequired(), Length(min=3, max=255)]
    )
    distance_km = DecimalField(
        "Distance (km)",
        validators=[DataRequired(), NumberRange(min=1, max=2000)],
        places=1,
    )
    elevation_gain_m = IntegerField(
        "Elevation gain (m)",
        validators=[InputRequired(), NumberRange(min=0, max=20000)],
    )
    difficulty = SelectField(
        "Difficulty",
        choices=[
            ("Leisure", "Leisure"),
            ("Moderate", "Moderate"),
            ("Challenging", "Challenging"),
            ("Advanced", "Advanced"),
        ],
        validators=[DataRequired()],
    )
    terrain = SelectField(
        "Primary terrain",
        choices=[
            ("Sealed road", "Sealed road"),
            ("Mixed sealed and gravel", "Mixed sealed and gravel"),
            ("Gravel road", "Gravel road"),
            ("Mountain trail", "Mountain trail"),
        ],
        validators=[DataRequired()],
    )
    route_image = FileField(
        "Route image or map",
        validators=[Optional(), FileAllowed(IMAGE_EXTENSIONS, "Images only.")],
    )
    route_description = TextAreaField(
        "Route notes",
        validators=[DataRequired(), Length(min=20, max=3000)],
    )
    equipment_requirements = TextAreaField(
        "Equipment requirements",
        validators=[DataRequired(), Length(min=20, max=2000)],
    )
    supply_points = FieldList(
        FormField(SupplyPointEntryForm), min_entries=3, max_entries=5
    )
    submit = SubmitField("Save event")

    def validate_event_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError("The event date cannot be in the past.")

    def validate_end_time(self, field):
        if self.start_time.data and field.data <= self.start_time.data:
            raise ValidationError("End time must be later than start time.")

    def validate_supply_points(self, field):
        completed = 0
        for entry in field.entries:
            values = (
                entry.form.name.data,
                entry.form.location_description.data,
                entry.form.distance_from_start_km.data,
                entry.form.services.data,
            )
            if any(value not in (None, "") for value in values):
                if not all(value not in (None, "") for value in values):
                    raise ValidationError(
                        "Complete every field for each supply point used."
                    )
                completed += 1
        if completed == 0:
            raise ValidationError("Add at least one complete supply point.")


class BookingForm(FlaskForm):
    quantity = IntegerField(
        "Number of places",
        validators=[DataRequired(), NumberRange(min=1, max=20)],
        default=1,
    )
    participation_group = SelectField(
        "Participation group",
        choices=[
            ("Elite", "Elite · 34+ km/h"),
            ("Amateur", "Amateur · 27–33 km/h"),
            ("Leisure", "Leisure · 21–26 km/h"),
        ],
        validators=[DataRequired()],
    )
    bicycle_type = SelectField(
        "Bicycle type",
        choices=[
            ("Road bike", "Road bike"),
            ("Endurance road bike", "Endurance road bike"),
            ("Gravel bike", "Gravel bike"),
            ("E-bike", "E-bike (Leisure only)"),
        ],
        validators=[DataRequired()],
    )
    equipment_confirmed = BooleanField(
        "I confirm that my bicycle and safety equipment meet the event requirements.",
        validators=[DataRequired()],
    )
    submit = SubmitField("Book this ride")

    def validate_bicycle_type(self, field):
        if field.data == "E-bike" and self.participation_group.data != "Leisure":
            raise ValidationError("E-bikes can only join the Leisure group.")


class CommentForm(FlaskForm):
    content = TextAreaField(
        "Your comment",
        validators=[DataRequired(), Length(min=2, max=500)],
    )
    submit = SubmitField("Post comment")


class CancelEventForm(FlaskForm):
    submit = SubmitField("Cancel event")
