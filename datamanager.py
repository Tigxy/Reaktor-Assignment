from config import config_dict
from enums import UpdateResult
from utils import Availability, get_category, get_manufacturer, split_sized_chunks

import os
import sys
import time
import logging
import threading

import sqlalchemy
from sqlalchemy import Column, String, Integer, create_engine, DateTime
from sqlalchemy.sql import case
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool

# Get logger for this module and configure it
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# Prevent logger from passing on messages
logger.propagate = False
formatter = logging.Formatter("%(asctime)-15s %(name)s: %(message)s")
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Following the tutorial from https://docs.sqlalchemy.org/en/14/orm/tutorial.html
Base = declarative_base()


class Product(Base):
    __tablename__ = 'product'
    id = Column(String(48), primary_key=True)
    name = Column(String(128), nullable=False)
    price = Column(Integer, nullable=False)
    colors = Column(String(512), nullable=False)
    category = Column(String(128), nullable=False)
    manufacturer = Column(String(128), nullable=False)
    available = Column(Integer, default=Availability.UNKNOWN.value)

    def __repr__(self):
        return f"<Product {self.id} {self.available}>"


# Dictionary that contains which column matches which entry in the result of the
# API category request. Only stated columns will be updated in an category update.
COLUMNS_KEY_DICT = {
    Product.name: "name",
    Product.colors: "color",
    Product.manufacturer: "manufacturer",
    Product.price: "price",
}


def dict_to_product(category, data_dict):
    return Product(category=category,
                   id=data_dict["id"],
                   name=data_dict["name"],
                   colors=data_dict["color"],
                   price=data_dict["price"],
                   manufacturer=data_dict["manufacturer"]
                   )


def generate_product_db():
    # Need to use a file based database as we want to access the data from multiple threads
    engine = create_engine("sqlite:///products.db",
                           connect_args={'check_same_thread': False},
                           # StaticPool required for memory databases
                           # see https://stackoverflow.com/a/61085725
                           poolclass=StaticPool)

    Product.__table__.create(bind=engine, checkfirst=True)
    Session = scoped_session(sessionmaker(bind=engine))
    return engine, Session


