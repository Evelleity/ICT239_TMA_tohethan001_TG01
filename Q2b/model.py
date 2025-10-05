from flask_mongoengine import Document
from mongoengine.fields import (
    StringField, ListField, IntField, BooleanField, ReferenceField, DateTimeField
)
from mongoengine import CASCADE, DENY
from datetime import datetime, timedelta
from random import randint
import books as book_data # Import the hardcoded book data

class Book(Document):
    """
    Book model for the library database
    """
    title = StringField(required=True)
    authors = ListField(StringField(), required=True)
    genres = ListField(StringField())
    category = StringField()
    url = StringField()
    description = ListField(StringField())
    pages = IntField()
    available = IntField()
    copies = IntField()
    
    meta = {'collection': 'books'}

    def clean(self):
        """Ensure description is always stored as a list of non-empty strings.

        MongoEngine calls `clean` before validation on save. This prevents any
        accidental assignment of a single string or None to `description`.
        """
        if self.description is None:
            self.description = []
        elif isinstance(self.description, str):
            text = self.description.strip()
            self.description = [text] if text else []
        elif isinstance(self.description, list):
            # Filter to strings, strip whitespace, drop empties
            self.description = [p.strip() for p in self.description if isinstance(p, str) and p.strip()]

    @property
    def first_paragraph(self) -> str:
        """Convenience accessor for templates: returns first paragraph or empty string."""
        return self.description[0] if self.description else ""

    @staticmethod
    def init_db():
        """
        Initializes the database with book data if the collection is empty.
        """
        # Check if the 'books' collection is empty
        if Book.objects.count() == 0:
            print("Database is empty. Seeding with initial data...")
            # Add each book from the books.py file to the database
            for i, book_dict in enumerate(book_data.all_books):
                # Accept list or single string; normalize to list of trimmed non-empty paragraphs
                raw_desc = book_dict.get('description', [])
                if isinstance(raw_desc, str):
                    desc_list = [raw_desc.strip()] if raw_desc.strip() else []
                elif isinstance(raw_desc, list):
                    desc_list = [p.strip() for p in raw_desc if isinstance(p, str) and p.strip()]
                else:
                    desc_list = []

                book = Book(
                    title=book_dict['title'],
                    authors=book_dict['authors'],
                    genres=book_dict['genres'],
                    category=book_dict['category'],
                    url=book_dict['url'],
                    description=desc_list,
                    pages=book_dict['pages'],
                    available=book_dict['available'],
                    copies=book_dict['copies']
                )
                book.save()
            print("Database seeded successfully.")
        else:
            print("Database already contains data. Skipping seed.")

class User(Document):
    """User model for authentication/registration.

    Extended with email, display name, and admin flag.
    """
    username = StringField(required=True, unique=True)
    email = StringField(required=True, unique=True)
    name = StringField(required=True)
    password_hash = StringField(required=True)
    is_admin = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {'collection': 'users', 'indexes': ['username', 'email', 'is_admin']}

    # Convenience helpers kept simple; you could swap for passlib or werkzeug.security
    def set_password(self, raw_password: str):
        # Basic hashing (NOT for production). Replace with werkzeug.security.generate_password_hash
        import hashlib
        self.password_hash = hashlib.sha256(raw_password.encode('utf-8')).hexdigest()

    def check_password(self, raw_password: str) -> bool:
        import hashlib
        return self.password_hash == hashlib.sha256(raw_password.encode('utf-8')).hexdigest()

def seed_users():
    """Seed specified admin and non-admin users if they do not exist.

    Requirements:
      - Admin: email=admin@lib.sg, username=admin, name=Admin, password=12345
      - Member: email=poh@lib.sg, username=poh, name=Peter Oh, password=12345
    """
    defaults = [
        {
            'username': 'admin',
            'email': 'admin@lib.sg',
            'name': 'Admin',
            'password': '12345',
            'is_admin': True,
        },
        {
            'username': 'poh',
            'email': 'poh@lib.sg',
            'name': 'Peter Oh',
            'password': '12345',
            'is_admin': False,
        }
    ]
    created = []
    for data in defaults:
        existing = User.objects(username=data['username']).first() or User.objects(email=data['email']).first()
        if existing:
            continue
        u = User(
            username=data['username'],
            email=data['email'],
            name=data['name'],
            is_admin=data['is_admin']
        )
        u.set_password(data['password'])
        u.save()
        created.append(data['username'])
    if created:
        print(f"Seeded users: {', '.join(created)}")
    else:
        print("Seed users already present; skipping.")

