"""Начальная схема БД: пользователи, медиа, курсы, вопросы, варианты, попытки, ответы.

Revision ID: 0001
Revises:
Create Date: 2026-11-25 00:16:13.682176
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pg_trgm нужен для быстрого поиска по подстроке (GIN-индексы *_trgm)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table('users',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('role', sa.String(length=20), server_default='user', nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("role IN ('user', 'creator', 'admin')", name=op.f('ck_users_role_valid')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index('ix_users_email_trgm', 'users', ['email'], unique=False, postgresql_using='gin', postgresql_ops={'email': 'gin_trgm_ops'})
    op.create_index('ix_users_full_name_trgm', 'users', ['full_name'], unique=False, postgresql_using='gin', postgresql_ops={'full_name': 'gin_trgm_ops'})
    op.create_index('ix_users_role', 'users', ['role'], unique=False)
    op.create_index('uq_users_email_lower', 'users', [sa.literal_column('lower(email)')], unique=True)
    op.create_table('media',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('content_type', sa.String(length=100), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('storage_path', sa.String(length=500), nullable=False),
    sa.Column('uploaded_by', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('image', 'audio')", name=op.f('ck_media_kind_valid')),
    sa.CheckConstraint('size_bytes > 0', name=op.f('ck_media_size_positive')),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], name=op.f('fk_media_uploaded_by_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_media')),
    sa.UniqueConstraint('storage_path', name=op.f('uq_media_storage_path'))
    )
    op.create_table('courses',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('author_id', sa.BigInteger(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), server_default='', nullable=False),
    sa.Column('cover_media_id', sa.UUID(), nullable=True),
    sa.Column('is_published', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_courses_author_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['cover_media_id'], ['media.id'], name=op.f('fk_courses_cover_media_id_media'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_courses'))
    )
    op.create_index('ix_courses_author_id', 'courses', ['author_id'], unique=False)
    op.create_index('ix_courses_description_trgm', 'courses', ['description'], unique=False, postgresql_using='gin', postgresql_ops={'description': 'gin_trgm_ops'})
    op.create_index('ix_courses_published_created', 'courses', ['created_at'], unique=False, postgresql_where=sa.text('is_published'))
    op.create_index('ix_courses_title_trgm', 'courses', ['title'], unique=False, postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'})
    op.create_table('attempts',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('course_id', sa.BigInteger(), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='in_progress', nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('total_questions', sa.Integer(), nullable=False),
    sa.Column('score', sa.Integer(), nullable=True),
    sa.CheckConstraint("(status = 'in_progress' AND finished_at IS NULL AND score IS NULL) OR (status = 'finished' AND finished_at IS NOT NULL AND score IS NOT NULL)", name=op.f('ck_attempts_finished_consistent')),
    sa.CheckConstraint("status IN ('in_progress', 'finished')", name=op.f('ck_attempts_status_valid')),
    sa.CheckConstraint('score IS NULL OR (score >= 0 AND score <= total_questions)', name=op.f('ck_attempts_score_range')),
    sa.CheckConstraint('total_questions >= 1', name=op.f('ck_attempts_total_positive')),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_attempts_course_id_courses'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_attempts_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attempts'))
    )
    op.create_index('ix_attempts_course_id', 'attempts', ['course_id'], unique=False)
    op.create_index('ix_attempts_user_started', 'attempts', ['user_id', sa.literal_column('started_at DESC')], unique=False)
    op.create_table('questions',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('course_id', sa.BigInteger(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('text', sa.String(length=1000), nullable=False),
    sa.Column('image_media_id', sa.UUID(), nullable=True),
    sa.Column('audio_media_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('position >= 1', name=op.f('ck_questions_position_positive')),
    sa.ForeignKeyConstraint(['audio_media_id'], ['media.id'], name=op.f('fk_questions_audio_media_id_media'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_questions_course_id_courses'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['image_media_id'], ['media.id'], name=op.f('fk_questions_image_media_id_media'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_questions')),
    sa.UniqueConstraint('course_id', 'position', deferrable=True, initially='DEFERRED', name='uq_questions_course_position')
    )
    op.create_table('answer_options',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('question_id', sa.BigInteger(), nullable=False),
    sa.Column('position', sa.SmallInteger(), nullable=False),
    sa.Column('text', sa.String(length=300), nullable=False),
    sa.Column('is_correct', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint('position BETWEEN 1 AND 4', name=op.f('ck_answer_options_position_range')),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], name=op.f('fk_answer_options_question_id_questions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_answer_options')),
    sa.UniqueConstraint('id', 'question_id', name='uq_answer_options_id_question'),
    sa.UniqueConstraint('question_id', 'position', name='uq_answer_options_question_position')
    )
    op.create_index('uq_answer_options_one_correct', 'answer_options', ['question_id'], unique=True, postgresql_where=sa.text('is_correct'))
    op.create_table('attempt_answers',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('attempt_id', sa.BigInteger(), nullable=False),
    sa.Column('question_id', sa.BigInteger(), nullable=False),
    sa.Column('option_id', sa.BigInteger(), nullable=False),
    sa.Column('answered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['attempt_id'], ['attempts.id'], name=op.f('fk_attempt_answers_attempt_id_attempts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['option_id', 'question_id'], ['answer_options.id', 'answer_options.question_id'], name='fk_attempt_answers_option_question', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], name=op.f('fk_attempt_answers_question_id_questions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attempt_answers')),
    sa.UniqueConstraint('attempt_id', 'question_id', name='uq_attempt_answers_attempt_question')
    )
    op.create_index('ix_attempt_answers_question_id', 'attempt_answers', ['question_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_attempt_answers_question_id', table_name='attempt_answers')
    op.drop_table('attempt_answers')
    op.drop_index('uq_answer_options_one_correct', table_name='answer_options', postgresql_where=sa.text('is_correct'))
    op.drop_table('answer_options')
    op.drop_table('questions')
    op.drop_index('ix_attempts_user_started', table_name='attempts')
    op.drop_index('ix_attempts_course_id', table_name='attempts')
    op.drop_table('attempts')
    op.drop_index('ix_courses_title_trgm', table_name='courses', postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'})
    op.drop_index('ix_courses_published_created', table_name='courses', postgresql_where=sa.text('is_published'))
    op.drop_index('ix_courses_description_trgm', table_name='courses', postgresql_using='gin', postgresql_ops={'description': 'gin_trgm_ops'})
    op.drop_index('ix_courses_author_id', table_name='courses')
    op.drop_table('courses')
    op.drop_table('media')
    op.drop_index('uq_users_email_lower', table_name='users')
    op.drop_index('ix_users_role', table_name='users')
    op.drop_index('ix_users_full_name_trgm', table_name='users', postgresql_using='gin', postgresql_ops={'full_name': 'gin_trgm_ops'})
    op.drop_index('ix_users_email_trgm', table_name='users', postgresql_using='gin', postgresql_ops={'email': 'gin_trgm_ops'})
    op.drop_table('users')
