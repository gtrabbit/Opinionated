#!/usr/bin/env python3

from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
import random
import string
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import(
    TimedJSONWebSignatureSerializer as Serializer,
    BadSignature, SignatureExpired)

Base = declarative_base()

secret_key = ''.join(
  random.choice(
    string.ascii_uppercase + string.digits) for x in range(32))


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    created_by = Column(Integer, ForeignKey('user.id'))

    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
           'name': self.name,
           'id': self.id,
           'created_by': self.created_by
        }


class Item(Base):
    __tablename__ = 'item'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('category.id'))
    description = Column(String(250))
    created_by = Column(Integer, ForeignKey('user.id'))

    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
           'name': self.name,
           'description': self.description,
           'id': self.id,
           'category_id': self.category_id,
           'created_by': self.created_by,
        }


class Vote(Base):
    __tablename__ = 'vote'

    id = Column(Integer, primary_key=True)
    voter = Column(Integer, ForeignKey('user.id'))
    votee = Column(Integer, ForeignKey('user.id'))
    item = Column(Integer, ForeignKey('item.id'))
    up_or_down = Column(Boolean)

    def serialize(self):
        return {
            'id': self.id,
            'voter': self.voter,
            'item id': self.item,
            'item created by': self.votee,
            'Up vote': self.up_or_down
        }


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), nullable=False)
    email = Column(String(80))
    about = Column(Text)
    picture = Column(String(250))

    def generate_auth_token(self, expiration=600):
        s = Serializer(secret_key, expires_in=expiration)
        return s.dumps({'id': self.id})

    def serialize(self):
        return {
            'username': self.username,
            'about': self.about,
            'id': self.id,
            'email': self.email,
            'picture': self.picture
        }

engine = create_engine('postgresql://user:psswd@localhost/opinionated')


Base.metadata.create_all(engine)
