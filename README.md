<p align="center">
  <img src="assets/icons/logo_Disc0ntrol.png" alt="DisC0ntrol Logo" width="180">
</p>

<h1 align="center">DisC0ntrol</h1>

<p align="center">
  Dashboard desktop para gerenciar multiplos bots Discord a partir de uma unica interface.
  <br />
  Controle, monitore e visualize logs de todos os seus bots em um so lugar.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/UI-CustomTkinter-1F6FEB?style=for-the-badge" alt="CustomTkinter">
  <img src="https://img.shields.io/badge/License-MIT-27ae60?style=for-the-badge" alt="License">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/discord.py-compatible-5865F2?style=flat-square&logo=discord&logoColor=white" alt="discord.py">
  <img src="https://img.shields.io/badge/No%20Token%20Required-grey?style=flat-square" alt="No Token">
</p>

---

## Sobre

**DisC0ntrol** e um gerenciador de processos projetado para quem trabalha com multiplos bots Discord em Python. Em vez de abrir terminais separados para cada bot, o DisC0ntrol oferece uma interface visual unificada com controle de processos, monitoramento em tempo real e visualizacao de logs.

> O DisC0ntrol **nao precisa de token Discord** — ele apenas gerencia processos locais via `subprocess` e `psutil`.

## Funcionalidades

| Feature | Descricao |
|---|---|
| **Autodescoberta** | Escaneia diretorios registrados e encontra bots automaticamente (qualquer pasta com script que importa `discord`) |
| **Bot Cards** | Cards visuais com cor personalizada, status em tempo real, PID, CPU, RAM e uptime |
| **Start / Stop / Restart** | Controle completo de processos com graceful shutdown e cleanup de orfaos |
| **Logs em tempo real** | Mini-log no card + visualizador expandido + abrir log no editor do sistema |
| **Auto-start** | Inicia todos os bots automaticamente ao abrir o DisC0ntrol |
| **Auto-restart** | Reinicia bots que cairam automaticamente (intervalo configuravel) |
| **System Tray** | Minimiza para a bandeja com menu de status dos bots |
| **Persistencia** | Salva configuracoes, diretorios, posicao da janela em `config.json` |
| **Tema escuro/claro** | Dark, Light ou System — alteravel nas configuracoes |

## Instalacao

### Opcao 1: Launcher automatico (recomendado)

```
scripts\iniciar_discontrol.bat
```

O `.bat` cria um ambiente virtual, instala dependencias e executa o DisC0ntrol automaticamente.

### Opcao 2: Manual

```bash
# Clone o repositorio
git clone https://github.com/seu-usuario/DisC0ntrol.git
cd DisC0ntrol

# Crie e ative um ambiente virtual
python -m venv venv
venv\Scripts\activate

# Instale as dependencias
pip install -r requirements.txt

# Execute
python main.py
```

## Como Usar

### 1. Registrar diretorios de bots

Clique em **"+ Adicionar"** > **"Registrar Diretorio"** e selecione a pasta que contem seus bots.

O scanner detecta bots automaticamente:
- Busca em subpastas (`Bot_Gerson/`, `Mionions/`, qualquer nome)
- Se o proprio diretorio for um bot, detecta tambem
- Identifica o script principal buscando `import discord` nos arquivos `.py`
- Detecta `.env`, `.lock` e pasta `logs/`

### 2. Adicionar bot individual

Para bots fora do padrao, use **"Adicionar Bot Individual"** e selecione o script `.py` diretamente, com nome e cor personalizados.

### 3. Controlar bots

Cada card exibe:

```
 ● Bot_Name                    [Online]
 PID 12345 | CPU 2% | RAM 45.3 MB | Up 2h 15m
 [▶ Start] [■ Stop] [↻ Restart]    [✕] [↗] [📄 Log]
 ┌─────────────────────────────────────────┐
 │ 2024-01-15 10:30:00 Bot connected...    │
 │ 2024-01-15 10:30:01 Ready!              │
 └─────────────────────────────────────────┘
```

