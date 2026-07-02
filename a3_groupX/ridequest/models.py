"""Database models for the RideQuest event management application."""

from datetime import date, datetime, timezone
from decimal import Decimal

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db


def utc_now():
    """Return a timezone-aware UTC timestamp for model defaults."""
    return datetime.now(timezone.utc)


class User(db.Model, UserMixin):
    """A registered RideQuest user."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    surname = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    contact_number = db.Column(db.String(30), nullable=False)
    street_address = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now
    )

    events = db.relationship(
        "Event",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="select",
    )
    bookings = db.relationship(
        "Booking",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    comments = db.relationship(
        "Comment",
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="select",
    )

    @property
    def full_name(self):
        """Return the user's display name without storing duplicate data."""
        return f"{self.first_name} {self.surname}"

    def set_password(self, password):
        """Hash and store a new password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Return True when a supplied password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.id}: {self.email}>"


class Category(db.Model):
    """A category used to group similar cycling events."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    events = db.relationship(
        "Event",
        back_populates="category",
        lazy="select",
    )

    def __repr__(self):
        return f"<Category {self.id}: {self.name}>"


class Event(db.Model):
    """A cycling event created and managed by a registered user."""

    __tablename__ = "events"
    __table_args__ = (
        db.CheckConstraint("price >= 0", name="ck_event_price_non_negative"),
        db.CheckConstraint("capacity > 0", name="ck_event_capacity_positive"),
        db.CheckConstraint(
            "distance_km > 0", name="ck_event_distance_positive"
        ),
        db.CheckConstraint(
            "elevation_gain_m >= 0",
            name="ck_event_elevation_non_negative",
        ),
        db.Index("ix_event_date_category", "event_date", "category_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255), nullable=False)

    event_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    capacity = db.Column(db.Integer, nullable=False)
    meeting_location = db.Column(db.String(255), nullable=False)

    route_start = db.Column(db.String(255), nullable=False)
    route_finish = db.Column(db.String(255), nullable=False)
    distance_km = db.Column(db.Numeric(7, 2), nullable=False)
    elevation_gain_m = db.Column(db.Integer, nullable=False, default=0)
    difficulty = db.Column(db.String(30), nullable=False)
    terrain = db.Column(db.String(80), nullable=False)
    route_image_filename = db.Column(db.String(255), nullable=True)
    route_description = db.Column(db.Text, nullable=False)
    equipment_requirements = db.Column(db.Text, nullable=False)

    # The creator's cancel button persists this value. Other status values are
    # derived by the application from the date and remaining capacity.
    is_cancelled = db.Column(db.Boolean, nullable=False, default=False)
    cancelled_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id"),
        nullable=False,
        index=True,
    )

    owner = db.relationship("User", back_populates="events")
    category = db.relationship("Category", back_populates="events")
    supply_points = db.relationship(
        "SupplyPoint",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="SupplyPoint.distance_from_start_km",
        lazy="select",
    )
    bookings = db.relationship(
        "Booking",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="select",
    )
    comments = db.relationship(
        "Comment",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
        lazy="select",
    )

    @property
    def booked_quantity(self):
        """Return places held by confirmed bookings."""
        return sum(
            booking.quantity
            for booking in self.bookings
            if booking.status == Booking.CONFIRMED
        )

    @property
    def remaining_capacity(self):
        """Return the number of places still available."""
        return max(self.capacity - self.booked_quantity, 0)

    @property
    def status(self):
        """Return the current application-managed event status."""
        if self.is_cancelled:
            return "Cancelled"
        if self.event_date < date.today():
            return "Inactive"
        if self.remaining_capacity == 0:
            return "Sold Out"
        return "Open"

    def can_book(self, quantity=1):
        """Return True when a requested number of places can be booked."""
        return (
            isinstance(quantity, int)
            and quantity > 0
            and self.status == "Open"
            and quantity <= self.remaining_capacity
        )

    def cancel_by(self, user):
        """Cancel the event when the supplied user is its creator.

        The cancel route should call this method after the creator clicks a
        POST-only, CSRF-protected Cancel Event button.
        """
        if user is None or user.id != self.owner_id:
            raise PermissionError("Only the event creator can cancel this event.")
        if self.event_date < date.today():
            raise ValueError("A past event cannot be cancelled.")
        if self.is_cancelled:
            raise ValueError("This event has already been cancelled.")

        self.is_cancelled = True
        self.cancelled_at = utc_now()

    def __repr__(self):
        return f"<Event {self.id}: {self.name}>"


class SupplyPoint(db.Model):
    """A support location along an event route."""

    __tablename__ = "supply_points"
    __table_args__ = (
        db.CheckConstraint(
            "distance_from_start_km >= 0",
            name="ck_supply_distance_non_negative",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location_description = db.Column(db.String(255), nullable=False)
    distance_from_start_km = db.Column(db.Numeric(7, 2), nullable=False)
    services = db.Column(db.Text, nullable=False)

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False,
        index=True,
    )
    event = db.relationship("Event", back_populates="supply_points")

    def __repr__(self):
        return f"<SupplyPoint {self.id}: {self.name}>"


class Booking(db.Model):
    """A user's confirmed order for places at an event."""

    __tablename__ = "bookings"
    __table_args__ = (
        db.CheckConstraint(
            "quantity > 0", name="ck_booking_quantity_positive"
        ),
        db.CheckConstraint(
            "unit_price >= 0", name="ck_booking_price_non_negative"
        ),
    )

    CONFIRMED = "Confirmed"
    CANCELLED = "Cancelled"

    id = db.Column(db.Integer, primary_key=True)
    booking_reference = db.Column(
        db.String(40), nullable=False, unique=True, index=True
    )
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    participation_group = db.Column(db.String(40), nullable=False)
    bicycle_type = db.Column(db.String(80), nullable=False)
    equipment_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(
        db.String(20), nullable=False, default=CONFIRMED
    )
    booked_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False,
        index=True,
    )

    user = db.relationship("User", back_populates="bookings")
    event = db.relationship("Event", back_populates="bookings")

    @property
    def total_price(self):
        """Return the price captured when the booking was created."""
        return self.unit_price * self.quantity

    def __repr__(self):
        return f"<Booking {self.booking_reference}>"


class Comment(db.Model):
    """A comment posted by a registered user on an event."""

    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now
    )

    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False,
        index=True,
    )

    author = db.relationship("User", back_populates="comments")
    event = db.relationship("Event", back_populates="comments")

    def __repr__(self):
        return f"<Comment {self.id} on Event {self.event_id}>"
