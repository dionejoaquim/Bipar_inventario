import threading
from datetime import datetime

import pytds

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView


# ============================================================
# CONFIGURAÇÕES DO SQL SERVER
# ALTERE ESTES DADOS
# ============================================================

DB_SERVER = "BRPMW2RS001"
DB_PORT = 1600
DB_DATABASE = "SKYLIGHT"
DB_USER = "wqt657"
DB_PASSWORD = "wqt6571234"

# Nome da tabela criada no SQL Server
DB_TABLE = "dbo.leitura_material"


# ============================================================
# FUNÇÃO DE CONEXÃO
# ============================================================

def conectar_banco():
    return pytds.connect(
        server=DB_SERVER,
        port=DB_PORT,
        database=DB_DATABASE,
        user=DB_USER,
        password=DB_PASSWORD,
        login_timeout=10,
        timeout=10,
        autocommit=False
    )


# ============================================================
# TESTE DE CONEXÃO
# ============================================================

def testar_conexao():
    conexao = None

    try:
        conexao = conectar_banco()
        return True, "Conexão com o banco realizada com sucesso."

    except Exception as erro:
        return False, f"Erro de conexão:\n{erro}"

    finally:
        if conexao:
            conexao.close()


# ============================================================
# SALVAR SIID NO SQL SERVER
# ============================================================

def salvar_siid(box, siid):
    conexao = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        sql = f"""
            INSERT INTO {DB_TABLE}
                (box, siid, data_hora, status)
            VALUES
                (%s, %s, SYSDATETIME(), %s)
        """

        cursor.execute(sql, (box, siid, "OK"))

        # Grava imediatamente no banco
        conexao.commit()

        return True, "SIID salvo com sucesso."

    except Exception as erro:
        if conexao:
            conexao.rollback()

        mensagem = str(erro)

        # Erros comuns de chave única no SQL Server
        if (
            "2601" in mensagem
            or "2627" in mensagem
            or "duplicate" in mensagem.lower()
            or "unique" in mensagem.lower()
        ):
            return False, "Este SIID já foi bipado nesta Box."

        return False, f"Erro ao salvar no banco:\n{erro}"

    finally:
        if conexao:
            conexao.close()


# ============================================================
# TELA PARA BIPAR A BOX
# ============================================================

class TelaBox(BoxLayout):

    def __init__(self, app_principal, **kwargs):
        super().__init__(**kwargs)

        self.app_principal = app_principal

        self.orientation = "vertical"
        self.padding = dp(20)
        self.spacing = dp(15)

        titulo = Label(
            text="BIPAR BOX",
            font_size=dp(27),
            size_hint_y=None,
            height=dp(55)
        )

        instrucoes = Label(
            text="Bipe a Box e pressione ENTER",
            font_size=dp(18),
            size_hint_y=None,
            height=dp(50)
        )

        self.campo_box = TextInput(
            hint_text="Ex.: K06-006-06",
            multiline=False,
            font_size=dp(24),
            size_hint_y=None,
            height=dp(65)
        )

        self.mensagem = Label(
            text="Aguardando leitura da Box.",
            font_size=dp(16)
        )

        self.campo_box.bind(
            on_text_validate=self.abrir_box
        )

        self.add_widget(titulo)
        self.add_widget(instrucoes)
        self.add_widget(self.campo_box)
        self.add_widget(self.mensagem)

        Clock.schedule_once(
            self.focar_campo,
            0.5
        )

    def focar_campo(self, tempo):
        self.campo_box.focus = True

    def abrir_box(self, campo):
        box = campo.text.strip()

        if not box:
            self.mensagem.text = "Leia uma Box válida."
            self.campo_box.focus = True
            return

        self.app_principal.box_atual = box
        self.app_principal.abrir_tela_siid()


# ============================================================
# TELA PARA BIPAR OS SIIDS
# ============================================================

