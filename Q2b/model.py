from flask_mongoengine import Document
from mongoengine.fields import (
    StringField, ListField, IntField, BooleanField, ReferenceField, DateTimeField
)
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
    available = BooleanField()
    copies = IntField()
    
    meta = {'collection': 'books'}

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
                # Handle cases where description is a list
                desc = book_dict.get('description', '')
                if isinstance(desc, list) and desc:
                    description_text = desc[0]
                else:
                    description_text = desc

                book = Book(
                    title=book_dict['title'],
                    authors=book_dict['authors'],
                    genres=book_dict['genres'],
                    category=book_dict['category'],
                    url=book_dict['url'],
                    description=description_text, # Use the processed description
                    pages=book_dict['pages'],
                    available=book_dict['available'],
                    copies=book_dict['copies']
                )
                book.save()
            print("Database seeded successfully.")
        else:
            print("Database already contains data. Skipping seed.")

class User(Document):
    """
    User model for the library database
    """
    email = StringField(required=True, unique=True)
    password = StringField(required=True)
    name = StringField()
    is_admin = BooleanField(default=False)

    meta = {'collection': 'users'}

class Loan(Document):
    """
    Loan model for the library database
    """
    member = ReferenceField(User, required=True)
    book = ReferenceField(Book, required=True)
    borrowDate = DateTimeField(required=True)
    returnDate = DateTimeField()
    renewCount = IntField(default=0)

    meta = {'collection': 'loans'}