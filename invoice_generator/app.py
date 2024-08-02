from flask import Flask, render_template, make_response, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from decimal import Decimal
from weasyprint import HTML
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'nacim'
app.config['MYSQL_PASSWORD'] = 'NACIM'
app.config['MYSQL_DB'] = 'invoice_generator_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

# Routes
# Route to index
@app.route('/')
def index():
    if 'user_id' in session:
        # Fetch user data based on session['user_id']
        user_id = session['user_id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()

        if user:
            return render_template('index.html', user=user)
        else:
            return "User not found", 404
    else:
        return redirect(url_for('login'))

# Route to login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user['password'], password):
            # Log the user in
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('index'))  # Redirect to index or dashboard
        else:
            return "Invalid email or password", 401

    return render_template('login.html')

# Route to logout
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear all session data
    return redirect(url_for('login'))  # Redirect to login page

# Route to register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not name or not email or not password or not confirm_password:
            return "All fields are required", 400

        if password != confirm_password:
            return "Passwords do not match", 400

        hashed_password = generate_password_hash(password, method='sha256')

        try:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
            mysql.connection.commit()
            cur.close()
        except Exception as e:
            return f"An error occurred: {str(e)}", 500

        return "Registration successful"

    return render_template('registration.html')

# Route to display all clients
@app.route('/clients')
def all_clients():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM clients")
    clients = cur.fetchall()
    cur.close()
    return render_template('clients.html', clients=clients)

# Route to add a new client
@app.route('/clients/new', methods=['GET', 'POST'])
def new_client():
    if request.method == 'POST':
        name = request.form['name']
        phone_number = request.form['phone_number']
        email = request.form['email']
        address = request.form['address']
        tax_registration_number = request.form['tax_registration_number']
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO clients (name, phone_number, email, address, tax_registration_number) VALUES (%s, %s, %s, %s, %s)",
                    (name, phone_number, email, address, tax_registration_number))
        mysql.connection.commit()
        cur.close()
        flash('Client added successfully', 'success')
        return redirect(url_for('all_clients'))
    return render_template('new_client.html')

# Route to edit a client
@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        name = request.form['name']
        phone_number = request.form['phone_number']
        email = request.form['email']
        address = request.form['address']
        tax_registration_number = request.form['tax_registration_number']
        
        cur.execute("UPDATE clients SET name=%s, phone_number=%s, email=%s, address=%s, tax_registration_number=%s WHERE client_id=%s",
                    (name, phone_number, email, address, tax_registration_number, client_id))
        mysql.connection.commit()
        cur.close()
        flash('Client updated successfully', 'success')
        return redirect(url_for('all_clients'))
    
    cur.execute("SELECT * FROM clients WHERE client_id = %s", (client_id,))
    client = cur.fetchone()
    cur.close()
    return render_template('edit_client.html', client=client)

