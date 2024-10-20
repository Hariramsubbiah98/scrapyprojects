from sqlalchemy import create_engine, Column, String, Integer, Table, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    title = Column(String)
    product_id = Column(String)
    sku = Column(String)
    gtin = Column(String)

def db_connect():
    return create_engine('sqlite:///products.db')

def create_table(engine):
    Base.metadata.create_all(engine)
