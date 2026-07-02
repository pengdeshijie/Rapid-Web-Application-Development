"""Event creation, editing, cancellation, booking and commenting routes."""

import secrets
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from . import db
from .forms import (
    BookingForm,
    CancelEventForm,
    CommentForm,
    EventForm,
)
from .models import Booking, Category, Comment, Event, SupplyPoint


events_bp = Blueprint("events", __name__, url_prefix="/events")


def configure_category_choices(form):
    categories = list(
        db.session.scalars(db.select(Category).order_by(Category.name))
    )
    form.category_id.choices = [
        (category.id, category.name) for category in categories
    ]


def save_image(file_storage):
    """Save an uploaded image and return its static-relative filename."""
    if not file_storage or not file_storage.filename:
        return None
    original_name = secure_filename(file_storage.filename)
    extension = Path(original_name).suffix.lower().lstrip(".")
    if extension not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        raise ValueError("Unsupported image type.")
    unique_name = f"{secrets.token_hex(8)}_{original_name}"
    destination = Path(current_app.config["UPLOAD_FOLDER"]) / unique_name
    file_storage.save(destination)
    return f"uploads/{unique_name}"


def apply_event_form(event, form):
    event.name = form.name.data.strip()
    event.category_id = form.category_id.data
    event.description = form.description.data.strip()
    event.event_date = form.event_date.data
    event.start_time = form.start_time.data
    event.end_time = form.end_time.data
    event.price = form.price.data
    event.capacity = form.capacity.data
    event.meeting_location = form.meeting_location.data.strip()
    event.route_start = form.route_start.data.strip()
    event.route_finish = form.route_finish.data.strip()
    event.distance_km = form.distance_km.data
    event.elevation_gain_m = form.elevation_gain_m.data
    event.difficulty = form.difficulty.data
    event.terrain = form.terrain.data
    event.route_description = form.route_description.data.strip()
    event.equipment_requirements = form.equipment_requirements.data.strip()

    event_image = save_image(form.event_image.data)
    if event_image:
        event.image_filename = event_image
    route_image = save_image(form.route_image.data)
    if route_image:
        event.route_image_filename = route_image

    event.supply_points.clear()
    for entry in form.supply_points.entries:
        if entry.form.name.data:
            event.supply_points.append(
                SupplyPoint(
                    name=entry.form.name.data.strip(),
                    location_description=(
                        entry.form.location_description.data.strip()
                    ),
                    distance_from_start_km=(
                        entry.form.distance_from_start_km.data
                    ),
                    services=entry.form.services.data.strip(),
                )
            )


def populate_supply_point_form(form, event):
    while len(form.supply_points.entries) < max(len(event.supply_points), 3):
        form.supply_points.append_entry()
    for form_entry, supply_point in zip(
        form.supply_points.entries, event.supply_points
    ):
        form_entry.form.name.data = supply_point.name
        form_entry.form.location_description.data = (
            supply_point.location_description
        )
        form_entry.form.distance_from_start_km.data = (
            supply_point.distance_from_start_km
        )
        form_entry.form.services.data = supply_point.services


def create_booking_reference():
    while True:
        reference = f"RQ-{secrets.token_hex(5).upper()}"
        existing = db.session.scalar(
            db.select(Booking.id).where(
                Booking.booking_reference == reference
            )
        )
        if existing is None:
            return reference


@events_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_event():
    form = EventForm()
    configure_category_choices(form)

    if form.validate_on_submit():
        event = Event(owner=current_user, image_filename="img/gran-fondo.svg")
        try:
            apply_event_form(event, form)
            db.session.add(event)
            db.session.commit()
        except (OSError, ValueError) as error:
            db.session.rollback()
            flash(f"The event could not be saved: {error}", "danger")
        else:
            flash("Your cycling event has been created.", "success")
            return redirect(
                url_for("main.event_detail", event_id=event.id)
            )

    return render_template(
        "event_form.html",
        form=form,
        heading="Create a cycling event",
        introduction=(
            "Give riders the route, safety and support details they need."
        ),
        event=None,
    )


@events_bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    event = db.get_or_404(Event, event_id)
    if event.owner_id != current_user.id:
        abort(403)
    if event.is_cancelled:
        flash("A cancelled event can no longer be edited.", "warning")
        return redirect(url_for("main.event_detail", event_id=event.id))

    form = EventForm(obj=event)
    configure_category_choices(form)

    if form.validate_on_submit():
        try:
            apply_event_form(event, form)
            db.session.commit()
        except (OSError, ValueError) as error:
            db.session.rollback()
            flash(f"The event could not be updated: {error}", "danger")
        else:
            flash("Event details have been updated.", "success")
            return redirect(
                url_for("main.event_detail", event_id=event.id)
            )
    elif not form.is_submitted():
        form.category_id.data = event.category_id
        populate_supply_point_form(form, event)

    return render_template(
        "event_form.html",
        form=form,
        heading="Update cycling event",
        introduction="Keep riders informed with accurate event details.",
        event=event,
    )


@events_bp.post("/<int:event_id>/cancel")
@login_required
def cancel_event(event_id):
    event = db.get_or_404(Event, event_id)
    form = CancelEventForm()
    if not form.validate_on_submit():
        abort(400)
    try:
        event.cancel_by(current_user)
        db.session.commit()
    except PermissionError:
        db.session.rollback()
        abort(403)
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "warning")
    else:
        flash("The event has been cancelled.", "success")
    return redirect(url_for("main.event_detail", event_id=event.id))


@events_bp.post("/<int:event_id>/book")
@login_required
def book_event(event_id):
    event = db.get_or_404(Event, event_id)
    form = BookingForm()
    if form.validate_on_submit():
        quantity = form.quantity.data
        if not event.can_book(quantity):
            flash(
                "This booking cannot be placed. Check the event status and "
                "remaining capacity.",
                "danger",
            )
        else:
            booking = Booking(
                booking_reference=create_booking_reference(),
                quantity=quantity,
                unit_price=event.price,
                participation_group=form.participation_group.data,
                bicycle_type=form.bicycle_type.data,
                equipment_confirmed=form.equipment_confirmed.data,
                user=current_user,
                event=event,
            )
            db.session.add(booking)
            db.session.commit()
            flash(
                f"Booking confirmed. Your reference is "
                f"{booking.booking_reference}.",
                "success",
            )
            return redirect(url_for("main.booking_history"))
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "danger")

    return redirect(url_for("main.event_detail", event_id=event.id))


@events_bp.post("/<int:event_id>/comments")
@login_required
def post_comment(event_id):
    event = db.get_or_404(Event, event_id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(
            content=form.content.data.strip(),
            author=current_user,
            event=event,
        )
        db.session.add(comment)
        db.session.commit()
        flash("Your comment has been posted.", "success")
    else:
        flash("Enter a comment between 2 and 500 characters.", "danger")
    return redirect(
        url_for("main.event_detail", event_id=event.id, _anchor="comments")
    )
