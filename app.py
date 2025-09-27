\
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "frontend", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "frontend", "static")
)

app.config['SECRET_KEY'] = "super-secret-key-please-change"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Product(db.Model):
    product_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(200), nullable=False)

class Location(db.Model):
    location_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(200), nullable=False)

class ProductMovement(db.Model):
    movement_id = db.Column(db.String(50), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    from_location = db.Column(db.String(50), db.ForeignKey('location.location_id'))
    to_location = db.Column(db.String(50), db.ForeignKey('location.location_id'))
    product_id = db.Column(db.String(50), db.ForeignKey('product.product_id'))
    qty = db.Column(db.Integer, nullable=False)

def get_product_balance(product_id, location_id):
    incoming = db.session.query(db.func.sum(ProductMovement.qty)).filter_by(product_id=product_id, to_location=location_id).scalar() or 0
    outgoing = db.session.query(db.func.sum(ProductMovement.qty)).filter_by(product_id=product_id, from_location=location_id).scalar() or 0
    return incoming - outgoing

def initialize_sample_data():
    if Product.query.count() == 0:
        products = [
            Product(product_id="P001", name="Product A"),
            Product(product_id="P002", name="Product B"),
            Product(product_id="P003", name="Product C"),
        ]
        db.session.bulk_save_objects(products)
        db.session.commit()
    if Location.query.count() == 0:
        locations = [
            Location(location_id="L001", name="Warehouse X"),
            Location(location_id="L002", name="Warehouse Y"),
            Location(location_id="L003", name="Warehouse Z"),
        ]
        db.session.bulk_save_objects(locations)
        db.session.commit()

@app.route('/')
def home():
    return redirect(url_for('report'))

@app.route('/products')
def products():
    return render_template('products.html', products=Product.query.all())

@app.route('/product/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        pid = request.form['product_id'].strip()
        name = request.form['name'].strip()
        if not pid or not name:
            flash('All fields are required!', 'error')
        elif Product.query.get(pid):
            flash('Product already exists!', 'error')
        else:
            db.session.add(Product(product_id=pid, name=name))
            db.session.commit()
            flash(f"Product '{name}' added successfully.", 'success')
            return redirect(url_for('products'))
    return render_template('product_form.html')

@app.route('/product/delete/<string:product_id>', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('products'))

@app.route('/locations')
def locations():
    return render_template('locations.html', locations=Location.query.all())

@app.route('/location/add', methods=['GET', 'POST'])
def add_location():
    if request.method == 'POST':
        lid = request.form['location_id'].strip()
        name = request.form['name'].strip()
        if not lid or not name:
            flash('All fields are required!', 'error')
        elif Location.query.get(lid):
            flash('Location already exists!', 'error')
        else:
            db.session.add(Location(location_id=lid, name=name))
            db.session.commit()
            flash(f"Location '{name}' added successfully.", 'success')
            return redirect(url_for('locations'))
    return render_template('location_form.html')

@app.route('/location/delete/<string:location_id>', methods=['POST'])
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)
    db.session.delete(location)
    db.session.commit()
    flash('Location deleted successfully!', 'success')
    return redirect(url_for('locations'))

@app.route('/movements')
def movements():
    moves = ProductMovement.query.order_by(ProductMovement.timestamp.desc()).all()
    return render_template('movements.html', movements=moves)

@app.route('/movement/add', methods=['GET', 'POST'])
def add_movement():
    products = Product.query.all()
    locations = Location.query.all()
    if request.method == 'POST':
        mid = request.form['movement_id'].strip()
        prod = request.form['product_id']
        qty = request.form.get('qty')
        from_loc = request.form.get('from_location') or None
        to_loc = request.form.get('to_location') or None

        if not mid or not prod or not qty:
            flash('All fields are required!', 'error')
        elif not from_loc and not to_loc:
            flash("Either 'From' or 'To' location must be set!", 'error')
        else:
            try:
                qty = int(qty)
                movement = ProductMovement(
                    movement_id=mid,
                    product_id=prod,
                    qty=qty,
                    from_location=from_loc,
                    to_location=to_loc,
                    timestamp=datetime.utcnow()
                )
                db.session.add(movement)
                db.session.commit()
                flash(f"Movement '{mid}' recorded successfully.", 'success')
                return redirect(url_for('movements'))
            except ValueError:
                flash('Quantity must be a number!', 'error')
    return render_template('movement_form.html', products=products, locations=locations)

@app.route('/movement/delete/<string:movement_id>', methods=['POST'])
def delete_movement(movement_id):
    movement = ProductMovement.query.get_or_404(movement_id)
    db.session.delete(movement)
    db.session.commit()
    flash('Movement deleted successfully!', 'success')
    return redirect(url_for('movements'))

@app.route('/report')
def report():
    data = []
    for p in Product.query.all():
        for l in Location.query.all():
            qty = get_product_balance(p.product_id, l.location_id)
            if qty != 0:
                data.append({
                    'product': p.name,
                    'location': l.name,
                    'qty': qty
                })
    return render_template('report.html', balances=data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        initialize_sample_data()
    app.run(debug=True)
