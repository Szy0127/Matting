import sys
from PyQt5.QtWidgets import QApplication, QAction,QFileDialog,QMainWindow,QMessageBox
from PyQt5.QtCore import QTimer,QSize
from PyQt5.QtGui import QPalette,QBrush,QPixmap,QPainter,QImage,qRgba,qRgb,QColor,QRgba64,QPen
from threading import Thread
import numpy as np
from queue import Queue
import cv2
from random import randint
from os import system

'''
功能：鼠标左键拖动 选择闭合区域 截取此区域

思路：
1 打开图片  图片充满整个区域 像素点与UI界面坐标一一对应
2 鼠标事件获得坐标 记录所有坐标构成边界
3 选取中间点进行bfs 遇到边界停止 可以获取中间一块选中的区域
4 选中区域的alpha通道为255 其他为0

图片展示需要用QImage
但是对于图片像素的操作 QImage.setPixel太慢
cv2读 直接改矩阵快
但是矩阵转QImage太麻烦
所以没法预览效果只能先保存
'''
class Cut:
    def __init__(self):
        self.direction = [[1,0],[0,1],[-1,0],[0,-1]]
        self.can_save = False
    def setup(self,path,width,height,bound):
        self.path = path
        img = cv2.imread(path)
        img = cv2.resize(img,(width,height))
        self.image = cv2.cvtColor(img,cv2.COLOR_BGR2BGRA)
        
        self.boundary = bound
        self.width = width
        self.height = height
    
        self.setupImage()
        
        
    def setupImage(self):
        for i in range(self.height):
            for j in range(self.width):
                self.image[i][j][3] = 0
    
    def reverse(self):
        if not self.can_save:
            return False
        for i in range(self.height):
            for j in range(self.width):
                self.image[i][j][3] ^= 0xff
        return True
        
    def bfs(self):
        self.visited = set()
        q = Queue()
        x,y = self.width//2,self.height//2 #起始点
        while not self.valid(x,y):
            x = randint(0,self.width)
            y = randint(0,self.height)
        q.put((x,y))
        self.visited.add((x,y))
        while not q.empty():
            x,y = q.get()
            for dx,dy in self.direction:
                nx = x + dx
                ny = y + dy
                if not (nx,ny) in self.visited and self.valid(nx,ny):
                    self.image[ny][nx][3] = 255
                    q.put((nx,ny))
                self.visited.add((nx,ny))
        self.can_save = True
            
    def valid(self,x,y):
        if x < 0 or x >= self.width:
            return False
        if y < 0 or y >= self.height:
            return False
        return not (x,y) in self.boundary
       
    def save(self,path):
        cv2.imwrite(path,self.image)

