# Copyright (c) 2020 SUSE LLC.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#

import json

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from mash.services.database.extensions import db


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    password_dirty = db.Column(db.Boolean, default=False)
    ec2_accounts = db.relationship(
        'EC2Account',
        back_populates='user',
        lazy='select',
        cascade='all, delete, delete-orphan'
    )
    gce_accounts = db.relationship(
        'GCEAccount',
        back_populates='user',
        lazy='select',
        cascade='all, delete, delete-orphan'
    )
    azure_accounts = db.relationship(
        'AzureAccount',
        back_populates='user',
        lazy='select',
        cascade='all, delete, delete-orphan'
    )
    oci_accounts = db.relationship(
        'OCIAccount',
        back_populates='user',
        lazy='select',
        cascade='all, delete, delete-orphan'
    )
    ec2_groups = db.relationship(
        'EC2Group',
        back_populates='user',
        lazy='select',
        cascade='all, delete, delete-orphan'
    )
    aliyun_accounts = db.relationship(
        'AliyunAccount',
        back_populates='user',
        lazy='select',
        cascade='all, delete, delete-orphan'
    )
    tokens = db.relationship(
        'Token',
        back_populates='user',
        lazy='select',
        cascade="all, delete, delete-orphan"
    )
    jobs = db.relationship(
        'Job',
        back_populates='user',
        lazy='select',
        cascade="all, delete, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.email)


class Token(db.Model):
    __tablename__ = 'token'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), index=True, nullable=False)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='tokens')
    expires = db.Column(db.DateTime)

    def __repr__(self):
        return '<Token {}>'.format(self.jti)


class EC2Group(db.Model):
    __tablename__ = 'ec2_group'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='ec2_groups')
    accounts = db.relationship(
        'EC2Account',
        back_populates='group'
    )
    __table_args__ = (
        db.UniqueConstraint('name', 'user_id', name='_ec2_group_user_uc'),
    )

    def __repr__(self):
        return '<EC2 Group {}>'.format(self.name)


class EC2Region(db.Model):
    __tablename__ = 'ec2_region'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    helper_image = db.Column(db.String(32), nullable=False)
    account_id = db.Column(
        db.Integer,
        db.ForeignKey('ec2_account.id'),
        nullable=False
    )
    account = db.relationship('EC2Account', back_populates='additional_regions')

    def __repr__(self):
        return '<EC2 Region {}>'.format(self.name)


class EC2Account(db.Model):
    __tablename__ = 'ec2_account'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    partition = db.Column(db.String(10), nullable=False)
    region = db.Column(db.String(32), nullable=False)
    subnet = db.Column(db.String(32))
    additional_regions = db.relationship(
        'EC2Region',
        back_populates='account',
        lazy='select',
        cascade="all, delete, delete-orphan"
    )
    group_id = db.Column(db.Integer, db.ForeignKey('ec2_group.id'))
    group = db.relationship('EC2Group', back_populates='accounts')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='ec2_accounts')
    __table_args__ = (
        db.UniqueConstraint('name', 'user_id', name='_ec2_account_user_uc'),
    )

    def __repr__(self):
        return '<EC2 Account {}>'.format(self.name)


class GCEAccount(db.Model):
    __tablename__ = 'gce_account'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    bucket = db.Column(db.String(222), nullable=False)
    region = db.Column(db.String(32), nullable=False)
    testing_account = db.Column(db.String(64))
    is_publishing_account = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='gce_accounts')
    __table_args__ = (
        db.UniqueConstraint('name', 'user_id', name='_gce_account_user_uc'),
    )

    def __repr__(self):
        return '<GCE Account {}>'.format(self.name)


class AzureAccount(db.Model):
    __tablename__ = 'azure_account'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    region = db.Column(db.String(32), nullable=False)
    source_container = db.Column(db.String(64), nullable=False)
    source_resource_group = db.Column(db.String(90), nullable=False)
    source_storage_account = db.Column(db.String(24), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='azure_accounts')
    __table_args__ = (
        db.UniqueConstraint('name', 'user_id', name='_azure_account_user_uc'),
    )

    def __repr__(self):
        return '<Azure Account {}>'.format(self.name)


class OCIAccount(db.Model):
    __tablename__ = 'oci_account'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    region = db.Column(db.String(32), nullable=False)
    availability_domain = db.Column(db.String(32), nullable=False)
    compartment_id = db.Column(db.String(255), nullable=False)
    oci_user_id = db.Column(db.String(255), nullable=False)
    tenancy = db.Column(db.String(255), nullable=False)
    bucket = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='oci_accounts')
    __table_args__ = (
        db.UniqueConstraint('name', 'user_id', name='_oci_account_user_uc'),
    )

    def __repr__(self):
        return '<OCI Account {}>'.format(self.name)


class AliyunAccount(db.Model):
    __tablename__ = 'aliyun_account'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    region = db.Column(db.String(32), nullable=False)
    security_group_id = db.Column(db.String(255))
    vswitch_id = db.Column(db.String(255))
    bucket = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='aliyun_accounts')
    __table_args__ = (
        db.UniqueConstraint('name', 'user_id', name='_aliyun_account_user_uc'),
    )

    def __repr__(self):
        return '<Aliyun Account {}>'.format(self.name)


class Job(db.Model):
    __tablename__ = 'job'
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(40), nullable=False)
    last_service = db.Column(db.String(16), nullable=False)
    current_service = db.Column(db.String(16))
    prev_service = db.Column(db.String(16))
    failed_service = db.Column(db.String(16))
    utctime = db.Column(db.String(32), nullable=False)
    image = db.Column(db.String(128), nullable=False)
    download_url = db.Column(db.String(256), nullable=False)
    cloud_architecture = db.Column(db.String(8), default='x86_64')
    profile = db.Column(db.String(32))
    state = db.Column(db.String(12))
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    finish_time = db.Column(db.DateTime)
    _errors = db.Column('errors', db.Text)
    _data = db.Column('data', db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='jobs')

    @property
    def data(self):
        return json.loads(self._data) if self._data else None

    @data.setter
    def data(self, value):
        self._data = json.dumps(value)

    @property
    def errors(self):
        return self._errors.split('|') if self._errors else []

    @errors.setter
    def errors(self, value):
        self._errors = '|'.join(value) if value else ''

    def __repr__(self):
        return '<Job {}>'.format(self.job_id)
