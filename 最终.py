#引入需要使用的库
from machine import Pin, PWM, Timer
from mpu6050 import MPU6050
import time
import _thread
import math
import socket
import json
import network

# 连接Wi-Fi网络
def connect_wifi(ssid, password):
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(ssid, password)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())    
ssid = "wlyjq"
password = "wzq050915"
connect_wifi(ssid, password)


##对MPU6050、对射传感器和PWM控制电机和舵机的引脚进行初始化设置，并读取MPU6050的加速度、陀螺仪、温度数据

#MPU6050
mpu = MPU6050()
accel = mpu.read_accel_data() 
aX = accel["x"]
aY = accel["y"]
aZ = accel["z"]
gyro = mpu.read_gyro_data()   
gX = gyro["x"]
gY = gyro["y"]
gZ = gyro["z"]
temp = mpu.read_temperature()
#对射传感器
pes = Pin(5, Pin.IN, Pin.PULL_UP, value=1)
tim0 = Timer(0)
tim1 = Timer(1)
cnt_0 = 0
cnt_1 = 0
distance = 0
speed = 0
#pwm值
motor1 = PWM(Pin(27), Pin.OUT)
motor2 = PWM(Pin(26), Pin.OUT)
servo = PWM(Pin(15), Pin.OUT)
motor1.freq(100)
motor2.freq(100)
servo.freq(100)

# 设置蜂鸣器引脚
buzzer_pin = 25
buzzer = PWM(Pin(buzzer_pin))
# 定义音符频率（Hz）
notes = {
    'C1': 262, 'D1': 294, 'E1': 330, 'F1': 349, 'G1': 392, 'A1': 440, 'B1': 494,
    'C': 523, 'D': 587, 'E': 659, 'F':698 , 'G': 784, 'A': 880, 'B': 988,
    'C2': 1046, 'D2': 1175, 'E2': 1318, 'F2': 1397, 'G2': 1568, 'A2': 1760, 'B2':1976,
    'C3':2155
    }


   

# 50-158-250(舵机)
servo.duty(158)
motor1.duty(1)
motor2.duty(1)
time.sleep(1)
##设置各个线程
#设置线程task1和task2，分别进行加速度、陀螺仪、温度和距离的读取，对射传感器的计数并计算速度和距离
def task1():
    global aX, aY, aZ, gX, gY, gZ, temp
    while 1:
        accel = mpu.read_accel_data() 
        aX = accel["x"]
        aY = accel["y"]
        aZ = accel["z"]
        print("acx: " + str(aX) + " acy: " + str(aY) + " acz: " + str(aZ))
        gyro = mpu.read_gyro_data()   
        gX = gyro["x"]
        gY = gyro["y"]
        gZ = gyro["z"]
        print("gx:" + str(gX) + " gy:" + str(gY) + " gz:" + str(gZ))
        temp = mpu.read_temperature()   
        print("Temperature: " + str(temp) + "°C")
        
        time.sleep(1) 

def task2():
    global cnt_0, cnt_1, distance, speed
    # 读取转动次数
    def read(tim0):
        global cnt_0, cnt_1
        if pes.value() == 0:
            cnt_0 += 1
        if cnt_0 > 0:
            if pes.value() == 1:
                cnt_1 += 1
                cnt_0 = 0

    # 计算速度，距离
    def calculate(tim1):
        global cnt_1, distance, speed
        number = cnt_1 / 18 * 8 / 24 * 12 / 28
        speed = float(number * math.pi * 6)
        distance += speed
        print(str(speed) + 'cm/s')
        print(str(distance) + 'cm')
        cnt_1 = 0

    tim0.init(period=10, mode=Timer.PERIODIC, callback=read)
    tim1.init(period=1000, mode=Timer.PERIODIC, callback=calculate)
    
#设置线程task3，通过TCP/IP socket向指定服务器发送传感器数据。    
def task3():
    global aX, aY, aZ, gX, gY, gZ, temp, distance, speed
    while 1:
        try:
            # 创建 TCP/IP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # 连接服务器
            server_address = ('192.168.0.6', 6666)
            sock.connect(server_address)

            # 发送数据
            data = {
                '加速度': [aX, aY, aZ],
                '陀螺仪': [gX, gY, gZ],
                '温度': temp,
                '距离': distance,
                '速度': speed
            }
            #通过对字符串进行utf-8编码，使其转变为字节流
            #将 Python 对象转换为 JSON 格式的字符串，并将其以 UTF-8 编码的字节流形式保存在变量 message 中
            message = json.dumps(data).encode('utf-8')
            sock.sendall(message)
            
            # 关闭连接
            sock.close()
        
        except Exception as e:
            print("发送数据时出现错误:", e)
        
        time.sleep(0.5)