class TelaSIID(BoxLayout):

    def __init__(self, app_principal, box, **kwargs):
        super().__init__(**kwargs)

        self.app_principal = app_principal
        self.box = box
        self.salvando = False

        self.orientation = "vertical"
        self.padding = dp(15)
        self.spacing = dp(10)

        titulo = Label(
            text=f"BOX ATUAL:\n{self.box}",
            font_size=dp(23),
            size_hint_y=None,
            height=dp(85)
        )

        instrucoes = Label(
            text="Bipe cada SIID e pressione ENTER",
            font_size=dp(17),
            size_hint_y=None,
            height=dp(45)
        )

        self.campo_siid = TextInput(
            hint_text="Aguardando SIID...",
            multiline=False,
            font_size=dp(23),
            size_hint_y=None,
            height=dp(65)
        )

        self.mensagem = Label(
            text="Nenhum SIID lido ainda.",
            font_size=dp(16),
            size_hint_y=None,
            height=dp(55)
        )

        self.lista_siid = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None
        )

        self.lista_siid.bind(
            minimum_height=self.lista_siid.setter("height")
        )

        scroll = ScrollView()
        scroll.add_widget(self.lista_siid)

        botao_finalizar = Button(
            text="FINALIZAR BOX",
            font_size=dp(20),
            size_hint_y=None,
            height=dp(70),
            background_color=(0.1, 0.55, 0.2, 1)
        )

        self.campo_siid.bind(
            on_text_validate=self.iniciar_salvamento
        )

        botao_finalizar.bind(
            on_press=self.finalizar_box
        )

        self.add_widget(titulo)
        self.add_widget(instrucoes)
        self.add_widget(self.campo_siid)
        self.add_widget(self.mensagem)
        self.add_widget(scroll)
        self.add_widget(botao_finalizar)

        Clock.schedule_once(
            self.focar_campo,
            0.5
        )

    def focar_campo(self, tempo):
        self.campo_siid.focus = True

    def iniciar_salvamento(self, campo):
        if self.salvando:
            return

        siid = campo.text.strip()

        if not siid:
            self.mensagem.text = "SIID vazio. Faça uma nova leitura."
            self.campo_siid.focus = True
            return

        self.salvando = True
        self.campo_siid.disabled = True
        self.mensagem.text = f"Salvando SIID {siid}..."

        thread = threading.Thread(
            target=self.salvar_em_thread,
            args=(siid,),
            daemon=True
        )

        thread.start()

    def salvar_em_thread(self, siid):
        sucesso, mensagem = salvar_siid(
            self.box,
            siid
        )

        Clock.schedule_once(
            lambda tempo: self.finalizar_salvamento(
                siid,
                sucesso,
                mensagem
            ),
            0
        )

    def finalizar_salvamento(self, siid, sucesso, mensagem):
        self.salvando = False
        self.campo_siid.disabled = False

        if sucesso:
            self.mensagem.text = mensagem
            self.campo_siid.text = ""

            horario = datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
            )

            item = Label(
                text=f"SIID: {siid}  |  {horario}",
                font_size=dp(16),
                size_hint_y=None,
                height=dp(38),
                color=(0.1, 0.7, 0.2, 1)
            )

            self.lista_siid.add_widget(item)

        else:
            # Mantém o SIID no campo para facilitar uma nova tentativa
            self.campo_siid.text = siid
            self.mensagem.text = mensagem

        self.campo_siid.focus = True

    def finalizar_box(self, botao):
        if self.salvando:
            self.mensagem.text = (
                "Aguarde o salvamento do SIID atual."
            )
            return

        self.app_principal.abrir_tela_box()


# ============================================================
# APLICAÇÃO PRINCIPAL
# ============================================================

class AppLeitura(App):

    def build(self):
        self.box_atual = ""

        self.tela_principal = BoxLayout(
            orientation="vertical"
        )

        self.abrir_tela_box()

        return self.tela_principal

    def abrir_tela_box(self):
        self.tela_principal.clear_widgets()

        tela = TelaBox(self)

        self.tela_principal.add_widget(tela)

    def abrir_tela_siid(self):
        self.tela_principal.clear_widgets()

        tela = TelaSIID(
            self,
            self.box_atual
        )

        self.tela_principal.add_widget(tela)

    def on_start(self):
        # Testa o banco sem travar a interface
        thread = threading.Thread(
            target=self.testar_banco_em_thread,
            daemon=True
        )

        thread.start()

    def testar_banco_em_thread(self):
        sucesso, mensagem = testar_conexao()

        print(mensagem)

        if not sucesso:
            Clock.schedule_once(
                lambda tempo: self.mostrar_erro_inicial(mensagem),
                0
            )

    def mostrar_erro_inicial(self, mensagem):
        # A tela continuará aberta, mas o erro aparecerá no terminal.
        print(mensagem)


# ============================================================
# INICIAR APLICAÇÃO
# ============================================================

if __name__ == "__main__":
    AppLeitura().run()
