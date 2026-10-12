"""Initial SQLite schema snapshot."""
from alembic import op
revision="001"
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    op.execute('\nCREATE TABLE audit (\n\tid VARCHAR(32) NOT NULL, \n\tactor VARCHAR(32) NOT NULL, \n\taction VARCHAR(100) NOT NULL, \n\ttarget VARCHAR(32) NOT NULL, \n\treason VARCHAR(1000) NOT NULL, \n\tcreated_at VARCHAR NOT NULL, \n\tPRIMARY KEY (id)\n)\n\n')
    op.execute('\nCREATE TABLE users (\n\tid VARCHAR(32) NOT NULL, \n\tnickname VARCHAR(32) NOT NULL, \n\tnickname_key VARCHAR(32) NOT NULL, \n\tpassword_hash TEXT NOT NULL, \n\tbio VARCHAR(600) NOT NULL, \n\tavatar VARCHAR(100) NOT NULL, \n\tadmin BOOLEAN NOT NULL, \n\tcreated_at VARCHAR NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (nickname), \n\tUNIQUE (nickname_key)\n)\n\n')
    op.execute('\nCREATE TABLE games (\n\tid VARCHAR(32) NOT NULL, \n\towner_id VARCHAR(32) NOT NULL, \n\ttitle_ru VARCHAR(100) NOT NULL, \n\ttitle_en VARCHAR(100) NOT NULL, \n\tdescription_ru TEXT NOT NULL, \n\tdescription_en TEXT NOT NULL, \n\tgenres TEXT NOT NULL, \n\ttags TEXT NOT NULL, \n\tplatforms TEXT NOT NULL, \n\tcontrols_ru VARCHAR(600) NOT NULL, \n\tcontrols_en VARCHAR(600) NOT NULL, \n\tmultiplayer BOOLEAN NOT NULL, \n\tdemo BOOLEAN NOT NULL, \n\tblocked BOOLEAN NOT NULL, \n\tcurrent_version VARCHAR(32), \n\ticon VARCHAR(100) NOT NULL, \n\tscreenshots TEXT NOT NULL, \n\tplays INTEGER NOT NULL, \n\tcreated_at VARCHAR NOT NULL, \n\tupdated_at VARCHAR NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(owner_id) REFERENCES users (id)\n)\n\n')
    op.execute('\nCREATE TABLE sessions (\n\tdigest VARCHAR(64) NOT NULL, \n\tuser_id VARCHAR(32) NOT NULL, \n\texpires INTEGER NOT NULL, \n\tPRIMARY KEY (digest), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)\n\n')
    op.execute('\nCREATE TABLE favorites (\n\tuser_id VARCHAR(32) NOT NULL, \n\tgame_id VARCHAR(32) NOT NULL, \n\tPRIMARY KEY (user_id, game_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tFOREIGN KEY(game_id) REFERENCES games (id)\n)\n\n')
    op.execute('\nCREATE TABLE play_sessions (\n\tid VARCHAR(64) NOT NULL, \n\tuser_id VARCHAR(32) NOT NULL, \n\tgame_id VARCHAR(32) NOT NULL, \n\texpires INTEGER NOT NULL, \n\tused BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tFOREIGN KEY(game_id) REFERENCES games (id)\n)\n\n')
    op.execute('\nCREATE TABLE ratings (\n\tuser_id VARCHAR(32) NOT NULL, \n\tgame_id VARCHAR(32) NOT NULL, \n\tvalue INTEGER NOT NULL, \n\tPRIMARY KEY (user_id, game_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tFOREIGN KEY(game_id) REFERENCES games (id)\n)\n\n')
    op.execute('\nCREATE TABLE scores (\n\tid VARCHAR(32) NOT NULL, \n\tuser_id VARCHAR(32) NOT NULL, \n\tgame_id VARCHAR(32) NOT NULL, \n\tvalue INTEGER NOT NULL, \n\tverified BOOLEAN NOT NULL, \n\tcreated_at VARCHAR NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tFOREIGN KEY(game_id) REFERENCES games (id)\n)\n\n')
    op.execute('\nCREATE TABLE versions (\n\tid VARCHAR(32) NOT NULL, \n\tgame_id VARCHAR(32) NOT NULL, \n\tlabel VARCHAR(40) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\treason TEXT NOT NULL, \n\tentry VARCHAR(300) NOT NULL, \n\tcreated_at VARCHAR NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (game_id, label), \n\tFOREIGN KEY(game_id) REFERENCES games (id)\n)\n\n')
    op.execute('\nCREATE TABLE files (\n\tid VARCHAR(32) NOT NULL, \n\tversion_id VARCHAR(32) NOT NULL, \n\tpath VARCHAR(300) NOT NULL, \n\tsize INTEGER NOT NULL, \n\tsha256 VARCHAR(64) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(version_id) REFERENCES versions (id)\n)\n\n')
    op.execute('\nCREATE TABLE moderation (\n\tid VARCHAR(32) NOT NULL, \n\tversion_id VARCHAR(32) NOT NULL, \n\tdecision VARCHAR(20) NOT NULL, \n\treason TEXT NOT NULL, \n\tcreated_at VARCHAR NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(version_id) REFERENCES versions (id)\n)\n\n')
def downgrade():
    op.drop_table('moderation')
    op.drop_table('files')
    op.drop_table('versions')
    op.drop_table('scores')
    op.drop_table('ratings')
    op.drop_table('play_sessions')
    op.drop_table('favorites')
    op.drop_table('sessions')
    op.drop_table('games')
    op.drop_table('users')
    op.drop_table('audit')
