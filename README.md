# ClipBoard Ninja
Histórico de textos e imagens para desktop Linux. Copie um trecho, depois outra coisa, pressione **Ctrl+Shift+V**, busque uma palavra e dê Enter para copiar o item original. Use Ctrl+V no destino. Para extrair uma frase de uma captura de tela, copie a imagem e aguarde o OCR. Use **Copiar texto** no resultado.

## Instalar no Kali Linux
Na pasta extraída, execute:
```bash
sudo apt update
sudo apt install python3-pyqt5 python3-xlib tesseract-ocr tesseract-ocr-por tesseract-ocr-eng
/usr/bin/python3 ninja.py
```
Use a sessão **X11/Xorg** para captura global e atalho. O programa começa com a janela visível. Com bandeja disponível, fechar a janela mantém a captura ativa. Use **Sair** no ícone N para encerrar. Sem bandeja, fechar a janela encerra o app. Em Wayland a captura entre aplicativos depende do compositor e o atalho global desta versão fica desativado. Se Ctrl+Shift+V estiver ocupado pelo ambiente, libere essa combinação ou abra pelo painel.

## Recursos e limites
- Busca local no conteúdo e nas transcrições das imagens. Duplo clique ou Enter copia o original.
- Imagens são guardadas em PNG e lidas pelo Tesseract em português e inglês, conforme idiomas instalados. OCR não bloqueia a busca. Imagens sem texto continuam disponíveis para copiar.
- O histórico sobrevive ao reinício. Até 200 itens, com limite aproximado de 64 MiB de conteúdo. Itens idênticos voltam ao topo. Captura formatos de texto e imagem da área de transferência padrão, não a seleção primária do mouse.
- Texto até 1 MB e imagem até 16 megapixels e 8 MB em PNG. Até quatro imagens aguardam OCR além da atual. Se a fila lotar, a imagem é salva sem transcrição.
- Não envia conteúdo a servidores. O arquivo SQLite fica em `$XDG_DATA_HOME/clipboard-ninja` ou `~/.local/share/clipboard-ninja`. O banco **não é criptografado**. Pause antes de copiar senhas ou outros segredos. Nem todos os aplicativos sinalizam conteúdo sensível. Limpar o histórico não limpa o clipboard do sistema.

## Publicar no GitHub
O ZIP contém uma única pasta de projeto. Rode os comandos **dentro dela**:
```bash
cd ~/Downloads/clipboard-ninja
git init -b main
git add README.md ninja.py storage.py hotkey.py .gitignore
git status --short
git commit -m "feat: publica ClipBoard Ninja para Linux"
git remote add origin https://github.com/allyxzs/clipboard-ninja.git
git push -u origin main
```
Se o remoto origin já existir, use `git remote set-url origin https://github.com/allyxzs/clipboard-ninja.git`. É um aplicativo de desktop executado no computador, sem etapa de build ou GitHub Pages.

