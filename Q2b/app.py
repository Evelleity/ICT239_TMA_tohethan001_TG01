from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mongoengine import MongoEngine
from model import Book, User
from users import seed_default_users
from forms import RegistrationForm, LoginForm
from werkzeug.security import generate_password_hash
 
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['MONGODB_SETTINGS'] = {
    'db': 'ict_239_library',
    'host': 'localhost',
    'port': 27017
}

db = MongoEngine(app)

Book.init_db()  # Initialize the database with book data
seed_default_users()  # Ensure default users exist

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

@app.route('/book/<int:book_id>')
def book_details(book_id):
    book = book.all_books[book_id]

    return render_template('book_details.html', book=book, panel='BOOK DETAILS')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if email already exists
        existing = User.objects(email=form.email.data.lower()).first()
        if existing:
            flash('A user with that email already exists.', 'error')
            return render_template('register.html', form=form)

        # Create new user
        user = User(
            email=form.email.data.lower(),
            name=form.username.data,
            password=generate_password_hash(form.password.data)
        )
        user.save()
        flash('Registration successful. You can now log in.', 'success')
        return redirect(url_for('register'))  # Change to 'login' when login implemented

    # For GET or failed validation
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.objects(email=form.email.data.lower()).first()
        if not user:
            flash('Invalid email or password.', 'error')
            return render_template('login.html', form=form)
        # Password verification placeholder (hash check needed when users exist)
        # from werkzeug.security import check_password_hash
        # if not check_password_hash(user.password, form.password.data):
        #     flash('Invalid email or password.', 'error')
        #     return render_template('login.html', form=form)
        flash('Login successful (password check not yet implemented).', 'success')
        return redirect(url_for('index'))
    return render_template('login.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)