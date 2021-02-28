from utils import pretty_product_dict
from config import config_dict
from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from flask_cors import CORS

from wtforms import SelectField
from datamanager import DataManager, Product


class Form(FlaskForm):
    """
    The form to select / change the currently displayed category
    """
    category = SelectField("category", choices=[(cat, cat) for cat in config_dict["categories"]])


app = Flask(__name__)

# for CSRF protection, not necessary in our use-case
app.config['SECRET_KEY'] = 'secret'

# TODO: Remove when done debugging (prevents caching of .html and .css files)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
CORS(app)


data_manager = DataManager(config_dict["update_interval"])
data_manager.start()


@app.route('/', methods=['GET', 'POST'])
def index():

    form = Form()
    if request.method == "POST":
        selected_category = form.category.data
    else:
        selected_category = config_dict["categories"][0]

    session = data_manager.Session()

    products = session \
        .query(Product) \
        .filter(Product.category == selected_category) \
        .order_by(Product.name) \
        .all()

    products = [pretty_product_dict(product) for product in products]
    data_manager.Session.remove()

    return render_template('index.html',
                           form=form,
                           products=products,
                           categories=config_dict["categories"],
                           selected_category=selected_category,
                           is_data_available=len(products) > 0)


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
