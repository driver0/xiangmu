#!/usr/bin/env python2
#-*- coding:utf-8 -*-

from flask import render_template,redirect,request,url_for,flash
from flask_login import login_user,logout_user,login_required,current_user
from . import auth
from .. import db
from ..models import User
from ..email import send_email
from .forms import LoginForm,RegistrationForm,ChangePasswordForm,PasswordResetRequestForm,PasswordResetForm,ChangeEmailForm

@auth.before_app_first_request
def before_first_request():
    # 如果浏览器保存有用户信息的 cookie，一旦用户登录之后，下次打开浏览器使用这个 cookie 可以复现用户会话
    # 也就是说用户再次登录时可以跳过登录页面而直接访问页面，所以在这种情况下要在处理第一个请求之前运行的 before_first_request()
    # 请求钩子中，判断用户是登录用户，如果是则更新该用户的登录时间
    if current_user.is_authenticated:
        current_user.last_login_time()

@auth.before_app_request
# 程序可以决定用户在确认账户之前可以执行哪些操作，比如允许未确认的用户登录，但只显示一个页面，
# 这个页面要求用户在获取权限之前先确认账户。Flask 提供的 before_request() 请求钩子可以在每次请求之前运行，
# 但对于蓝本来说，before_request() 钩子只能应用到属于蓝本的请求上。若想在蓝本中使用针对程序全局请求的钩子，
# 必须使用 before_app_request_before 修饰器。
def before_request():
    # 同时满足以下三个条件时，before_app_request 修饰器会拦截请求：
    #   1. 用户已登录
    #   2. 用户的账户还未确认
    #   3. 请求的端点(使用 request.endpoint 获取)不在认证蓝本 auth 中。访问认证蓝本 auth 中的路由本身就需要获取用户的权限。
    # 将页面重定向到 /auth/unconfirmed 路由，显示一个确认账户相关信息的页面
    if current_user.is_authenticated \
            and not current_user.confirmed \
            and request.endpoint[:5] != 'auth.' \
            and request.endpoint != 'static':
        return redirect(url_for('auth.unconfirmed'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # 如果电子邮件对应的用户存在并且密码正确
        if user is not None and user.verify_password(form.password.data):
            # Flask-Login 中的 login_user() 函数，在用户会话中把用户标记为已登录
            # remember_me 值为 False，那么关闭浏览器后用户会话就过期，所以下次用户访问时要重新登录
            # 如果值为 True，那么会在用户浏览器中写入一个长期有效的 cookie，使用这个 cookie 可以复现用户会话
            login_user(user, form.remember_me.data)
            # 更新用户的登录时间
            user.last_login_time()
            return redirect(request.args.get('next') or url_for('main.index'))
        flash(u'无效的用户名或密码')
    return render_template('auth/login.html', form=form)

@auth.route('/logout')
# Flask-Login 提供的 login_required 修饰器作用后，未认证的用户访问这个路由，Flask-Login 会拦截请求，把用户发往登录页面
@login_required
def logout():
    # 用户登出时，更新用户的登出时间
    current_user.last_logout_time()
    # Flask-Login 中的 logout_user() 函数，删除并重设用户会话
    logout_user()
    flash(u'你已经登出系统')
    return redirect(url_for('auth.login'))

#@app.route('/secret')
#@login_required
#def secret():
#    return 'Only authenticated users are allowed!'



@auth.route('/register',methods=['GET','POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                username=form.username.data,
                password=form.password.data)
        db.session.add(user)  
        db.session.commit()
        token =  user.generate_confirmation_token()
        send_email(user.email, u'确认您的账户',
                   'auth/email/confirm', user=user, token=token)
        flash(u'一封确认邮件已经发送到您的邮箱')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html',form=form)

@auth.route('/confirm/<token>')
# Flask-Login 提供的 login_required 修饰器作用后，未认证的用户访问这个路由，Flask-Login 会拦截请求，把用户发往登录页面
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        db.session.commit()
        flash(u'您已经确认了您的账户，非常感谢！')
    else:
        flash(u'确认链接无效或已过期')
    return redirect(url_for('main.index'))

@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email,u'确认您的账户',
            'auth/email/confirm',user=current_user,token=token)
    flash(u'新的确认邮件已经发送到您的邮箱')
    return redirect(url_for('main.index'))

@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')



# 对于忘记密码无法登录的用户，提供重置密码功能。但安全起见，有必要使用类似于确认账户时用到的令牌。
#   1. 用户请求重置密码后，程序会向用户注册时提供的电子邮件地址发送一封包含重设令牌的邮件
@auth.route('/reset-password/',methods=['GET','POST'])
def password_reset_request():
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email,u'重置您的密码',
                    'auth/email/reset_password',
                    user=user,token=token,
                    next=request.args.get('next'))
        flash(u'带有重置密码操作步骤的邮件已经发送到您的邮箱')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html',form=form)

# 对于忘记密码无法登录的用户，提供重置密码功能。但安全起见，有必要使用类似于确认账户时用到的令牌。
#   2. 用户点击邮件中的链接，令牌验证后，会显示一个用于输入新密码的表单
@auth.route('/reset/<token>',methods=['GET','POST'])
def password_reset(token):
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            return redirect(url_for('main.index'))
        if user.reset_password(token, form.password.data):
            flash(u'您的密码已经重置！')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

@auth.route('/change-password',methods=['GET','POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
            flash(u'您的密码已经更新！')
            return redirect(url_for('main.index'))
        else:
            flash(u'原密码不正确')
    return render_template("auth/change_password.html",form=form)

@auth.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, u'确认您的邮箱地址',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash(u'确认您新邮箱的邮件已经发送到该新邮箱！')
            return redirect(url_for('main.index'))
        else:
            flash(u'密码不正确')
    return render_template("auth/change_email.html", form=form)


@auth.route('/change_email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        flash(u'您的邮箱地址已经更改成功！')
    else:
        flash(u'无效的请求链接！')
    return redirect(url_for('main.index'))
