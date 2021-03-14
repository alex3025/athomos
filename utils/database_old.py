import sqlalchemy as master
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from utils.config import Config
from utils.logger import Logger

config = Config()
log = Logger()

Base = declarative_base()
engine = master.create_engine(config.db_uri)
Session = sessionmaker(bind=engine)


class Database:

    def __init__(self):
        self.session = Session()
        Base.metadata.create_all(bind=engine)

    class Guilds(Base):
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

        customcommands = master.Column(master.String, default='[]')
    

    def get(self, filter_, table=Guilds):
        return self.session.query(table).filter(filter_).first()


    def createTables(self, guild):
        # self.session.add(self.db.Guild(guild_id=guild.id, language=guild.preferred_locale.replace('-', '_') if guild.preferred_locale.replace('-', '_') + '.json' in os.listdir('config/i18n/') else 'en_EN'))
        self.session.add(self.Guilds(guild_id=guild.id))
        self.session.add(self.Admin(guild_id=guild.id))
        self.session.add(self.Mod(guild_id=guild.id))
        self.session.add(self.CustomCommands(guild_id=guild.id))

        self.session.commit()
        log.debug('Added new guild to the database.')

    def deleteTables(self, guild):
        try:
            self.session.delete(self.get(self.Guilds.guild_id == guild.id))
            self.session.delete(self.get(self.Admin.guild_id == guild.id, self.Admin))
            self.session.delete(self.get(self.Mod.guild_id == guild.id, self.Mod))
            self.session.delete(self.get(self.CustomCommands.guild_id == guild.id, self.CustomCommands))

            self.session.commit()
            log.debug('Removed a guild from the database.')
        except master.orm.exc.UnmappedInstanceError:
            pass


    def checkDatabase(self, bot):
        log.debug('Checking database for sync errors...')

        firstCase = False
        secondCase = False
        for table in Base.__subclasses__():
            for tableElement in self.session.query(table).all():
                dbGuild = self.get(table.guild_id == tableElement.guild_id, table)
                if dbGuild is None:
                    for guild in bot.guilds:
                        if guild.id == tableElement.guild_id:
                            self.session.add(table(guild_id=guild.id))
                            firstCase = True
                else:
                    if not dbGuild.guild_id == tableElement.guild_id:
                        self.session.delete(self.get(table.guild_id == dbGuild.guild_id, table))
                        secondCase = True

            if firstCase:
                log.info('Missing guild added to the database.')
            if secondCase:
                log.info('Ghost guild removed from the database.')

        log.debug('Database checked.')
