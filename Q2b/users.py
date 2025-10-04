"""User utilities including seeding default accounts."""

from werkzeug.security import generate_password_hash
from model import User


def seed_default_users():
	"""Ensure default admin and standard user exist.

	Admin: admin@lib.sg / 12345
	User:  poh@lib.sg / 12345
	Passwords stored as hashes.
	"""
	defaults = [
		{
			'email': 'admin@lib.sg',
			'name': 'Admin',
			'password': '12345',
			'is_admin': True,
		},
		{
			'email': 'poh@lib.sg',
			'name': 'Peter Oh',
			'password': '12345',
			'is_admin': False,
		},
	]

	created = []
	for data in defaults:
		if not User.objects(email=data['email']).first():
			user = User(
				email=data['email'],
				name=data['name'],
				password=generate_password_hash(data['password']),
				is_admin=data['is_admin']
			)
			user.save()
			created.append(data['email'])
	if created:
		print(f"Seeded users: {', '.join(created)}")
	else:
		print("Default users already present.")

