from flask import Flask, render_template, request
from flask_mongoengine import MongoEngine
import books
 
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['MONGODB_SETTINGS'] = {
    'db': 'ict_239_library',
    'host': 'localhost',
    'port': 27017
}

db = MongoEngine(app)

@app.route('/')
def index():
    # Get the category from the request args (if any)
    category = request.args.get('category', None)
    if category:
        filtered_books = [book for book in books.all_books if category in book['category']]
    else:
        filtered_books = books.all_books

    # Sort books by title
    filtered_books.sort(key=lambda x: x['title'])

    return render_template('index.html', books=filtered_books, category=category)

@app.route('/book/<int:book_id>')
def book_details(book_id):
    book = books.all_books[book_id]

    return render_template('book_details.html', book=book, panel='BOOK DETAILS')

if __name__ == '__main__':
    app.run(debug=True)