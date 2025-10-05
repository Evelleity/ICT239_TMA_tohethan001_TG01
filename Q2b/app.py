from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mongoengine import MongoEngine
from model import Book, User, seed_users
from bson import ObjectId  # if needed, often not required directly
from mongoengine import DoesNotExist

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['MONGODB_SETTINGS'] = {
    'db': 'ict_239_library',
    'host': 'localhost',
    'port': 27017
}

db = MongoEngine(app)

Book.init_db()  # Initialize the database with book data
seed_users()    # Seed default users

@app.route('/')
def index():
    # Get the category from the request args (if any)
    category = request.args.get('category', None)
    if category:
        # Query the database for books matching the category and sort them by title
        filtered_books = Book.objects(category=category).order_by('title')
    else:
        # Query the database for all books and sort them by title
        filtered_books = Book.objects().order_by('title')

    return render_template('index.html', books=filtered_books, category=category)

@app.route('/book/<book_id>')
def book_details(book_id):
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        # handle 404 appropriately
        return "Book not found", 404
    return render_template('book_details.html', book=book, panel='BOOK DETAILS')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Email-based registration.

    Inputs (POST): email, password, name
    Username is derived automatically from the part before '@'.
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        name = request.form.get('name', '').strip()

        if not email or not password or not name:
            flash('Email, password and name are required.', 'danger')
        elif '@' not in email:
            flash('Please provide a valid email address.', 'danger')
        elif User.objects(email=email).first():
            flash('Email already registered.', 'warning')
        else:
            # Derive username from email local part; ensure uniqueness fallback
            base_username = email.split('@', 1)[0]
            username = base_username
            suffix = 1
            while User.objects(username=username).first():
                username = f"{base_username}{suffix}"
                suffix += 1

            u = User(username=username, email=email, name=name)
            u.set_password(password)
            u.save()
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html', panel='REGISTER')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Email + password login."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        user = User.objects(email=email).first()
        if user and user.check_password(password):
            flash('Login success (session handling not yet implemented).', 'success')
            return redirect(url_for('index'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', panel='LOGIN')

if __name__ == '__main__':
    app.run(debug=True)