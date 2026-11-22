#!/usr/bin/python3
import os
import sys
import fcntl
import subprocess
from pathlib import Path
from collections import deque
from PyQt5 import QtCore as C, QtGui as G, QtWidgets as W
from storage import History
from hotkey import register

STYLE = """QWidget{background:#131622;color:#eeeafa;font-size:14px}
QLabel#brand{color:#66f5cb;font-size:26px;font-weight:bold}
QLineEdit,QListWidget,QPlainTextEdit{background:#1c2030;border:1px solid #525672;padding:6px}
QPushButton{background:#33354c;border:1px solid #656184;border-radius:4px;padding:7px}
QPushButton:focus,QLineEdit:focus{border:2px solid #66f5cb}
QListWidget::item:selected{background:#53477c;color:white}"""


class Reader(C.QThread):
    done = C.pyqtSignal(str,str,str)
    def __init__(self, digest, png, lang):
        super().__init__()
        self.digest,self.png,self.lang = digest,png,lang

    def run(self):
        try:
            result = subprocess.run(['tesseract','stdin','stdout','-l',self.lang],input=self.png,
                                    capture_output=True,timeout=25)
            body = result.stdout.decode('utf-8',errors='replace').strip()[:200000]
            state = ('OCR concluído' if body else 'Sem texto reconhecido') if result.returncode == 0 else 'Falha no OCR'
        except (OSError,subprocess.TimeoutExpired):
            body,state = '', 'OCR indisponível'
        self.done.emit(self.digest,body,state)