class DataManager:
    def __init__(self, update_interval, change_callback=None, add_remove_callback=None, perform_update=False):
        self.update_interval = update_interval
        self._change_callback = change_callback
        self._add_remove_callback = add_remove_callback
        self.__t = None

        logger.debug("Init - Setting up database")
        self.engine, self.Session = generate_product_db()

        if perform_update:
            session = self.Session()
            self.run_update_cycle(session)
            self.Session.remove()

        logger.debug("Init - Done")

    @property
    def is_running(self):
        return self.__t is not None and self.__t.is_alive()

    def start(self):
        if not self.is_running:
            self.__t = threading.Thread(target=self.run)
            self.__t.start()

    def run(self):
        while True:
            # Create session local to current thread
            session = self.Session()

            # Track when update cycle was started
            start = time.time()

            logger.debug("Update process - Update cycle start")
            self.run_update_cycle(session)
            end = time.time()
            logger.debug(f"Update process - Update cycle done, took {end - start} seconds")

            # Sleep the rest of the remaining time
            time.sleep(max(0, self.update_interval - (end - start)))

            # End session
            self.Session.remove()

    def run_update_cycle(self, session):
        logger.debug("Update process - Updating categories")

        added_removed = False
        categories_to_update = config_dict["categories"]

        # Update categories until all have been updated successfully
        while True:
            cat_results = self.update_all_categories(session, categories_to_update)
            added_removed |= any([r == UpdateResult.ADDED_REMOVED for _, r in cat_results.items()])
            failed_updates = [cat for cat, r in cat_results.items() if r == UpdateResult.FAILURE]
            if len(failed_updates) == 0:
                break
            categories_to_update = failed_updates
            logger.debug(f"Update process - Retrieving data failed for categories {', '.join(categories_to_update)}")
            time.sleep(config_dict["api_call_delay_on_failure"])

        logger.debug("Update process - Updating manufacturers")
        # Update availability info until all have been updated successfully
        manufacturers_to_update = None
        while True:
            update_failures = self.update_all_available(session, manufacturers_to_update)
            if len(update_failures) == 0:
                break
            manufacturers_to_update = update_failures
            logger.debug(
                f"Update process - Retrieving data failed for manufacturer(s) {', '.join(manufacturers_to_update)}")
            time.sleep(config_dict["api_call_delay_on_failure"])

        # Send notifications that data has changed
        if added_removed and self._add_remove_callback is not None:
            self._add_remove_callback()
        if self._change_callback is not None:
            self._change_callback()

    @staticmethod
    def build_update_resource_dict(columns_key_dict, ids_to_consider, id_product_data_dict):
        return {k: {i: data[v] for i, data in id_product_data_dict.items() if i in ids_to_consider}
                for k, v in columns_key_dict.items()}

    def update_category(self, session, category_name):
        """
        Updates the items in our database which are in the category 'category_name'
        :param session: The session to use when retrieving / storing data
        :param category_name: The category name to update products for
        :return: the result of what kind of information was changed
        """
        # Retrieve data
        category_items = get_category(category_name)
        item_ids = list(category_items.keys())

        # Determine if successful
        if category_items is None:
            return UpdateResult.FAILURE

        previous_ids = [i for i, in session.query(Product.id).filter(Product.category == category_name).all()]

        # Determine which products were removed, updated or added
        removed_ids = list(set(previous_ids) - set(item_ids))
        added_ids = list(set(item_ids) - set(previous_ids))
        updated_ids = list(set(previous_ids).intersection(set(item_ids)))

        # Remove the products that are no longer in use
        for split in split_sized_chunks(removed_ids, config_dict["max_items_db_call"]):
            session.query(Product).filter(Product.id.in_(split)).delete(synchronize_session=False)
            session.commit()

        # Udpate properties of currently in use products
        for split in split_sized_chunks(updated_ids, config_dict["max_items_db_call"]):
            self.update_with_dict(session,
                                  id_value_dict=self.build_update_resource_dict(columns_key_dict=COLUMNS_KEY_DICT,
                                                                                ids_to_consider=split,
                                                                                id_product_data_dict=category_items),
                                  ids_to_consider=split)
            session.commit()

        # Add new products
        for split in split_sized_chunks(added_ids, config_dict["max_items_db_call"]):
            session.add_all([dict_to_product(category_name, category_items[i]) for i in split])
            session.commit()

        # We already have set of indices, therefore we can just subtract one from the other
        were_items_added = len(added_ids) > 0
        were_items_removed = len(removed_ids) > 0

        # We want to keep track on what has changed for each category.
        # With this, we can either update the displayed content automatically or notify user that products have changed
        return UpdateResult.ADDED_REMOVED if were_items_added or were_items_removed else UpdateResult.CHANGED

    def update_all_categories(self, session, categories_to_update):
        """
        Updates the information of all database entries
        :param session: The session to use when retrieving / storing data
        :param categories_to_update: A list of categories that should be updated
        :return: the result of each of the categories
        """
        results = dict()
        for category in categories_to_update:
            update_result = self.update_category(session, category)
            results[category] = update_result

        return results

    def update_available(self, session, manufacturer_name):
        """
        Updates the availability status of the products of a single manufacturer
        :param session: The session to use when retrieving / storing data
        :param manufacturer_name: The manufacturer to get the available information from
        :return: the result of what kind of information was changed
        """
        # Retrieve data
        manufacturer_data = get_manufacturer(manufacturer_name)

        # Determine if successful
        if manufacturer_data is None:
            return UpdateResult.FAILURE

        # Some items from the manufacturer might not be listed as a product, select only listed ones
        all_ids = [i for i, in session.query(Product.id).all()]

        contained_ids = [k for k in manufacturer_data.keys() if k in all_ids]

        # Database cannot handle all changes at once, therefore split them up
        for split in split_sized_chunks(contained_ids, config_dict["max_items_db_call"]):
            split_manufacturer_data = {k: v.value for k, v in manufacturer_data.items() if k in split}
            self.update_available_with_dict(session, split_manufacturer_data, split)
            session.commit()

        return UpdateResult.CHANGED

    def update_all_available(self, session, manufacturers=None):
        """
        Updates the availability information of all database entries
        :param session: The session to use when retrieving / storing data
        :param manufacturers: (optional) a list of manufacturers for which items should be updated
        :return: a list of manufacturers for which the availability update failed
        """
        if manufacturers is None:
            manufacturers = {man for man, in session.query(Product.manufacturer).distinct()}

        failed_updates = list()
        for manufacturer in manufacturers:
            if self.update_available(session, manufacturer) == UpdateResult.FAILURE:
                failed_updates.append(manufacturer)

        return failed_updates

    @staticmethod
    def update_with_dict(session, id_value_dict, ids_to_consider):
        if sqlalchemy.__version__.startswith("1.4"):
            # sqlalchemy has changed api for update call (at least in beta version) and now
            # requires a list of tuples, might be worth looking up changes in detail
            id_value_dict = {k: list(v.items()) for k, v in id_value_dict.items()}

        session.query(Product) \
            .filter(Product.id.in_(ids_to_consider)) \
            .update({
            value_type: case(value_dict, value=Product.id) for value_type, value_dict in id_value_dict.items()}
            , synchronize_session=False)

    @staticmethod
    def update_available_with_dict(session, id_available_dict, ids_to_consider):
        if sqlalchemy.__version__.startswith("1.4"):
            # sqlalchemy has changed api for update call (at least in beta version) and now
            # requires a list of tuples, might be worth looking up changes in detail
            id_available_dict = list(id_available_dict.items())

        session.query(Product) \
            .filter(Product.id.in_(ids_to_consider)) \
            .update({
            Product.available: case(
                id_available_dict,
                value=Product.id
            )
        }, synchronize_session=False)