class Loan(Document):
    """Loan model & domain logic for user book loans.

    Rules implemented (from specification):
    - A user cannot create a new (unreturned) loan for the same book title if one already exists.
    - Book's available count decremented on successful loan creation; incremented on return.
    - Borrow date is randomly generated 10–20 days BEFORE today on creation.
    - Due date is 14 days after borrow date.
    - Renew: allowed only if not returned, not overdue, renew_count < 2. Renew sets a NEW borrow date
      randomly 10–20 days AFTER the current borrow date (capped at today) and recalculates due date.
    - Return: sets a return date randomly 10–20 days AFTER borrow date (capped at today) and restores availability.
    - Delete: allowed only after return.
    """

    member = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    book = ReferenceField(Book, required=True, reverse_delete_rule=DENY)
    borrow_date = DateTimeField(required=True)
    due_date = DateTimeField(required=True)
    return_date = DateTimeField()
    renew_count = IntField(default=0)

    meta = {
        'collection': 'loans',
        'indexes': [
            '-borrow_date',  # for sorting newest first
            {'fields': ['member', 'book', 'return_date']},
        ]
    }

    # # Constants / configuration
    # LOAN_PERIOD_DAYS = 14
    # MAX_RENEWS = 2
    # RANDOM_PAST_MIN = 10  # creation: borrow date = today - rand(10..20)
    # RANDOM_PAST_MAX = 20
    # RANDOM_FUTURE_MIN = 10  # renew/return generation relative to existing borrow date
    # RANDOM_FUTURE_MAX = 20

    # # -------------------- Creation & Retrieval --------------------
    # @classmethod
    # def _random_past_borrow_date(cls) -> datetime:
    #     return datetime.utcnow() - timedelta(days=randint(cls.RANDOM_PAST_MIN, cls.RANDOM_PAST_MAX))

    # @classmethod
    # def _random_future_date_from(cls, base_dt: datetime) -> datetime:
    #     candidate = base_dt + timedelta(days=randint(cls.RANDOM_FUTURE_MIN, cls.RANDOM_FUTURE_MAX))
    #     # Cannot be later than 'now'
    #     now = datetime.utcnow()
    #     return candidate if candidate <= now else now

    # @classmethod
    # def create_loan(cls, user: User, book: Book):
    #     """Attempt to create a new loan.

    #     Returns: (loan, created_bool, message)
    #     """
    #     # Check existing active loan
    #     existing = cls.objects(member=user, book=book, return_date__exists=False).first()
    #     if existing:
    #         return existing, False, "You already have this book on loan."
    #     if book.available <= 0:
    #         return None, False, "No available copies for this title."

    #     borrow_date = cls._random_past_borrow_date()
    #     due_date = borrow_date + timedelta(days=cls.LOAN_PERIOD_DAYS)

    #     loan = cls(member=user, book=book, borrow_date=borrow_date, due_date=due_date)
    #     loan.save()

    #     # Decrement availability
    #     book.available -= 1
    #     if book.available < 0:
    #         book.available = 0  # safety
    #     book.save()
    #     return loan, True, "Loan created successfully."

    # @classmethod
    # def for_user(cls, user: User):
    #     return cls.objects(member=user).order_by('-borrow_date')

    # @classmethod
    # def get_user_loan(cls, user: User, loan_id: str):
    #     return cls.objects(member=user, id=loan_id).first()

    # # -------------------- State & Helper Properties --------------------
    # @property
    # def is_returned(self) -> bool:
    #     return self.return_date is not None

    # @property
    # def is_overdue(self) -> bool:
    #     return (not self.is_returned) and datetime.utcnow() > self.due_date

    # @property
    # def can_renew(self) -> bool:
    #     return (not self.is_returned) and (not self.is_overdue) and self.renew_count < self.MAX_RENEWS

    # @property
    # def can_return(self) -> bool:
    #     return not self.is_returned

    # @property
    # def can_delete(self) -> bool:
    #     return self.is_returned

    # # -------------------- Actions --------------------
    # def renew(self):
    #     """Renew this loan if possible.
    #     Returns (success_bool, message).
    #     """
    #     if not self.can_renew:
    #         if self.is_returned:
    #             return False, "Cannot renew a returned loan."
    #         if self.is_overdue:
    #             return False, "Cannot renew an overdue loan."
    #         return False, "Maximum renewals reached."

    #     # Generate new borrow date in the 'past' relative to today but after original borrow_date
    #     new_borrow_date = self._random_future_date_from(self.borrow_date)
    #     # Ensure monotonic increase
    #     if new_borrow_date <= self.borrow_date:
    #         new_borrow_date = datetime.utcnow()
    #     self.borrow_date = new_borrow_date
    #     self.due_date = self.borrow_date + timedelta(days=self.LOAN_PERIOD_DAYS)
    #     self.renew_count += 1
    #     self.save()
    #     return True, "Loan renewed."

    # def return_book(self):
    #     """Return this loan if possible.
    #     Returns (success_bool, message).
    #     """
    #     if not self.can_return:
    #         return False, "Loan already returned."

    #     self.return_date = self._random_future_date_from(self.borrow_date)
    #     if self.return_date < self.borrow_date:
    #         self.return_date = datetime.utcnow()
    #     self.save()

    #     # Restore availability
    #     self.book.available += 1
    #     self.book.save()
    #     return True, "Book returned."

    # def delete_if_allowed(self):
    #     if not self.can_delete:
    #         return False, "Only returned loans can be deleted."
    #     self.delete()
    #     return True, "Loan deleted."

    # # -------------------- Validation Hook --------------------
    # def clean(self):
    #     if not self.due_date and self.borrow_date:
    #         self.due_date = self.borrow_date + timedelta(days=self.LOAN_PERIOD_DAYS)