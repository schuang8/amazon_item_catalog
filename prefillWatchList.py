from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from database_setup import WatchList, Base, Item, User

engine = create_engine('sqlite:///watchlistwithusers.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = scoped_session(sessionmaker(bind=engine))


# Create dummy user
User1 = User(name="Robo Barista",
             email="tinnyTim@udacity.com",
             picture=("https://pbs.twimg.com/profile_images/"
                      "2671170543/18debd694829ed78203a5a36dd364160_"
                      "400x400.png"))
session.add(User1)
session.commit()

watch_list1 = WatchList(user_id=1, name="Amazon Prime List #1")
session.add(watch_list1)
session.commit()

item2 = Item(user_id=1,
             name="Kelty Low Loveseat Chair",
             url=("https://www.amazon.com/gp/product/"
                  "B012EVR3MA/ref=ox_sc_sfl_title_1?"
                  "ie=UTF8&psc=1&smid=ATVPDKIKX0DER"),
             price="99.95",
             discount="0.00",
             category="Sports & Outdoors",
             in_stock="yes",
             watch_list=watch_list1)
session.add(item2)
session.commit()

item1 = Item(user_id=1,
             name="Alienware 25 Gaming Monitor - AW2518Hf",
             url=("https://www.amazon.com/gp/product/"
                  "B0733YCKM5/ref=ox_sc_sfl_title_2?"
                  "ie=UTF8&psc=1&smid=ATVPDKIKX0DER"),
             price="313.49",
             discount="186.50",
             category="Electronics",
             watch_list=watch_list1)
session.add(item1)
session.commit()

print ("added watch list items!")
