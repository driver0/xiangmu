#!/usr/bin/env python2
#-*- coding:utf-8 -*-

from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash,check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app,request,url_for
from flask_login import UserMixin,AnonymousUserMixin
from . import db,login_manager

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(64),unique=True)
    default = db.Column(db.Boolean,default=False,index=True)
    users = db.relationship('User',backref='role',lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User': True, 
            'Administrator': False
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.default = roles[r]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' %self.name


class User(UserMixin,db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(64),unique=True,index=True)
    username = db.Column(db.String(64),unique=True,index=True)
    # role_id 这个外键建立起了 User 模型和 Role 模型的联系
    role_id = db.Column(db.Integer,db.ForeignKey('roles.id'))
    # 要保证数据库中用户密码的安全，不存储密码本身，而是存储密码的散列值
    # Werkzeug 中的 security 模块能够很方便地实现密码散列值的计算和验证。
    # 注册用户时，generate_password_hash(password) 将原始密码作为输入，以字符串形式输出密码的散列值
    # 验证用户时，check_password_hash(hash, password) hash是从数据库中取回的密码散列值，password 是用户输入的密码，
    # 对两者进行比对，密码正确返回 True，密码错误返回 False
    password_hash =db.Column(db.String(128))
    confirmed = db.Column(db.Boolean,default=False)
    last_login = db.Column(db.DateTime, default=datetime.utcnow())
    last_logout = db.Column(db.DateTime, default=datetime.utcnow())

    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    
    #在创建用户实例时初始化用户角色
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(default=False).first()
            else:
                self.role = Role.query.filter_by(default=True).first()

    # @property 修饰器对 password 方法进行修饰，从而使其可以像类似 User 模型属性的方式直接访问
    #使用Ｗerkzeug为注册和登录验证提供密码的散列值计算和验证
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    # setter方法保证设置 password 时，调用 Werkzeug 提供的 generate_password_hash() 函数生成 password_hash
    @password.setter
    def password(self,password):
        self.password_hash = generate_password_hash(password)
    def verify_password(self,password):
        return check_password_hash(self.password_hash,password)

    # 使用 itsdangerous 生成确认邮件链接中用户 id 的确认令牌
    # 确认邮件中最简单的确认链接是 http://www.example.com/auth/confirm/<id>这种形式的 URL，其中 id 是数据库
    # 分配给用户的数字 id 。用户点击链接后，处理这个路由的视图函数就将收到的用户 id 作为参数进行确认，然后将用户状态更新为已确认
    # 但是这种方式显然不安全，只要用户能判断确认链接的格式，就可以随便指定 URL 中的 id ，从而确认任意账户。解决办法是把 URL 中的
    # id 换成加密后得到的令牌。使用 itsdangerous 包的 TimedJSONWebSignatureSerializer 类可以生成具有过期时间的 JSON Web 签名
    # (JSON Web Signatures, JWS)。这个类的构造函数接收的参数是一个秘钥，在 Flask 程序中可使用 SECRET_KEY 设置
    #注册阶段用
    def generate_confirmation_token(self,expiration=3600):
        #生成一个具有过期时间的JSON Web签名
        s = Serializer(current_app.config['SECRET_KEY'],expiration)
        #用生成的JSON Web签名的dumps()方法为指定的用户id生成加密签名
        return s.dumps({'confirm':self.id}).decode('utf-8')

    #验证阶段用
    def confirm(self,token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            # 解码令牌使用序列化对象的 loads() 方法，其唯一的参数是令牌字符串。这个方法会检验签名和过期时间，如果通过，返回原始数据。
            # 如果提供给 loads() 方法的令牌不正确或已过期，则抛出异常
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        # 验证通过把用户确认状态更新为已确认
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self,expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'],expiration)
        return s.dumps({'reset':self.id}).decode('utf-8')

    @staticmethod
    def reset_password(token,new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
       # 验证通过，调用经 @property 修饰器修饰后的 password 方法(属性)重置密码 
        user.password = new_password
        db.session.add(user)
        return True


    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        # 将用户输入的新的电子邮件地址和用户 id 一起保存在更改邮箱的令牌中
        return s.dumps(
            {'change_email': self.id, 'new_email': new_email}).decode('utf-8')

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        db.session.add(self)
        return True

    def is_Administrator(self):
        return self.role.name == "Administrator"

    # 在用户登录时调用 last_login_time() 更新用户的登录时间
    def last_login_time(self):
        self.last_login = datetime.utcnow()
        db.session.add(self)

    # 在用户登出时调用 last_logout_time() 更新用户的登出时间
    def last_logout_time(self):
        self.last_logout = datetime.utcnow()
        db.session.add(self)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def __repr__(self):
        return '<User %r>' % self.username


class InitialGas(db.Model):
    __tablename__ = 'initialGas'
    id = db.Column(db.Integer, primary_key=True)
    gas_data = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow())

    @staticmethod
    def insert_initialGas():
        initialGass = InitialGas.query.order_by(InitialGas.timestamp).all()
        if len(initialGass) == 0:
            initialGass[0].gas_data = 0 
            initialGass[0].timestamp = datetime.utcnow() 
            db.session.add(initialGass[0])
            db.session.commit()

class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False
    def is_administrator(self):
        return False
login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) #返回指定主键对应的行，如果没有对应
                                        #的行则返回None


