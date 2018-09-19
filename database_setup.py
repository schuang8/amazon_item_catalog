from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


class WatchList(Base):
    __tablename__ = 'watch_list'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'list_name': self.list_name,
            'id': self.id,
        }


class Item(Base):
    __tablename__ = 'item'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    url = Column(String(250))
    price = Column(String(8))
    discount = Column(String(8))
    category = Column(String(250))
    in_stock = Column(String(3))
    watch_list_id = Column(Integer, ForeignKey('watch_list.id'))
    watch_list = relationship(WatchList)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
            'url': self.url,
            'price': self.price,
            'discount': self.discount,
            'category': self.category,
            'in_stock': self.in_stock
        }


engine = create_engine('sqlite:///watchlistwithusers.db')
Base.metadata.create_all(engine)
