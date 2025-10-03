from flask import Flask, render_template, request
from flask_mongoengine import MongoEngine
from model import Book
 
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['MONGODB_SETTINGS'] = {
    'db': 'ict_239_library',
    'host': 'localhost',
    'port': 27017
}

db = MongoEngine(app)

Book.init_db()  # Initialize the database with book data

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

if __name__ == '__main__':
    app.run(debug=True)