class MatUI(QMainWindow):
    
    def __init__(self):
        super(MatUI,self).__init__()

        self.cutModel = Cut()
        self.maxWidth = 1800
        self.maxHeight = 900
        
        self.file = self.menuBar().addMenu('文件')
        self.operate = self.menuBar().addMenu('编辑')
        self.help = self.menuBar().addMenu('帮助')
        
        self.addAct('打开',self.select,self.file)
        self.addAct('保存',self.save,self.file)
        self.addAct('裁剪',self.cut,self.operate)
        self.addAct('清空',self.clear,self.operate)
        self.addAct('反向选择',self.reverse,self.operate)
        self.addAct('使用说明',self.usage,self.help)
        self.addAct('注意事项',self.notice,self.help)
        self.addAct('联系作者',self.contact,self.help)


        self.resize(600,480)
        self.move(500,200)
        self.setWindowTitle('抠图神器')


        self.image = None
        self.qmap = None

        #self.choose = QColor(QRgba64.fromRgba64(0,0,0,0))

        self.record = set()

        self.penWidth = 2
        self.penColor = QColor(0x87,0xce,0xeb)
        
        self.imagePath = ''
        
    def addAct(self,name,func,menu):
        act = QAction(parent=self)
        act.setText(name)
        act.triggered.connect(func)

        menu.addAction(act)
    def start(self):
        if fileName:= self.select():
            self.set_background(fileName)
            
    def getSize(self,width,height):
        scalew = self.maxWidth/width
        scaleh = self.maxHeight/height

        scale = min(scalew,scaleh)

        return int(width * scale), int(height * scale)

    def select(self):
        fileName,t = QFileDialog.getOpenFileName(self,"选择图片",filter="Image Files (*.png *.jpg *.bmp)")
        if not fileName:
            return
        self.imagePath = fileName
        self.image = QImage(fileName)
        #self.imageo = self.image.convertToFormat(QImage.Format.Format_RGBA64)
        self.size = self.getSize(self.image.width(),self.image.height())
        self.image = self.image.scaled(QSize(*self.size))
        self.qmap = QPixmap(self.image)
        
        self.resize(*self.size)
        self.move(300,50)
            
            
    def reverse(self):
        if self.cutModel.reverse():
            QMessageBox.information(self,'提示','反向选择完成')
        else:
            QMessageBox.critical(self,'错误','请先选择裁剪')
    def cut(self):
        if not self.image:
            QMessageBox.critical(self,'错误','请先打开图片')
            return
        if not self.record:
            QMessageBox.critical(self,'错误','请先画出轮廓')
            return
        self.cutModel.setup(self.imagePath,*self.size,self.record)
        self.cutModel.bfs()
        QMessageBox.information(self,'提示','裁剪完成')
        
    def save(self):
        if not self.cutModel.can_save:
            QMessageBox.critical(self,'错误','请先选择裁剪')
            return
        path,t = QFileDialog.getSaveFileName(self,"保存图片",self.imagePath[:-4]+'_cut',"Image Files (*.png)")
        if not path:
            return
        self.cutModel.save(path)
        QMessageBox.information(self,'提示','保存成功')
        system(path)
        
    def clear(self):
        self.record.clear()
        self.update()
        
    def usage(self):
        message = ''
        with open('usage.txt','r',encoding='utf-8') as f:
            while m:= f.readline():
                message += m
        QMessageBox.information(self,'使用说明',message)
    
    def notice(self):
        message = ''
        with open('notice.txt','r',encoding='utf-8') as f:
            while m:= f.readline():
                message += m
        QMessageBox.information(self,'注意事项',message)    
    def contact(self):
        QMessageBox.information(self,'联系作者','szy0127@sjtu.edu.cn')
    '''   
    def setChosen(self,x,y):
        
        self.image.setPixelColor(x,y,self.choose) # 这个api太慢 不适合大规模使用
        self.qmap = QPixmap(self.image)
        self.update()
    '''
    def paintEvent(self,event):
        if not self.qmap:
            return
        painter = QPainter(self)
        painter.begin(self)

        painter.drawPixmap(0,0,self.qmap)
        
        pen = QPen()
        pen.setWidth(1)
        pen.setColor(self.penColor)
        painter.setPen(pen)
        for x,y in self.record:
            painter.drawPoint(x,y)

        painter.end()


    def expand(self,x,y):
        for i in range(-self.penWidth,self.penWidth+1):
            for j in range(-self.penWidth,self.penWidth+1):
                yield (x+i,y+j)
    
    def mousePressEvent(self,event):
        if not self.image:
            return
        self.draw_line = False
        self.clear_line = False
        key = event.button()
        if key == 1:#左键 画
            self.draw_line = True
        elif key == 2:#右键 擦
            self.clear_line = True
            
    def mouseMoveEvent(self,event):
        if not self.image:
            return
        #print(event.pos()) #快速移动时不保证连续
        pos = event.pos()
        self.event = event
        for xi,yi in self.expand(pos.x(),pos.y()):
            if self.draw_line:
                self.record.add((xi,yi))
            elif self.clear_line and (xi,yi) in self.record:
                self.record.remove((xi,yi))
        self.update()
        
        
if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    mat = MatUI()
    mat.show()
    sys.exit(app.exec_())