class Ninja(W.QWidget):
    def __init__(self, app, store):
        super().__init__()
        self.app,self.store,self.clip = app,store,app.clipboard()
        self.paused=False
        self.queue=deque()
        self.worker=None
        self.setWindowTitle('ClipBoard Ninja')
        self.resize(720,580)
        self.setStyleSheet(STYLE)
        layout=W.QVBoxLayout(self)
        title=W.QLabel('◈  ClipBoard Ninja'); title.setObjectName('brand');layout.addWidget(title)
        self.status=W.QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        self.find=W.QLineEdit();self.find.setPlaceholderText('Buscar em textos e imagens reconhecidas…');layout.addWidget(self.find)
        self.list=W.QListWidget();layout.addWidget(self.list,2)
        self.preview=W.QPlainTextEdit();self.preview.setReadOnly(True);layout.addWidget(self.preview,1)
        buttons=W.QHBoxLayout();layout.addLayout(buttons)
        for label,action in [('Copiar original',self.restore),('Copiar texto',lambda:self.restore(True)),
                             ('Excluir',self.delete),('Limpar tudo',self.clear),('Pausar',self.pause)]:
            b=W.QPushButton(label);b.clicked.connect(lambda _,fn=action:fn());buttons.addWidget(b)
            if label=='Pausar':self.pausebtn=b
        self.find.textChanged.connect(self.refresh)
        self.list.currentItemChanged.connect(self.detail)
        self.list.itemDoubleClicked.connect(lambda _:self.restore())
        self.find.returnPressed.connect(self.restore)
        self.tray=None
        if W.QSystemTrayIcon.isSystemTrayAvailable():
            ico=G.QPixmap(48,48);ico.fill(G.QColor('#151927'));p=G.QPainter(ico)
            p.setPen(G.QColor('#66f5cb'));p.setFont(G.QFont('Sans',24,G.QFont.Bold));p.drawText(ico.rect(),C.Qt.AlignCenter,'N');p.end()
            self.tray=W.QSystemTrayIcon(G.QIcon(ico),self);self.tray.setToolTip('ClipBoard Ninja')
            menu=W.QMenu(self);menu.addAction('Abrir busca',self.open);menu.addAction('Pausar / retomar',self.pause);menu.addAction('Sair',app.quit)
            self.tray.setContextMenu(menu);self.tray.activated.connect(lambda reason:self.open() if reason==W.QSystemTrayIcon.Trigger else None);self.tray.show()
        self.shortcut='Use o ícone ou a janela para pesquisar.'
        if os.environ.get('XDG_SESSION_TYPE')!='wayland' and app.platformName()=='xcb':
            try:
                self.notifier=register(app,self.open);self.shortcut='Busca global: Ctrl+Shift+V.'
            except Exception:self.shortcut='Atalho indisponível ou ocupado. Abra a janela pelo painel.'
        self.lang='por+eng'
        try:
            langs=subprocess.check_output(['tesseract','--list-langs'],timeout=4,text=True).splitlines()
            self.lang='+'.join(x for x in ('por','eng') if x in langs) or 'por'
        except (OSError,subprocess.SubprocessError):pass
        self.clip.dataChanged.connect(self.capture)
        self.info();self.refresh()
    def info(self,msg=''):
        self.status.setText(('Captura pausada' if self.paused else 'Captura ativa')+'  •  '+self.shortcut+' '+msg)
    def open(self):
        self.showNormal();self.raise_();self.activateWindow();self.find.setFocus();self.find.selectAll()
    def closeEvent(self,event):
        if self.tray:event.ignore();self.hide()
        else:event.accept()
    def pause(self):
        self.paused=not self.paused;self.pausebtn.setText('Retomar' if self.paused else 'Pausar');self.info()
    def capture(self):
        if self.paused or self.clip.ownsClipboard():return
        mime=self.clip.mimeData()
        if not mime or any(x in mime.formats() for x in ['application/x-kde-passwordManagerHint','x-kde-passwordManagerHint']):return
        if mime.hasImage():
            img=self.clip.image()
            if img.isNull() or img.width()*img.height()>16000000:self.info('Imagem muito grande ou inválida.');return
            buf=C.QBuffer();buf.open(C.QIODevice.WriteOnly)
            if not img.save(buf,'PNG'):return
            data=bytes(buf.data())
            if len(data)>8000000:self.info('Imagem excede 8 MB.');return
            digest,new=self.store.add('imagem','',data)
            if new:
                if len(self.queue)>=4:self.store.finish(digest,'','OCR ocupado')
                else:self.queue.append((digest,data));self.next_ocr()
        elif mime.hasText():
            text=mime.text()
            if not text.strip():return
            if len(text.encode())>1000000:self.info('Texto excede 1 MB.');return
            self.store.add('texto',text)
        else:return
        self.refresh()
    def next_ocr(self):
        if self.worker or not self.queue:return
        self.worker=Reader(*self.queue.popleft(),self.lang)
        self.worker.done.connect(self.ocr_result);self.worker.finished.connect(self.worker_done);self.worker.start()
    def ocr_result(self,key,text,state):
        self.store.finish(key,text,state);self.refresh()
    def worker_done(self):
        self.worker.deleteLater();self.worker=None;self.next_ocr()
    def current(self):
        item=self.list.currentItem()
        return item.data(C.Qt.UserRole) if item else None
    def refresh(self):
        prev=self.current();self.list.clear()
        for ident,kind,body,stamp,state in self.store.results(self.find.text()):
            label=' '.join(body.split())[:95] or state
            item=W.QListWidgetItem(f'{stamp[11:16]}  ·  {kind.upper()}  ·  {label}')
            item.setData(C.Qt.UserRole,ident);self.list.addItem(item)
            if ident==prev:self.list.setCurrentItem(item)
        if self.list.currentRow()<0 and self.list.count():self.list.setCurrentRow(0)
        self.detail()
    def detail(self,*_):
        row=self.store.db.execute('SELECT stamp,state,body FROM clips WHERE id=?',(self.current(),)).fetchone()
        self.preview.setPlainText('\n'.join(row) if row else 'Nenhum item nesta busca.')
    def restore(self,text_only=False):
        row=self.store.db.execute('SELECT body,image FROM clips WHERE id=?',(self.current(),)).fetchone()
        if not row:return
        body,img=row
        if img and not text_only:self.clip.setImage(G.QImage.fromData(img))
        elif body:self.clip.setText(body)
        else:self.info('Esta imagem ainda não tem texto reconhecido.');return
        self.info('Copiado. Cole no aplicativo de destino.')
    def delete(self):
        if self.current() is not None:self.store.remove(self.current());self.refresh()
    def clear(self):
        if W.QMessageBox.question(self,'Histórico','Excluir todos os itens do histórico?',W.QMessageBox.Yes|W.QMessageBox.No,W.QMessageBox.No)==W.QMessageBox.Yes:
            self.store.remove();self.queue.clear();self.refresh()

def main():
    os.umask(0o077)
    folder=Path(os.environ.get('XDG_DATA_HOME') or Path.home()/'.local/share')/'clipboard-ninja'
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=(folder/'session.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:sys.exit('ClipBoard Ninja já está em execução.')
    app=W.QApplication(sys.argv);store=History(folder/'history.sqlite3');window=Ninja(app,store)
    window.open()
    app.exec_()
    window.queue.clear()
    if window.worker:window.worker.wait()
    store.db.close()

if __name__=='__main__':main()