- **Start/Stop/Restart** — Controle de processos (roda em thread separada, nao trava a UI)
- **✕** — Remover bot do dashboard
- **↗** — Abrir visualizador de logs expandido (in-app, com auto-scroll e busca)
- **Log** — Abrir arquivo de log diretamente no editor padrao do Windows

### 4. Configuracoes

Acesse **Config** na toolbar:

- **Reiniciar bots automaticamente** — Se um bot cair, o DisC0ntrol reinicia
- **Intervalo de restart** — Tempo entre verificacoes (em horas)
- **Iniciar bots ao abrir** — Auto-start de todos os bots no startup
- **Iniciar minimizado** — Abre direto na bandeja do sistema
- **Tema** — Dark / Light / System

## Estrutura de Bots Suportada

O scanner e flexivel e reconhece qualquer bot Discord Python:

```
# Padrao classico (Bot_*)
Bot_Gerson/
├── gerson_bot.py        # Script principal (import discord)
├── gerson_bot.lock      # PID (gerenciado pelo DisC0ntrol)
├── .env                 # DISCORD_TOKEN, CHANNEL_ID, etc
└── logs/
    └── bot_logs.log

# Qualquer outro nome de pasta
Mionions/
├── Disbot_Mionions.py   # Detectado por ter "import discord"
├── .env
└── logs/
    └── bot_logs.log
```

**Requisitos minimos do bot:**
- Ser um arquivo `.py` que contenha `import discord` ou `from discord`
- Estar em uma pasta dedicada

## Estrutura do Projeto

```
DisC0ntrol/
├── main.py                      # Entry point
├── config.json                  # Diretorios e bots registrados (gitignored)
├── core/
│   ├── bot_scanner.py           # Autodescoberta de bots em qualquer pasta
│   ├── bot_controller.py        # Start/Stop/Restart via subprocess + psutil
│   └── log_reader.py            # Leitura de logs em tempo real (tail -f)
├── ui/
│   ├── dashboard.py             # Janela principal + toolbar + grid + tray
│   ├── bot_card.py              # Card com status, controles e mini-log
│   ├── log_viewer.py            # Visualizador expandido de logs
│   ├── add_bot_dialog.py        # Dialog para adicionar bots/diretorios
│   └── settings_dialog.py       # Configuracoes gerais
├── assets/icons/                # Icones
├── logs/                        # Logs do proprio DisC0ntrol (gitignored)
├── scripts/
│   └── iniciar_discontrol.bat   # Launcher Windows
├── requirements.txt
├── .gitignore
└── README.md
```

## Dependencias

| Pacote | Versao | Uso |
|---|---|---|
| [`customtkinter`](https://github.com/TomSchimansky/CustomTkinter) | >= 5.2.0 | Interface grafica moderna com tema escuro |
| [`psutil`](https://github.com/giampaolo/psutil) | >= 5.9.0 | Gerenciamento e monitoramento de processos |
| [`pystray`](https://github.com/moses-palmer/pystray) | >= 0.19.0 | Icone na bandeja do sistema |
| [`Pillow`](https://github.com/python-pillow/Pillow) | >= 10.0.0 | Geracao de icone para a bandeja |

## Notas Tecnicas

- Bots rodam como **subprocessos independentes** (`subprocess.Popen` com `CREATE_NO_WINDOW`)
- PIDs sao rastreados via **lock files** (`.lock`) — limpos automaticamente se o processo nao existir mais
- Status verificado a cada **3 segundos** via `psutil.Process`
- Logs monitorados via **polling** a cada 1 segundo (detecta rotacao de arquivo)
- Acoes de Start/Stop/Restart rodam em **threads separadas** para nao bloquear a UI
- Fechar a janela (X) **minimiza para a bandeja** — sair de verdade pelo menu do tray

---

<p align="center">
  Feito com Python + CustomTkinter
</p>
