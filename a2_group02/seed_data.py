"""Create the submitted RideQuest SQLite database with synthetic data."""

from datetime import date, time, timedelta
from decimal import Decimal

from ridequest import create_app, db
from ridequest.models import (
    Booking,
    Category,
    Comment,
    Event,
    SupplyPoint,
    User,
)


def make_user(first_name, surname, email):
    user = User(
        first_name=first_name,
        surname=surname,
        email=email,
        contact_number="0400 000 000",
        street_address="2 George Street, Brisbane QLD 4000",
    )
    user.set_password("RideQuest123!")
    return user


def make_event(
    owner,
    category,
    name,
    day_offset,
    image,
    price,
    capacity,
    location,
    distance,
    elevation,
    difficulty,
    terrain="Sealed road",
    cancelled=False,
):
    return Event(
        owner=owner,
        category=category,
        name=name,
        description=(
            f"{name} is a supported RideQuest cycling experience designed "
            "for riders who want clear route information, suitable pace "
            "groups and practical event-day support. The route combines "
            "memorable scenery with well-marked sections and responsible "
            "group riding."
        ),
        image_filename=f"img/{image}",
        event_date=date.today() + timedelta(days=day_offset),
        start_time=time(6, 0),
        end_time=time(14, 30),
        price=Decimal(price),
        capacity=capacity,
        meeting_location=location,
        route_start=location,
        route_finish=location,
        distance_km=Decimal(str(distance)),
        elevation_gain_m=elevation,
        difficulty=difficulty,
        terrain=terrain,
        route_image_filename="img/route-map.svg",
        route_description=(
            "A signed loop using quiet roads and clearly identified turns. "
            "Riders should expect rolling terrain, several sustained climbs "
            "and normal public-road conditions."
        ),
        equipment_requirements=(
            "Australian-standard helmet, working front and rear lights, "
            "two spare tubes, pump or inflator, basic repair tools and at "
            "least 1.5 litres of water are required."
        ),
        is_cancelled=cancelled,
    )


def add_points(event, distances):
    for index, distance in enumerate(distances, start=1):
        event.supply_points.append(
            SupplyPoint(
                name=f"Supply point {index}",
                location_description=f"Signed support area at {distance} km",
                distance_from_start_km=Decimal(str(distance)),
                services="Water, electrolyte drink, fruit and basic first aid",
            )
        )


def seed_database():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        carl = make_user("Carl", "Pan", "carl@example.com")
        maya = make_user("Maya", "Lee", "maya@example.com")
        sam = make_user("Sam", "Chen", "sam@example.com")

        gran_fondo = Category(
            name="Gran Fondo",
            description="Supported long-distance road cycling events.",
        )
        hill_climb = Category(
            name="Hill Climb",
            description="Climbing challenges focused on elevation.",
        )
        group_ride = Category(
            name="Weekend Group Ride",
            description="Social rides with structured pace groups.",
        )

        glass_house = make_event(
            carl,
            gran_fondo,
            "Glass House Gran Fondo",
            48,
            "gran-fondo.svg",
            "79.00",
            200,
            "Beerburrum Sports Ground",
            122,
            1760,
            "Challenging",
        )
        summit = make_event(
            maya,
            hill_climb,
            "Mt Coot-tha Summit Dash",
            26,
            "hill-climb.svg",
            "35.00",
            4,
            "Toowong, Brisbane",
            18,
            620,
            "Advanced",
        )
        river_loop = make_event(
            sam,
            group_ride,
            "Brisbane River Social Loop",
            39,
            "weekend-ride.svg",
            "0.00",
            60,
            "South Bank, Brisbane",
            42,
            260,
            "Leisure",
        )
        border_ranges = make_event(
            carl,
            gran_fondo,
            "Border Ranges Gravel Quest",
            33,
            "forest-gravel.svg",
            "65.00",
            100,
            "Rathdowney, Scenic Rim",
            86,
            1340,
            "Challenging",
            terrain="Mixed sealed and gravel",
            cancelled=True,
        )
        winter_classic = make_event(
            maya,
            gran_fondo,
            "Winter Hinterland Classic",
            -10,
            "gran-fondo.svg",
            "70.00",
            160,
            "Nerang, Gold Coast",
            105,
            1420,
            "Moderate",
        )
        tamborine = make_event(
            sam,
            hill_climb,
            "Tamborine Dawn Climb",
            61,
            "hill-climb.svg",
            "42.00",
            90,
            "Oxenford, Gold Coast",
            36,
            940,
            "Advanced",
        )

        for event, points in (
            (glass_house, [34, 68, 96]),
            (summit, [9, 15]),
            (river_loop, [21]),
            (border_ranges, [28, 57]),
            (winter_classic, [35, 72]),
            (tamborine, [18, 29]),
        ):
            add_points(event, points)

        db.session.add_all(
            [
                carl,
                maya,
                sam,
                gran_fondo,
                hill_climb,
                group_ride,
                glass_house,
                summit,
                river_loop,
                border_ranges,
                winter_classic,
                tamborine,
            ]
        )
        db.session.flush()

        bookings = [
            Booking(
                booking_reference="RQ-DEMO-1001",
                quantity=2,
                unit_price=glass_house.price,
                participation_group="Amateur",
                bicycle_type="Endurance road bike",
                equipment_confirmed=True,
                user=maya,
                event=glass_house,
            ),
            Booking(
                booking_reference="RQ-DEMO-1002",
                quantity=4,
                unit_price=summit.price,
                participation_group="Elite",
                bicycle_type="Road bike",
                equipment_confirmed=True,
                user=carl,
                event=summit,
            ),
            Booking(
                booking_reference="RQ-DEMO-1003",
                quantity=1,
                unit_price=river_loop.price,
                participation_group="Leisure",
                bicycle_type="E-bike",
                equipment_confirmed=True,
                user=carl,
                event=river_loop,
            ),
            Booking(
                booking_reference="RQ-DEMO-1004",
                quantity=1,
                unit_price=winter_classic.price,
                participation_group="Amateur",
                bicycle_type="Road bike",
                equipment_confirmed=True,
                user=carl,
                event=winter_classic,
            ),
        ]
        comments = [
            Comment(
                content=(
                    "Is there a supervised bag drop near registration?"
                ),
                author=maya,
                event=glass_house,
            ),
            Comment(
                content=(
                    "Yes. The organiser confirmed it will be beside the "
                    "registration tent."
                ),
                author=sam,
                event=glass_house,
            ),
            Comment(
                content="Would 32 mm road tyres be suitable for this route?",
                author=carl,
                event=glass_house,
            ),
        ]
        db.session.add_all(bookings + comments)
        db.session.commit()

        print("RideQuest database created.")
        print("Demo password for all users: RideQuest123!")
        print("Demo emails: carl@example.com, maya@example.com")


if __name__ == "__main__":
    seed_database()
