#!/usr/bin/env python2
#-*- coding:utf-8 -*-

from flask import render_template,session,redirect,url_for,abort,flash,current_app,request,make_response
from flask_login import login_required, current_user
from . import main
from .. import db
from ..models import Role,User,InitialGas
from socket_client import updateModel, parseGasData
from .forms import EditProfileForm,EditProfileAdminForm

from ..email import send_email

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user)

# 执行对于初始气体数据刷新的 Ajax 请求
@main.route('/InitialGas_deal', methods=['GET'])
def initialGas_deal():
    # 首先与主程序通信更新 InitialGas 模型中数据
    updateModel(parseGasData, user_email=current_user.email)
    # 查询数据库获取当前的主控板数据
    # 按照时间戳降序方式将控制板数据排序，也就是说第一位数据时间最新
    initialGas = InitialGas.query.order_by(InitialGas.timestamp.desc()).first()
    return initialGas

@main.route('/views')
def views():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    else:
        flash(u'欢迎使用！')
        updateModel(parseGasData, user_email=current_user.email)
        initialGass = InitialGas.query.order_by(InitialGas.timestamp).all()
        return render_template('views.html',initialGass=initialGass)
 
@main.route('/point')
def point():
    return render_template('point.html')
         
@main.route('/nopoint')
def nopoint():
    return render_template('nopoint.html')

@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)

@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


