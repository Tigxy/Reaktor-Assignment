from config import categories
from utils import Availability, get_category, get_manufacturer, split_sized_chunks
from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import case


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# TODO: Remove when done debugging
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SECRET_KEY'] = 'secret'


class Product(db.Model):
    id = db.Column(db.String(48), primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    price = db.Column(db.INT, nullable=False)
    colors = db.Column(db.String(512), nullable=False)
    category = db.Column(db.String(128), nullable=False)
    manufacturer = db.Column(db.String(128), nullable=False)
    available = db.Column(db.String(20))

    def __repr__(self):
        return f"<Product {self.id}, {self.available}>"


# ======================================================
# Database has to be created after class 'Product' is created,
# otherwise the corresponding table will not be created
db.create_all()

db.session.add(
    Product(id="test_id", name="Shoe", price=89, colors="red, green", category="boots", manufacturer="adidas",
            available=""))

db.session.add(
    Product(id="other_test", name="Laces", price=98, colors="red, green", category="boots", manufacturer="adidas",
            available=""))


print("added")
db.session.commit()
print("committed")


available_dict = {"test_id": "less than", "other_test": "more than"}
# all_rows = Product.query.filter(Product.id.in_(available_dict))
#
# for row in all_rows:
#     row.available = available_dict[row.id]

# all_ids = [i for i, in db.session.query(Product.id).all()]
# contained_ids = [k for k, _ in available_dict.items() if k in all_ids]
#
# for split in split_sized_chunks(contained_ids, 200):
#     split_manufacturer_data = {k: v for k, v in available_dict.items() if k in split}
#     all_rows = Product.query.filter(Product.id.in_(split))
#     all_rows.update({
#         Product.colors: case(
#             split_manufacturer_data,
#             value=Product.id
#         )
#     }, synchronize_session=False)


print("done")

# # Changed items
# changed_ids = [i for i in category_items.keys() if i in previous_ids]
# for split in split_sized_chunks(changed_ids, max_op):
#     split_category_items = defaultdict(lambda: dict())
#     for k, v in category_items.items():
#         for k1, v1 in v.items():
#             split_category_items[k1][k] = v1
#
#     all_rows = Product.query \
#         .filter(Product.id.in_(split))
#     all_rows.update({
#         Product.available: case(
#             split_category_items["available"],
#             value=Product.id
#         ),
#
#         Product.colors: case(
#             split_category_items["manufacturer"],
#             value=Product.id
#         ),
#
#         Product.price: case(
#             split_category_items["price"],
#             value=Product.id
#         ),
#
#     }, synchronize_session=False)