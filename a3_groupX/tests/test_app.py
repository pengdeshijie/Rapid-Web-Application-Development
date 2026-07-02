import unittest
from datetime import date, time, timedelta
from decimal import Decimal

from ridequest import create_app, db
from ridequest.models import Booking, Category, Comment, Event, User


class RideQuestTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "WTF_CSRF_ENABLED": False,
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "SECRET_KEY": "test-secret",
            }
        )
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            owner = User(
                first_name="Carl",
                surname="Pan",
                email="owner@example.com",
                contact_number="0400000000",
                street_address="1 Test Street",
            )
            owner.set_password("Password123!")
            rider = User(
                first_name="Maya",
                surname="Lee",
                email="rider@example.com",
                contact_number="0400000001",
                street_address="2 Test Street",
            )
            rider.set_password("Password123!")
            category = Category(name="Gran Fondo")
            event = Event(
                name="Test Gran Fondo",
                description=(
                    "A complete test event description with enough detail "
                    "for riders."
                ),
                image_filename="img/gran-fondo.svg",
                event_date=date.today() + timedelta(days=30),
                start_time=time(7, 0),
                end_time=time(12, 0),
                price=Decimal("20.00"),
                capacity=2,
                meeting_location="Brisbane",
                route_start="Start",
                route_finish="Finish",
                distance_km=Decimal("80.0"),
                elevation_gain_m=900,
                difficulty="Moderate",
                terrain="Sealed road",
                route_image_filename="img/route-map.svg",
                route_description=(
                    "A sufficiently detailed route description for testing."
                ),
                equipment_requirements=(
                    "Helmet, lights, water, spare tubes and repair tools."
                ),
                owner=owner,
                category=category,
            )
            db.session.add_all([owner, rider, category, event])
            db.session.commit()
            self.owner_id = owner.id
            self.rider_id = rider.id
            self.event_id = event.id
            self.category_id = category.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, email, password="Password123!"):
        return self.client.post(
            "/auth/login",
            data={"email": email, "password": password},
            follow_redirects=False,
        )

    def logout(self):
        return self.client.post("/auth/logout", follow_redirects=False)

    def test_public_pages_and_404(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(
            self.client.get(f"/events/{self.event_id}").status_code, 200
        )
        self.assertEqual(self.client.get("/missing-page").status_code, 404)

    def test_500_error_uses_friendly_page(self):
        self.app.config["PROPAGATE_EXCEPTIONS"] = False

        @self.app.get("/force-test-error")
        def force_test_error():
            raise RuntimeError("forced test error")

        response = self.client.get("/force-test-error")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"unexpected climb", response.data)
        self.assertNotIn(b"RuntimeError", response.data)

    def test_registration_uses_first_name_and_surname(self):
        response = self.client.post(
            "/auth/register",
            data={
                "first_name": "Sam",
                "surname": "Chen",
                "email": "sam@example.com",
                "contact_number": "0400000002",
                "street_address": "3 Test Street",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            user = db.session.scalar(
                db.select(User).where(User.email == "sam@example.com")
            )
            self.assertEqual(user.first_name, "Sam")
            self.assertEqual(user.surname, "Chen")
            self.assertTrue(user.check_password("Password123!"))

    def test_protected_route_redirects_to_login(self):
        response = self.client.get("/events/create")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.location)

    def test_only_owner_can_edit_or_cancel(self):
        self.login("rider@example.com")
        forbidden = self.client.get(f"/events/{self.event_id}/edit")
        self.assertEqual(forbidden.status_code, 403)
        cancel_forbidden = self.client.post(
            f"/events/{self.event_id}/cancel"
        )
        self.assertEqual(cancel_forbidden.status_code, 403)

        self.logout()
        self.login("owner@example.com")
        cancelled = self.client.post(
            f"/events/{self.event_id}/cancel",
            follow_redirects=False,
        )
        self.assertEqual(cancelled.status_code, 302)
        with self.app.app_context():
            event = db.session.get(Event, self.event_id)
            self.assertTrue(event.is_cancelled)
            self.assertEqual(event.status, "Cancelled")

    def test_booking_updates_capacity_and_history(self):
        self.login("rider@example.com")
        response = self.client.post(
            f"/events/{self.event_id}/book",
            data={
                "quantity": 2,
                "participation_group": "Amateur",
                "bicycle_type": "Road bike",
                "equipment_confirmed": "y",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/bookings", response.location)

        with self.app.app_context():
            event = db.session.get(Event, self.event_id)
            self.assertEqual(event.remaining_capacity, 0)
            self.assertEqual(event.status, "Sold Out")
            self.assertEqual(
                db.session.scalar(db.select(db.func.count(Booking.id))), 1
            )

        history = self.client.get("/bookings")
        self.assertEqual(history.status_code, 200)
        self.assertIn(b"Test Gran Fondo", history.data)

    def test_invalid_booking_does_not_exceed_capacity(self):
        self.login("rider@example.com")
        response = self.client.post(
            f"/events/{self.event_id}/book",
            data={
                "quantity": 3,
                "participation_group": "Amateur",
                "bicycle_type": "Road bike",
                "equipment_confirmed": "y",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"cannot be placed", response.data)
        with self.app.app_context():
            self.assertEqual(
                db.session.scalar(db.select(db.func.count(Booking.id))), 0
            )

    def test_logged_in_user_can_comment(self):
        self.login("rider@example.com")
        response = self.client.post(
            f"/events/{self.event_id}/comments",
            data={"content": "Is there parking at the meeting point?"},
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            comment = db.session.scalar(db.select(Comment))
            self.assertEqual(comment.author_id, self.rider_id)
            self.assertEqual(comment.event_id, self.event_id)

    def test_search_filters_results(self):
        response = self.client.get("/?q=Test+Gran")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Gran Fondo", response.data)

        response = self.client.get("/?q=NoSuchRide")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No routes match", response.data)

    def test_owner_can_create_event_with_supply_point(self):
        self.login("owner@example.com")
        response = self.client.post(
            "/events/create",
            data={
                "name": "New Test Ride",
                "category_id": str(self.category_id),
                "description": (
                    "A detailed new cycling event description that clearly "
                    "explains the experience."
                ),
                "event_date": (
                    date.today() + timedelta(days=45)
                ).isoformat(),
                "start_time": "08:00",
                "end_time": "12:00",
                "price": "15.00",
                "capacity": "40",
                "meeting_location": "New Farm Park",
                "route_start": "New Farm",
                "route_finish": "New Farm",
                "distance_km": "55.0",
                "elevation_gain_m": "450",
                "difficulty": "Moderate",
                "terrain": "Sealed road",
                "route_description": (
                    "A signed river loop with rolling roads and clear turns."
                ),
                "equipment_requirements": (
                    "Helmet, lights, two tubes, water and repair tools."
                ),
                "supply_points-0-name": "River refill",
                "supply_points-0-location_description": "Kangaroo Point",
                "supply_points-0-distance_from_start_km": "28.0",
                "supply_points-0-services": "Water and fruit",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            event = db.session.scalar(
                db.select(Event).where(Event.name == "New Test Ride")
            )
            self.assertIsNotNone(event)
            self.assertEqual(event.owner_id, self.owner_id)
            self.assertEqual(len(event.supply_points), 1)

    def test_owner_can_update_event_details(self):
        self.login("owner@example.com")
        response = self.client.post(
            f"/events/{self.event_id}/edit",
            data={
                "name": "Updated Test Gran Fondo",
                "category_id": str(self.category_id),
                "description": (
                    "An updated cycling event description with enough detail "
                    "for every rider."
                ),
                "event_date": (
                    date.today() + timedelta(days=35)
                ).isoformat(),
                "start_time": "07:30",
                "end_time": "12:30",
                "price": "25.00",
                "capacity": "50",
                "meeting_location": "Updated Brisbane location",
                "route_start": "Updated start",
                "route_finish": "Updated finish",
                "distance_km": "88.0",
                "elevation_gain_m": "980",
                "difficulty": "Challenging",
                "terrain": "Sealed road",
                "route_description": (
                    "An updated signed loop with clear route information."
                ),
                "equipment_requirements": (
                    "Helmet, lights, water, spare tubes and repair tools."
                ),
                "supply_points-0-name": "Updated refill",
                "supply_points-0-location_description": "Halfway park",
                "supply_points-0-distance_from_start_km": "44.0",
                "supply_points-0-services": "Water and nutrition",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            event = db.session.get(Event, self.event_id)
            self.assertEqual(event.name, "Updated Test Gran Fondo")
            self.assertEqual(event.capacity, 50)
            self.assertEqual(len(event.supply_points), 1)


if __name__ == "__main__":
    unittest.main()