# Route to delete a client
@app.route('/clients/delete/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    try:
        cur = mysql.connection.cursor()

        # Delete related records in invoice_articles
        cur.execute("""
            DELETE ia FROM invoice_articles ia
            JOIN invoices i ON ia.invoice_id = i.invoice_number
            WHERE i.client_id = %s
        """, (client_id,))

        # Delete related records in invoices
        cur.execute("DELETE FROM invoices WHERE client_id = %s", (client_id,))

        # Finally, delete the client
        cur.execute("DELETE FROM clients WHERE client_id = %s", (client_id,))

        mysql.connection.commit()
        cur.close()
        flash('Client deleted successfully', 'success')
    except pymysql.err.OperationalError as e:
        if e.args[0] == 1205:  # Lock wait timeout
            flash('Operation timed out. Please try again.', 'danger')
        else:
            flash('An error occurred. Please try again.', 'danger')
    except pymysql.err.IntegrityError as e:
        flash('Integrity error: ' + str(e), 'danger')
    except Exception as e:
        flash('An unexpected error occurred: ' + str(e), 'danger')

    return redirect(url_for('all_clients'))

# Route to display all articles
@app.route('/articles')
def all_articles():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()
    cur.close()
    return render_template('articles.html', articles=articles)

# Route to add a new article
@app.route('/articles/new', methods=['GET', 'POST'])
def new_article():
    if request.method == 'POST':
        name = request.form['name']
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO articles (name) VALUES (%s)", (name,))
        mysql.connection.commit()
        cur.close()
        flash('Article added successfully', 'success')
        return redirect(url_for('all_articles'))
    return render_template('new_article.html')

# Route to edit an article
@app.route('/articles/edit/<int:article_id>', methods=['GET', 'POST'])
def edit_article(article_id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        name = request.form['name']
        
        cur.execute("UPDATE articles SET name=%s WHERE article_id=%s", (name, article_id))
        mysql.connection.commit()
        cur.close()
        flash('Article updated successfully', 'success')
        return redirect(url_for('all_articles'))
    
    cur.execute("SELECT * FROM articles WHERE article_id = %s", (article_id,))
    article = cur.fetchone()
    cur.close()
    return render_template('edit_article.html', article=article)

# Route to delete an article
@app.route('/articles/delete/<int:article_id>', methods=['POST'])
def delete_article(article_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM articles WHERE article_id = %s", (article_id,))
    mysql.connection.commit()
    cur.close()
    flash('Article deleted successfully', 'success')
    return redirect(url_for('all_articles'))

# Route to display all invoices
@app.route('/invoices')
def all_invoices():
    cur = mysql.connection.cursor()
    cur.execute("SELECT invoices.*, clients.name AS client_name FROM invoices JOIN clients ON invoices.client_id = clients.client_id ORDER BY invoice_number")
    invoices = cur.fetchall()
    cur.close()
    return render_template('invoices.html', invoices=invoices)

# Route to add a new invoice
@app.route('/invoices/new', methods=['GET', 'POST'])
def new_invoice():
    if request.method == 'POST':
        try:
            # Extract form data
            invoice_date = request.form['invoice_date']
            client_id = request.form['client_id']
            delivery_date = request.form['delivery_date']
            return_date = request.form['return_date']
            payment_due_date = request.form['payment_due_date']
            payment_method = request.form['payment_method']
            rental_contract_number = request.form['rental_contract_number']
            description = request.form['description']
            status = request.form['status']
            discount = Decimal(request.form['discount'])

            cur = mysql.connection.cursor()

            # Insert into invoices table
            cur.execute("INSERT INTO invoices (invoice_date, client_id, delivery_date, return_date, payment_due_date, payment_method, rental_contract_number, description, status, discount) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (invoice_date, client_id, delivery_date, return_date, payment_due_date, payment_method, rental_contract_number, description, status, discount))
            mysql.connection.commit()

            # Get the last inserted invoice ID
            cur.execute("SELECT LAST_INSERT_ID() AS invoice_id")
            invoice_id = cur.fetchone()['invoice_id']

            # Retrieve item details from the form
            article_ids = request.form.getlist('article_id[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')

            # Insert each item into the invoice_articles table
            for article_id, quantity, unit_price in zip(article_ids, quantities, unit_prices):
                # Convert unit_price to decimal.Decimal
                unit_price_decimal = Decimal(unit_price)
                cur.execute("INSERT INTO invoice_articles (invoice_id, article_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                            (invoice_id, article_id, quantity, unit_price_decimal))
            mysql.connection.commit()

            # Calculate total price and update invoice
            cur.execute("SELECT SUM(quantity * unit_price) AS total FROM invoice_articles WHERE invoice_id = %s", (invoice_id,))
            result = cur.fetchone()
            total_price = result['total'] if result and result['total'] is not None else Decimal('0.0')

            # Apply discount to total price
            total_price -= total_price * (discount / Decimal('100'))

            # Add TVA (let's assume 19%) and timbre (1 DT)
            tva = total_price * Decimal('0.19')
            total_with_tva = total_price + tva + Decimal('1.0')

            # Update invoice with total price including discount
            cur.execute("UPDATE invoices SET total_price = %s WHERE invoice_number = %s", (total_with_tva, invoice_id))
            mysql.connection.commit()

            cur.close()
            flash('Invoice added successfully', 'success')
            return redirect(url_for('all_invoices'))

        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
            return redirect(url_for('new_invoice'))

    # GET method
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM clients")
    clients = cur.fetchall()
    cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()
    cur.close()
    return render_template('new_invoice.html', clients=clients, articles=articles)

# Route to change payement status
@app.route('/invoice/status/<invoice_number>', methods=['POST'])
def change_status(invoice_number):
    new_status = request.form['status']
    invoice = Invoice.query.filter_by(invoice_number=invoice_number).first()
    if invoice:
        invoice.status = new_status
        db.session.commit()
    return redirect(url_for('all_invoices'))

# Route to edit an invoice
@app.route('/edit_invoice/<int:invoice_number>', methods=['GET', 'POST'])
def edit_invoice(invoice_number):
    if request.method == 'POST':
        # Extract form data
        invoice_date = request.form['invoice_date']
        client_id = request.form['client_id']
        delivery_date = request.form['delivery_date']
        return_date = request.form['return_date']
        payment_due_date = request.form['payment_due_date']
        payment_method = request.form['payment_method']
        rental_contract_number = request.form['rental_contract_number']
        description = request.form['description']
        status = request.form['status']
        discount = Decimal(request.form['discount'])  # Ensure discount is a Decimal

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE invoices 
            SET invoice_date = %s, client_id = %s, delivery_date = %s, return_date = %s, 
                payment_due_date = %s, payment_method = %s, rental_contract_number = %s, description = %s,
                status = %s, discount = %s
            WHERE invoice_number = %s
            """,
            (invoice_date, client_id, delivery_date, return_date, payment_due_date, payment_method, rental_contract_number, description, status, discount, invoice_number))
        mysql.connection.commit()

        # Remove all current items from invoice_articles
        cur.execute("DELETE FROM invoice_articles WHERE invoice_id = %s", (invoice_number,))

        # Insert new items
        article_ids = request.form.getlist('article_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for article_id, quantity, unit_price in zip(article_ids, quantities, unit_prices):
            cur.execute("""
                INSERT INTO invoice_articles (invoice_id, article_id, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
                """,
                (invoice_number, article_id, quantity, unit_price))

        mysql.connection.commit()
        # Calculate total price and update invoice
        cur.execute("SELECT SUM(quantity * unit_price) AS total FROM invoice_articles WHERE invoice_id = %s", (invoice_number,))
        total_price = cur.fetchone()['total']

        # Ensure total_price is a Decimal
        total_price = Decimal(total_price)

        # Apply discount
        discount_amount = total_price * (discount / Decimal('100'))
        total_price -= discount_amount

        # Add TVA (19%) and timbre (1 DT)
        tva = total_price * Decimal('0.19')
        total_with_tva = total_price + tva + Decimal('1')

        cur.execute("UPDATE invoices SET total_price = %s WHERE invoice_number = %s", (total_with_tva, invoice_number))
        mysql.connection.commit()
        return redirect(url_for('all_invoices'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM invoices WHERE invoice_number = %s", (invoice_number,))
    invoice = cur.fetchone()
    cur.execute("SELECT * FROM clients")
    clients = cur.fetchall()
    cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()
    cur.execute("""
        SELECT ia.article_id, ia.quantity, ia.unit_price, a.name 
        FROM invoice_articles ia 
        JOIN articles a ON ia.article_id = a.article_id 
        WHERE ia.invoice_id = %s
        """, (invoice_number,))
    invoice_articles = cur.fetchall()
    cur.close()
    return render_template('edit_invoice.html', invoice=invoice, clients=clients, articles=articles, invoice_articles=invoice_articles)

# Route to invoice pdf
@app.route('/invoices/pdf/<int:invoice_number>')
def invoice_pdf(invoice_number):
    cur = mysql.connection.cursor()

    # Fetch invoice details
    cur.execute("SELECT * FROM invoices WHERE invoice_number = %s", (invoice_number,))
    invoice = cur.fetchone()

    # Fetch invoice articles with article details
    cur.execute("""
        SELECT ia.quantity, ia.unit_price, ia.quantity * ia.unit_price AS total,
               a.name AS article_name
        FROM invoice_articles ia
        JOIN articles a ON ia.article_id = a.article_id
        WHERE ia.invoice_id = %s
    """, (invoice_number,))
    invoice_articles = cur.fetchall()

    # Fetch client details
    cur.execute("SELECT * FROM clients WHERE client_id = %s", (invoice['client_id'],))
    client = cur.fetchone()

    cur.close()

    # Calculate total price
    total_price = Decimal('0.0')
    for item in invoice_articles:
        total_price += item['quantity'] * item['unit_price']

    # Apply discount if it exists
    discount = invoice.get('discount', Decimal('0'))
    if discount is not None:
        discount_amount = total_price * (discount / Decimal('100'))
        total_price -= discount_amount
    else:
        discount_amount = Decimal('0.0')

    # Calculate TVA (19%) and Timbre (1.0)
    tva = total_price * Decimal('0.19')
    total_with_tva = total_price + tva + Decimal('1.0')

    # Format total_price to 3 decimal places
    total_price = total_price.quantize(Decimal('0.001'))
    total_with_tva = total_with_tva.quantize(Decimal('0.001'))

    # Render HTML template
    html = render_template('invoice_pdf.html', invoice=invoice, invoice_articles=invoice_articles, total_price=total_price, tva=tva, total_with_tva=total_with_tva, client=client, discount_amount=discount_amount)
    
    # Create PDF using WeasyPrint
    pdf = HTML(string=html).write_pdf()

    # Create a response with PDF
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=invoice_{invoice_number}.pdf'

    return response
# Addtional options are under development
# Route to credit note
@app.route('/invoices/create_credit_note/<int:invoice_number>', methods=['GET', 'POST'])
def create_credit_note(invoice_number):
    if request.method == 'POST':
        reason = request.form.get('reason')
        amount = request.form.get('amount')
        credit_date = datetime.now().date()  # Automatically set the current date

        cur = mysql.connection.cursor()

        # Insert into credit_notes table
        cur.execute("""
            INSERT INTO credit_notes (invoice_number, credit_date, amount, reason)
            VALUES (%s, %s, %s, %s)
        """, (invoice_number, credit_date, amount, reason))

        # Get the newly created credit note ID
        credit_note_id = cur.lastrowid

        mysql.connection.commit()
        cur.close()

        flash('Credit note created successfully', 'success')
        return redirect(url_for('all_credit_notes'))  # Redirect to the all_credit_notes route

    # Fetch invoice details or other necessary data for the form
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT * FROM invoices WHERE invoice_number = %s
    """, (invoice_number,))
    invoice = cur.fetchone()
    cur.close()

    return render_template('create_credit_note.html', invoice=invoice)

# Route to lists credit note
@app.route('/credit_notes')
def all_credit_notes():
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of records per page
    offset = (page - 1) * per_page

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT credit_notes.id AS `Credit Note ID`,
               credit_notes.invoice_number AS `Invoice Number`,
               clients.name AS `Client Name`,
               credit_notes.credit_date AS `Credit Date`,
               credit_notes.amount AS `Amount`,
               credit_notes.reason AS `Reason`,
               'View PDF' AS `Action`
        FROM credit_notes
        JOIN invoices ON credit_notes.invoice_number = invoices.invoice_number
        JOIN clients ON invoices.client_id = clients.client_id
        ORDER BY credit_notes.id ASC
        LIMIT %s OFFSET %s;
    """, (per_page, offset))

    credit_notes = cur.fetchall()
    cur.close()

    return render_template('credit_notes.html', credit_notes=credit_notes)

# Route to credit note pdf
@app.route('/credit_note_pdf/<int:credit_note_id>', methods=['GET'])
def credit_note_pdf(credit_note_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT credit_notes.*, invoices.client_id, clients.name AS client_name
        FROM credit_notes
        JOIN invoices ON credit_notes.invoice_number = invoices.invoice_number
        JOIN clients ON invoices.client_id = clients.client_id
        WHERE credit_notes.id = %s
    """, (credit_note_id,))
    credit_note = cur.fetchone()
    cur.close()

    if not credit_note:
        abort(404)  # Handle case where credit note with given ID doesn't exist

    # Prepare data to pass to template
    data = {
        'invoice_number': credit_note['invoice_number'],
        'credit_note_number': credit_note['id'],  # Assuming 'id' is the credit note ID
        'reason': credit_note['reason'],
        'amount': credit_note['amount'],
        'client_name': credit_note['client_name'],
    }

    # Render HTML template with data
    rendered = render_template('credit_note_pdf.html', data=data)

    # Generate PDF from rendered HTML
    pdf = HTML(string=rendered).write_pdf()

    # Prepare PDF response
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=credit_note.pdf'
    return response


if __name__ == '__main__':
    app.run(debug=True, port=8000)
