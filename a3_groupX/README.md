# RideQuest

RideQuest is the IFQ557 Assignment 2 event management application for road
cycling, hill-climb and weekend group-ride events.

## Run the submitted application

From the `a3_groupX` folder:

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

Open `http://127.0.0.1:5000`.

The submitted `ridequest/sitedata.sqlite` database already contains synthetic
events, users, bookings and comments. It does not need to be recreated.

## Demonstration accounts

- `carl@example.com`
- `maya@example.com`
- `sam@example.com`

Password for every demonstration account: `RideQuest123!`

Carl owns the Glass House Gran Fondo and can demonstrate updating or cancelling
his own event. Other users receive a 403 response if they attempt that action.

## Optional database reset

```bash
python3 seed_data.py
```

This deletes and rebuilds the synthetic demonstration database.

## Tests

```bash
python3 -m unittest discover -s tests -v
```
