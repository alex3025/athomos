import sqlalchemy as master
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from utils.config import Config


config = Config()

Base = declarative_base()
engine = master.create_engine(config.db_uri)
Session = sessionmaker(bind=engine)


class Database:
    def __init__(self):
        self.session = Session()
        Base.metadata.create_all(bind=engine)

    class Guild(Base):
        __tablename__ = 'Guilds'

        # Base
        guild_id = master.Column(master.Integer, primary_key=True, autoincrement=False)

        prefix = master.Column(master.String, default='!')
        language = master.Column(master.String, default='it_IT')

    class Admin(Base):
        __tablename__ = 'Admin'

        guild_id = master.Column(master.Integer, primary_key=True, autoincrement=False)

        join_message = master.Column(master.String, default=None)
        join_message_textChannel = master.Column(master.Integer, default=None)
        join_message_sendInDM = master.Column(master.Boolean, default=False)

        leave_message = master.Column(master.String, default=None)
        leave_message_textChannel = master.Column(master.Integer, default=None)

        welcome_roles = master.Column(master.String, default='')

    class Mod(Base):
        __tablename__ = 'Mod'

        guild_id = master.Column(master.Integer, primary_key=True, autoincrement=False)

        reports_channel = master.Column(master.Integer, default=None)

    class CustomCommands(Base):
        __tablename__ = 'Custom Commands'

        guild_id = master.Column(master.Integer, primary_key=True, autoincrement=False)

        customcommands = master.Column(master.String, default=r'{}')

    def get(self, filter_, table=Guild):
        return self.session.query(table).filter(filter_).first()
