#!/usr/bin/env python2
#-*- coding:utf-8 -*-

import socket
from threading import Thread
from flask import current_app
from ..models import InitialGas, User
from .. import db
#from datetime import datetime
#import hashlib
#import os
#import base64
#import time

# socket 接收数据的最大长度
SOCKET_SIZE = 1024

def parseGasData(data, user_email=None):
    # len(data) != 0，表示连接主程序成功，可以更新初始气体数据
    if len(data) != 0:
        # 丢弃数据结尾的 '\0'
        data = data.replace('\n',' ')
        data = data.replace(' ','')
        initialGass = InitialGas.query.order_by(InitialGas.timestamp).all()
        if len(initialGass) != 0:
            for i in range(0, len(initialGass)-1):
                try:
                    initialGass[i].gas_data = initialGass[i+1].gas_data 
                    initialGass[i].timestamp = initialGass[i+1].timestamp
                    db.session.add(initialGass[i])
                    db.session.commit()
                except Exception as err:
                    print('Modify data to InitialGas model occurs error: %s' % err)
                    db.session.rollback()
            try:
                i = len(initialGass) - 1
                initialGass[i].gas_data = data[0]  
                initialGass[i].timestamp = datetime.strptime(timestamp, '%Y_%m_%d_%H_%M_%S')

                # 手动更新最后一位数据
                db.session.add(initialGass[i])
            except Exception as err:
                print('Update InitialGass Model in socket communication occurs error: %s' % err)
            finally:
                db.session.commit()
        else:
            print('InitialGass table is empty!')

def async_updateModel(app, parseDatafunc, user_email):
    with app.app_context():
        # 创建一个socket
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        # 连接到指定的服务器：IP + 端口号 指定
        s.connect(('127.0.0.1',9999))
        # 接收数据
        data = s.recv(10).decode('utf-8')
        if len(data) != 0:
            # 解析接收到数据
            parseGasData(data, user_email=user_email)
        else:
            print('Socket recevie data is None.')
        s.close()

def updateModel(parseDatafunc, user_email):
   # async_updateCalBoardModel 函数中，需要使用当前应用实例 app 来创建
    # 应用上下文，所以需要获取 current_app 代理对象背后潜在的被代理的当前应用实例 app，
    # 可以用 _get_current_object() 方法获取 app。
    app = current_app._get_current_object()
    thr = Thread(target=async_updateModel, args=[app, parseDatafunc, user_email])
    thr.start()
    return thr




