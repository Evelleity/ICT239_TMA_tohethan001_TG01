from flask import Flask, render_template, request, redirect, url_for, flash, session, g
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

# -------------------- Auth / Role Helpers --------------------
from functools import wraps

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper

@app.before_request
def load_current_user():
    g.current_user = None
    uid = session.get('user_id')
    if uid:
        try:
            g.current_user = User.objects(id=uid).first()
        except Exception:
            g.current_user = None

@app.context_processor
def inject_user():
    return {'current_user': g.get('current_user'), 'is_admin': bool(session.get('is_admin'))}

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
            session['user_id'] = str(user.id)
            session['is_admin'] = bool(user.is_admin)
            session['name'] = user.name
            flash('Login success.', 'success')
            return redirect(url_for('index'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', panel='LOGIN')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/new_book', methods=['GET', 'POST'])  # direct alias
@app.route('/books/new', methods=['GET', 'POST'])  # original path also supported
@admin_required
def new_book():
    """Create a new Book (admin only).

        Enhancements:
            - Authors textarea (semicolon separated) unlimited.
      - Persist submitted form values on validation errors.
      - On success: flash + show success link + reset form.
    """
    form_data = {
        'title': '', 'category': '', 'url': '', 'pages': '', 'copies': '1',
        'description': '', 'authors_text': '', 'selected_genres': []
    }
    created_book = None
    if request.method == 'POST':
        # Extract raw inputs
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        url_val = request.form.get('url', '').strip()
        pages_raw = request.form.get('pages', '').strip()
        copies_raw = request.form.get('copies', '').strip()
        description_raw = request.form.get('description', '').strip()
        authors_text = request.form.get('authors_text', '').strip()
        selected_genres = request.form.getlist('genres')

        # Persist attempted values
        form_data.update({
            'title': title,
            'category': category,
            'url': url_val,
            'pages': pages_raw,
            'copies': copies_raw or '1',
            'description': description_raw,
            'authors_text': authors_text,
            'selected_genres': selected_genres,
        })

        # Authors parsing: semicolon separated values, strip, remove duplicates preserving order
        raw_authors = [ln.strip() for ln in authors_text.split(';')] if authors_text else []
        authors = []
        for a in raw_authors:
            if a and a not in authors:
                authors.append(a)

        errors = []
        if not title:
            errors.append('Title is required.')
        if not authors:
            errors.append('At least one author is required (separate authors with a semicolon).')

        pages = None
        if pages_raw:
            try:
                pages = int(pages_raw)
                if pages < 1:
                    errors.append('Pages must be at least 1.')
            except ValueError:
                errors.append('Pages must be a number.')
        copies = 1
        if copies_raw:
            try:
                copies = int(copies_raw)
                if copies < 1:
                    errors.append('Copies must be at least 1.')
            except ValueError:
                errors.append('Copies must be a number.')

        paragraphs = [p.strip() for p in description_raw.split('\n') if p.strip()]

        if errors:
            for e in errors:
                flash(e, 'danger')
        else:
            book = Book(
                title=title,
                authors=authors,
                genres=selected_genres,
                category=category or None,
                url=url_val or None,
                description=paragraphs,
                pages=pages,
                copies=copies,
                available=copies
            )
            book.save()
            created_book = book
            flash(f'"{book.title}" created successfully.', 'success')
            # Reset form fields
            form_data = {
                'title': '', 'category': '', 'url': '', 'pages': '', 'copies': '1',
                'description': '', 'authors_text': '', 'selected_genres': []
            }

    # Provide genres and categories (prefer class constant if available)
    genres_list = getattr(Book, 'GENRES', [])
    categories_list = ["Children", "Teens", "Adults", "Reference", "Comics", "Education", "General"]
    return render_template(
        'new_book.html',
        panel='NEW BOOK',
        genres=genres_list,
        categories=categories_list,
        form_data=form_data,
        created_book=created_book
    )

if __name__ == '__main__':
    app.run(debug=True)