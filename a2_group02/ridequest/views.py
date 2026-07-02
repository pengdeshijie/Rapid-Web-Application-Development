"""Public discovery, event details and booking-history routes."""

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from . import db
from .forms import BookingForm, CancelEventForm, CommentForm
from .models import Booking, Category, Event


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    query_text = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    difficulty = request.args.get("difficulty", "").strip()
    requested_status = request.args.get("status", "").strip()

    statement = db.select(Event).join(Event.category)
    if query_text:
        search_term = f"%{query_text}%"
        statement = statement.where(
            or_(
                Event.name.ilike(search_term),
                Event.description.ilike(search_term),
                Event.meeting_location.ilike(search_term),
                Category.name.ilike(search_term),
            )
        )
    if category_id:
        statement = statement.where(Event.category_id == category_id)
    if difficulty:
        statement = statement.where(Event.difficulty == difficulty)

    events = list(
        db.session.scalars(statement.order_by(Event.event_date, Event.name))
    )
    if requested_status:
        events = [event for event in events if event.status == requested_status]

    all_events = list(db.session.scalars(db.select(Event)))
    categories = list(
        db.session.scalars(db.select(Category).order_by(Category.name))
    )
    rider_count = db.session.scalar(
        db.select(db.func.coalesce(db.func.sum(Booking.quantity), 0)).where(
            Booking.status == Booking.CONFIRMED
        )
    )

    return render_template(
        "index.html",
        events=events,
        categories=categories,
        query_text=query_text,
        selected_category=category_id,
        selected_difficulty=difficulty,
        selected_status=requested_status,
        total_events=len(all_events),
        open_events=sum(event.status == "Open" for event in all_events),
        rider_count=rider_count,
    )


@main_bp.get("/events/<int:event_id>")
def event_detail(event_id):
    event = db.get_or_404(Event, event_id)
    return render_template(
        "event.html",
        event=event,
        booking_form=BookingForm(),
        comment_form=CommentForm(),
        cancel_form=CancelEventForm(),
    )


@main_bp.get("/bookings")
@login_required
def booking_history():
    bookings = list(
        db.session.scalars(
            db.select(Booking)
            .where(Booking.user_id == current_user.id)
            .order_by(Booking.booked_at.desc())
        )
    )
    return render_template("history.html", bookings=bookings)