def task4():
    # 播放音符函数
    def play_note(note, duration):
        if note in notes:
            if note == '':
                time.sleep(duration)  # 空拍时直接等待，不播放音符
            else:
                buzzer.freq(notes[note])
                buzzer.duty(824)
                time.sleep(duration)
                buzzer.duty(0)  # 停止发声
        else:
            print("Invalid note")

    # 播放旋律
    melody = [
        ('G1', 0.15), ('D', 0.15), ('C', 0.15),('G1',0.22),
        ('C', 0.05), ('D', 0.05), ('E', 0.05), ('D', 0.05),('C', 0.05),('D', 0.05),
        ('G1', 0.15), ('D', 0.15), ('C', 0.15),('G1',0.22),
        ('C', 0.05), ('D', 0.05), ('E', 0.05), ('D', 0.05),('C', 0.05),('D', 0.05),
        ('G1', 0.15), ('D', 0.15), ('C', 0.15),('G1',0.3),
        ('C',0.11),('',0.03),('C',0.08),('E', 0.2), ('G', 0.2),('A',0.32),('G',0.3),('',0.2),
        ('C',0.09),('',0.03),('C',0.04),('D',0.2),('C',0.2),('D',0.2),('E',0.2),('',0.2),
        ('E',0.18),('G',0.2),('A',0.2),('B',0.2),('A',0.2),('G',0.2),('D',0.2),('E',0.2),('C',0.2),('D',0.2),('D',0.2),('D',0.2),('C',0.2),('',0.4),
        ('C2',0.2),('E2',0.2),('G2',0.2),('A2',0.4),('G2',0.2),('',0.2),
        ('C',0.2),('D',0.2),('D',0.2),('C',0.2),('E',0.2),('',0.2),
        ('D',0.3),('G',0.2),('A',0.2),('C2',0.2),('D2',0.2),('E2',0.2),('D2',0.2),('C2',0.2),('G',0.2),('C2',0.2),('E2',0.2),('',0.1),('E2',0.2),('',0.1),('E2',0.2),('',0.2),('D',0.2),('',0.2),
        ('G',0.2),('C2',0.2),('E2',0.2),('',0.1),('E2',0.2),('',0.1),('E2',0.2),('',0.1),('D2',0.2),('',0.2),
        ('C3',0.15),('B2',0.15),('A2',0.4),('G2',0.15),('C3',0.15),('B2',0.15),('A2',0.3),('G2',0.15),('A2',0.15),('G2',0.15),('E2',0.15),('',0.2),
        ('G',0.1),('A',0.1),('C2',0.1),('D2',0.1),('E2',0.25),('D2',0.1),('E2',0.25),('D2',0.1),('E2',0.25),('D2',0.1),('E2',0.1),('G2',0.1),('E2',0.1),('D2',0.1),('C2',0.25),('A',0.1),('C2',0.25),('D2',0.1),('C2',0.1),('',0.2),
        ('C3',0.15),('B2',0.15),('A2',0.4),('G2',0.15),('C3',0.15),('B2',0.15),('A2',0.3),('G2',0.15),('A2',0.15),('G2',0.15),('E2',0.15),('',0.2),
        ('G',0.1),('A',0.1),('C2',0.1),('D2',0.1),('E2',0.25),('D2',0.1),('E2',0.25),('D2',0.1),('E2',0.25),('D2',0.1),('E2',0.1),('G2',0.1),('E2',0.1),('D2',0.1),('C2',0.25),('A',0.1),('C2',0.25),('D2',0.1),('C2',0.1),('',0.2)
    
    ]
    # 播放音乐
    while 1:
        for note, duration in melody:
            play_note(note, duration)
            time.sleep(0.1)
        #细节0.824秒
        time.sleep(0.824)  
    
_thread.start_new_thread(task1, ())
_thread.start_new_thread(task2, ())
_thread.start_new_thread(task3, ())
_thread.start_new_thread(task4, ())

#小车运行的主要代码
while 1:
    
    for i in range(1, 1000, 50):
        motor2.duty(i)
        time.sleep_ms(400)
        time.sleep(0.01)  # 让出时间片给其他线程
    time.sleep(2.3)
    for i in range(1023, 555, -50):
        motor2.duty(i)
        servo.duty(55)
        time.sleep_ms(770)
        time.sleep(0.01)  # 让出时间片给其他线程
    servo.duty(165)
    time.sleep_ms(200)
    motor2.duty(1023)
    time.sleep(6.8)
    motor2.duty(1)
    time.sleep(2)
    # 倒车入库
    motor1.duty(1023)
    servo.duty(55)
    time.sleep(4.8)
    for i in range(1023, 1, -50):
        motor1.duty(i)
        servo.duty(165)
        time.sleep_ms(160)
        time.sleep(0.01)  # 让出时间片给其他线程
    time.sleep(2)
    # 出库
    motor1.duty(1)
    motor2.duty(1023)
    time.sleep(3)
    servo.duty(55)
    time.sleep(5.2)
    servo.duty(165)
    motor2.duty(1)
    time.sleep_ms(500)
    motor1.duty(1023)
    time.sleep(4)
    motor1.duty(1)
    time.sleep_ms(500)
    # 转弯并走完最后一条道路
    motor2.duty(666)
    time.sleep(2.6)
    servo.duty(55)
    time.sleep(7.2)
    for i in range(666, 1023, 50):
        motor2.duty(i)
        servo.duty(165)
        time.sleep_ms(100)
        time.sleep(0.01)  # 让出时间片给其他线程
    time.sleep(24)


