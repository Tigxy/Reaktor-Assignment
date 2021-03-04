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

# secret for CSRF protection, not necessary in our use-case
app.config['SECRET_KEY'] = 'secret'
CORS(app)

data_loaded = False


def db_changed():
    global data_loaded
    data_loaded = True


data_manager = DataManager(config_dict["update_interval"], change_callback=db_changed)
data_manager.start()


@app.route('/', methods=['GET', 'POST'])
def index():

    global data_loaded
    if not data_loaded:
        return render_template('loading.html')

    form = Form()
    if request.method == "POST":
        selected_category = form.category.data
    else:
        selected_category = config_dict["categories"][0]

    # Get a new session
    session = data_manager.Session()

    # Select products to display
    products = session \
        .query(Product) \
        .filter(Product.category == selected_category) \
        .order_by(Product.name) \
        .all()

    # Cleanup products to make them presentable
    products = [pretty_product_dict(product) for product in products]

    # Close session
    data_manager.Session.remove()

    return render_template('index.html',
                           form=form,
                           products=products,
                           categories=config_dict["categories"],
                           selected_category=selected_category)


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
