#!/usr/bin/env python2
#-*- coding:utf-8 -*-

import socket
from threading import Thread
#from flask import current_app
from ..models import InitialGas, User
#from .. import db
#from datetime import datetime
#import hashlib
#import os
#import base64
#import time

# socket 接收数据的最大长度
SOCKET_SIZE = 1024

def parseControlBoardData(data, user_email=None):
    if len(data) != 0:
        # 丢弃数据结尾的 '\0'
        data = data.replace('\n',' ')
        data = data.rstrip(' ')
        InitialGass = InitialGas.query.order_by(InitialGas.timestamp).first()
        if len(controlBoards) != 0:
            for i in range(0, len(controlBoards)-1):
                try:
                    # 用后面一位较新的数据覆盖前面那个较老的数据，最后一位数据需要在接下来手动更新
                    controlBoards[i].cpu_user_percent = controlBoards[i+1].cpu_user_percent
                    controlBoards[i].cpu_sys_percent = controlBoards[i + 1].cpu_sys_percent
                    controlBoards[i].cpu_idle_percent = controlBoards[i + 1].cpu_idle_percent
                    controlBoards[i].timestamp = controlBoards[i + 1].timestamp
                    db.session.add(controlBoards[i])
                    db.session.commit()
                except Exception as err:
                    print('Modify data to ControlBoard model occurs error: %s' % err)
                    db.session.rollback()
            try:
                i = len(controlBoards) - 1
                controlBoards[i].cpu_user_percent = float(int(cpu_user) / 10.0)
                controlBoards[i].cpu_sys_percent = float(int(cpu_system) / 10.0)
                controlBoards[i].cpu_idle_percent = float(int(cpu_idle) / 10.0)
                controlBoards[i].timestamp = datetime.strptime(timestamp, '%Y_%m_%d_%H_%M_%S')
                print("{'cpu_user': %s, 'cpu_system: %s, 'cpu_idle: %s''}" % ( float(int(cpu_user) / 10.0),
                                                                                float(int(cpu_system) / 10.0), float(int(cpu_idle) / 10.0)) )
                # 手动更新最后一位数据
                db.session.add(controlBoards[i])
            except Exception as err:
                print('Update ControlBoard Model in socket communication occurs error: %s' % err)
            finally:
                db.session.commit()
        else:
            print('ControlBoard table is empty!')










s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

s.connect(('127.0.0.1',9999))

print(s.recv(1024).decode('utf-8'))

s.close()
