import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'super_secret_key_cst_project'
CURRENT_USER_ID = 1

def get_db_connection():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, 'store.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.before_request
def initialize_database():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS cart (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, quantity INTEGER)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, total_amount REAL, status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS support (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, subject TEXT, message TEXT)''')
    
    try:
        conn.execute('ALTER TABLE orders ADD COLUMN total_amount REAL')
    except sqlite3.OperationalError:
        pass 
    try:
        conn.execute('ALTER TABLE orders ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

FOOTER_PAGES = {
    'contact': {'title': 'VIP Concierge', 'icon': 'fa-envelope', 'text': 'Reach our luxury support team at concierge@greatindiastore.in.'},
    'about': {'title': 'About GREAT INDIA STORE', 'icon': 'fa-building', 'text': 'Founded as an exclusive RRKGP CST MINOR Project, bringing luxury to your fingertips.'},
    'careers': {'title': 'Careers', 'icon': 'fa-briefcase', 'text': 'Join our elite team. Send your resume to careers@greatindiastore.in.'},
    'payments': {'title': 'Payment Methods', 'icon': 'fa-credit-card', 'text': 'We accept Platinum Credit Cards, Secure UPI, and Premium COD.'},
    'shipping': {'title': 'White-Glove Delivery', 'icon': 'fa-truck-fast', 'text': 'Exclusive secure delivery takes 2-3 business days.'},
    'policy': {'title': 'Privacy & Security', 'icon': 'fa-shield-halved', 'text': 'Your data is secured with enterprise-grade 256-bit SSL encryption.'},
    'returns': {'title': 'Bespoke Returns', 'icon': 'fa-arrow-rotate-left', 'text': 'Complimentary 14-day premium return policy.'},
    'terms': {'title': 'Terms of Use', 'icon': 'fa-scale-balanced', 'text': 'Review our exclusive community guidelines and terms.'},
    'stories': {'title': 'GIS Heritage', 'icon': 'fa-book-open', 'text': 'Discover the craftsmanship behind our curated collections.'}
}

@app.route('/')
def index():
    conn = get_db_connection()
    search_query = request.args.get('q')
    try:
        if search_query:
            products = conn.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ?', ('%'+search_query+'%', '%'+search_query+'%')).fetchall()
        else:
            products = conn.execute('SELECT * FROM products').fetchall()
    except sqlite3.OperationalError:
        products = [] 
    conn.close()
    return render_template('index.html', products=products, search_query=search_query)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    conn = get_db_connection()
    existing = conn.execute('SELECT * FROM cart WHERE user_id = ? AND product_id = ?', (CURRENT_USER_ID, product_id)).fetchone()
    if existing:
        conn.execute('UPDATE cart SET quantity = quantity + 1 WHERE id = ?', (existing['id'],))
    else:
        conn.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, 1)', (CURRENT_USER_ID, product_id))
    conn.commit()
    conn.close()
    flash('Item added to your premium cart!', 'success')
    return redirect(url_for('index'))

@app.route('/cart')
def cart():
    conn = get_db_connection()
    try:
        items = conn.execute('''SELECT cart.id as cart_id, products.name, products.price, cart.quantity 
                                FROM cart JOIN products ON cart.product_id = products.id 
                                WHERE cart.user_id = ?''', (CURRENT_USER_ID,)).fetchall()
        total = sum([item['price'] * item['quantity'] for item in items])
    except sqlite3.OperationalError:
        items = []
        total = 0
    conn.close()
    return render_template('cart.html', items=items, total=total)

@app.route('/checkout')
def checkout():
    conn = get_db_connection()
    try:
        items = conn.execute('SELECT products.price, cart.quantity FROM cart JOIN products ON cart.product_id = products.id WHERE cart.user_id = ?', (CURRENT_USER_ID,)).fetchall()
        if items:
            total = sum([item['price'] * item['quantity'] for item in items])
            conn.execute('INSERT INTO orders (user_id, total_amount, status) VALUES (?, ?, ?)', (CURRENT_USER_ID, total, 'Processing VIP Order'))
            conn.execute('DELETE FROM cart WHERE user_id = ?', (CURRENT_USER_ID,))
            conn.commit()
            flash('Order placed successfully! Thank you for experiencing Great India Store.', 'success')
    except sqlite3.OperationalError:
        flash('Checkout error. Please try again.', 'error')
    conn.close()
    return redirect(url_for('history'))

@app.route('/history')
def history():
    conn = get_db_connection()
    try:
        orders = conn.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC', (CURRENT_USER_ID,)).fetchall()
    except sqlite3.OperationalError:
        orders = []
    conn.close()
    return render_template('history.html', orders=orders)

@app.route('/account')
def account():
    conn = get_db_connection()
    try:
        orders_count = conn.execute('SELECT COUNT(*) FROM orders WHERE user_id = ?', (CURRENT_USER_ID,)).fetchone()[0]
        tickets_count = conn.execute('SELECT COUNT(*) FROM support WHERE user_id = ?', (CURRENT_USER_ID,)).fetchone()[0]
    except:
        orders_count = 0
        tickets_count = 0
    conn.close()
    return render_template('account.html', current_user=CURRENT_USER_ID, orders_count=orders_count, tickets_count=tickets_count)

@app.route('/support', methods=('GET', 'POST'))
def support():
    if request.method == 'POST':
        subject = request.form['subject']
        message = request.form['message']
        conn = get_db_connection()
        conn.execute('INSERT INTO support (user_id, subject, message) VALUES (?, ?, ?)', (CURRENT_USER_ID, subject, message))
        conn.commit()
        conn.close()
        flash('Priority support ticket submitted successfully.', 'success')
        return redirect(url_for('support'))
    return render_template('support.html')

@app.route('/info/<page_id>')
def info_page(page_id):
    page_data = FOOTER_PAGES.get(page_id, {'title': 'Page Under Construction', 'icon': 'fa-person-digging', 'text': 'This section is currently being updated for a premium experience.'})
    return render_template('info.html', data=page_data)

# --- SECURE ADMIN ROUTES ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'RRKGPCST2026':  # Admin Password
            session['admin_logged_in'] = True
            flash('Admin access granted.', 'success')
            return redirect(url_for('admin_login'))
        else:
            flash('Invalid admin credentials.', 'error')
            
    if not session.get('admin_logged_in'):
        return render_template('admin_login.html')
        
    conn = get_db_connection()
    try:
        orders = conn.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
        tickets = conn.execute('SELECT * FROM support ORDER BY id DESC').fetchall()
    except:
        orders = []
        tickets = []
    conn.close()
    return render_template('admin.html', orders=orders, tickets=tickets)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Admin logged out successfully.', 'success')
    return redirect(url_for('index'))

# --- REAL-TIME IMAGE INJECTOR ---
@app.route('/magic_setup')
def magic_setup():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, price REAL, image TEXT)')
    
    # Clears old empty products
    conn.execute('DELETE FROM products')
    
    # Injects luxury products with direct, real internet photos
    real_products = [
        ('Aurum Pro Smartphone', 'Limited edition 5G mobile encased in titanium.', 125000.0, 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=500&q=80'),
        ('Titanium Creator Studio', 'High performance workstation with 4K OLED display.', 215000.0, 'https://images.unsplash.com/photo-1593642632823-8f785ba67e45?auto=format&fit=crop&w=500&q=80'),
        ('Acoustic Gold Headphones', 'Studio-grade noise cancelling audiophile headphones.', 45000.0, 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=500&q=80'),
        ('Chronograph Masterpiece', 'Swiss-crafted automatic movement luxury timepiece.', 85000.0, 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=500&q=80'),
        ('Handcrafted Leather Derbies', 'Italian bespoke calfskin leather dress shoes.', 22000.0, 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=500&q=80'),
        ('Full-Grain Weekender Bag', 'Premium waterproof leather travel companion.', 35000.0, 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=500&q=80')
    ]
    
    for p in real_products:
        conn.execute('INSERT INTO products (name, description, price, image) VALUES (?, ?, ?, ?)', p)
        
    conn.commit()
    conn.close()
    flash('Premium collection successfully loaded into the database!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

