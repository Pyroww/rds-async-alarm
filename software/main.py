import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
from datetime import datetime
import threading
import time

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

COR_VERDE_SEGURO = "#008000"   
COR_AMARELA_AVISO = "#DAA520"  
COR_VERMELHA_CRITICO = "#B22222"
COR_FUNDO_LOG = "#F5F5F5"

class CommandCenterAlarme(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Command Center RDS - Sistema de alarme")
        self.geometry("1150x690")
        self.minsize(1050, 650)

        self.porta_serial = None
        self.modo_atual = "DESCONHECIDO"
        self.id_alvo_selecionado = None
        
        self.dados_hierarquia = {
            "00000": {"estado": "BRASIL", "municipio": "TODOS", "bairro": "ALERTA NACIONAL", "display": "[00000] ALERTA GERAL (NACIONAL)"}
        }

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1) 
        self.grid_columnconfigure(2, weight=2) 
        self.grid_rowconfigure(0, weight=1)

        self.setup_estilos_ttk()
        self.setup_sidebar()
        
        self.frame_meio = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_meio.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.frame_direita = ctk.CTkFrame(self, corner_radius=10)
        self.frame_direita.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        
        self.setup_conexao(self.frame_meio)
        self.setup_cadastro_hierarquico(self.frame_meio)
        
        # O Novo Painel de Gravação na Placa
        self.setup_provisionamento(self.frame_meio)
        
        self.setup_disparo_alarmes(self.frame_meio)
        self.setup_logs()

        self.atualizar_arvore()
        self.log_dinamico("=== Sistema de Alarme Iniciado ===")

    def setup_estilos_ttk(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=COR_FUNDO_LOG, foreground="black", rowheight=25, fieldbackground=COR_FUNDO_LOG, bordercolor="#d0d0d0", borderwidth=0)
        style.map('Treeview', background=[('selected', '#3b8ed0')])

    def setup_sidebar(self):
        self.frame_sidebar = ctk.CTkFrame(self, corner_radius=10)
        self.frame_sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.frame_sidebar.grid_rowconfigure(2, weight=1)
        self.frame_sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.frame_sidebar, text="Georreferenciamento de Zonas", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, pady=(10, 5))

        self.entry_busca = ctk.CTkEntry(self.frame_sidebar, placeholder_text="Pesquisar região ou ID...")
        self.entry_busca.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.entry_busca.bind("<KeyRelease>", self.filtrar_arvore)

        tree_container = ctk.CTkFrame(self.frame_sidebar, fg_color="transparent")
        tree_container.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="nsew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_container, columns=("ID",), show="tree", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.column("#0", width=400, minwidth=350, stretch=True)

        vsb = ctk.CTkScrollbar(tree_container, orientation="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ctk.CTkScrollbar(tree_container, orientation="horizontal", command=self.tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def setup_conexao(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(frame, text="Antena ou Sirene Local:", font=ctk.CTkFont(weight="bold")).pack(pady=(5,0))
        self.combo_portas = ctk.CTkComboBox(frame, values=self.listar_portas())
        self.combo_portas.pack(pady=5, padx=10, fill="x")
        self.btn_conectar = ctk.CTkButton(frame, text="CONECTAR DISPOSITIVO", command=self.conectar_serial, fg_color="#3b8ed0")
        self.btn_conectar.pack(pady=(0,10), padx=10, fill="x")

    def setup_cadastro_hierarquico(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=5)
        ctk.CTkLabel(frame, text="1. Mapeamento Lógico (Software)", font=ctk.CTkFont(weight="bold")).pack(pady=(5,5))

        linha1 = ctk.CTkFrame(frame, fg_color="transparent")
        linha1.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(linha1, text="Est:", width=40, anchor="w").pack(side="left")
        self.entry_estado = ctk.CTkEntry(linha1, width=50)
        self.entry_estado.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(linha1, text="ID (0-99999):", width=80, anchor="w").pack(side="left")
        self.entry_id_no = ctk.CTkEntry(linha1, width=60)
        self.entry_id_no.pack(side="left")

        linha2 = ctk.CTkFrame(frame, fg_color="transparent")
        linha2.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(linha2, text="Mun:", width=40, anchor="w").pack(side="left")
        self.entry_municipio = ctk.CTkEntry(linha2)
        self.entry_municipio.pack(side="left", fill="x", expand=True)

        linha3 = ctk.CTkFrame(frame, fg_color="transparent")
        linha3.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(linha3, text="Bai:", width=40, anchor="w").pack(side="left")
        self.entry_bairro = ctk.CTkEntry(linha3)
        self.entry_bairro.pack(side="left", fill="x", expand=True)

        self.btn_cadastrar = ctk.CTkButton(frame, text="Adicionar Região à Árvore", command=self.adicionar_no_geografico, fg_color="#555555")
        self.btn_cadastrar.pack(pady=10, padx=10, fill="x")

    def setup_provisionamento(self, parent):
        self.frame_prov = ctk.CTkFrame(parent)
        self.frame_prov.pack(fill="x", pady=5)
        ctk.CTkLabel(self.frame_prov, text="⚙️ 2. Provisionamento (Sirene USB)", font=ctk.CTkFont(weight="bold")).pack(pady=(5,5))

        linha1 = ctk.CTkFrame(self.frame_prov, fg_color="transparent")
        linha1.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(linha1, text="ID Estado:", width=60).pack(side="left")
        self.entry_prov_est = ctk.CTkEntry(linha1, width=50)
        self.entry_prov_est.pack(side="left", padx=(0,10))
        ctk.CTkLabel(linha1, text="ID Mun:", width=50).pack(side="left")
        self.entry_prov_mun = ctk.CTkEntry(linha1, width=50)
        self.entry_prov_mun.pack(side="left")

        linha2 = ctk.CTkFrame(self.frame_prov, fg_color="transparent")
        linha2.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(linha2, text="ID Bairro:", width=60).pack(side="left")
        self.entry_prov_bai = ctk.CTkEntry(linha2, width=50)
        self.entry_prov_bai.pack(side="left")

        self.btn_gravar_ids = ctk.CTkButton(self.frame_prov, text="💾 Gravar IDs na Placa", state="disabled", command=self.gravar_ids_na_placa, fg_color="#555555")
        self.btn_gravar_ids.pack(pady=10, padx=10, fill="x")

    def setup_disparo_alarmes(self, parent):
        self.frame_disparo = ctk.CTkFrame(parent)
        self.frame_disparo.pack(fill="x", pady=5)
        ctk.CTkLabel(self.frame_disparo, text="3. Disparo de Sirenes (Antena USB)", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(5,5))

        self.lbl_alvo = ctk.CTkLabel(self.frame_disparo, text="Alvo: NENHUM", text_color=COR_VERMELHA_CRITICO, font=ctk.CTkFont(weight="bold"))
        self.lbl_alvo.pack(pady=(0,5), padx=10)
        
        self.btn_alerta_normal = ctk.CTkButton(self.frame_disparo, text="🟢 ALL CLEAR (SEGURO)", fg_color=COR_VERDE_SEGURO, hover_color="#006400", state="disabled", command=lambda: self.enviar_alarme("1"))
        self.btn_alerta_normal.pack(pady=2, padx=10, fill="x")

        self.btn_alerta_aviso = ctk.CTkButton(self.frame_disparo, text="🟡 AVISO PREVENTIVO", fg_color=COR_AMARELA_AVISO, hover_color="#B8860B", state="disabled", command=lambda: self.enviar_alarme("2"))
        self.btn_alerta_aviso.pack(pady=2, padx=10, fill="x")

        self.btn_alerta_critico = ctk.CTkButton(self.frame_disparo, text="🔴 EVACUAÇÃO CRÍTICA", fg_color=COR_VERMELHA_CRITICO, hover_color="#8B0000", state="disabled", command=lambda: self.enviar_alarme("3"))
        self.btn_alerta_critico.pack(pady=2, padx=10, fill="x")

        self.btn_silenciar = ctk.CTkButton(self.frame_disparo, text="⏹ SILENCIAR SIRENES", fg_color="#333333", hover_color="#000000", state="disabled", command=lambda: self.enviar_alarme("0"))
        self.btn_silenciar.pack(pady=(10,10), padx=10, fill="x")

    def setup_logs(self):
        self.frame_direita.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.frame_direita, text="Monitoramento RDS de Borda", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        self.log_area = ctk.CTkTextbox(self.frame_direita, font=ctk.CTkFont(family="Consolas", size=13), state="disabled", wrap="word", fg_color=COR_FUNDO_LOG, text_color="black")
        self.log_area.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

    def listar_portas(self):
        portas = serial.tools.list_ports.comports()
        return [p.device for p in portas] or ["Nenhuma porta encontrada"]

    def log_dinamico(self, mensagem, color="black"):
        timestamp = datetime.now().strftime("[%H:%M:%S] ")
        self.log_area.configure(state="normal")
        self.log_area.configure(text_color=color) 
        self.log_area.insert("end", timestamp + mensagem + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    # ==========================================
    # GERENCIAMENTO DE ESTADO DA UI (A Mágica)
    # ==========================================
    def gerenciar_botoes_por_dispositivo(self, modo):
        if modo == "DESCONHECIDO":
            # Bloqueia Tudo
            self.btn_gravar_ids.configure(state="disabled", fg_color="#555555")
            self.entry_prov_est.configure(state="disabled")
            self.entry_prov_mun.configure(state="disabled")
            self.entry_prov_bai.configure(state="disabled")
            
            self.btn_alerta_normal.configure(state="disabled")
            self.btn_alerta_aviso.configure(state="disabled")
            self.btn_alerta_critico.configure(state="disabled")
            self.btn_silenciar.configure(state="disabled")
            
        elif modo == "TRANSMISSOR":
            # Plugar a Antena libera o DISPARO, mas bloqueia o Provisionamento
            self.btn_gravar_ids.configure(state="disabled", fg_color="#555555")
            self.entry_prov_est.configure(state="disabled")
            self.entry_prov_mun.configure(state="disabled")
            self.entry_prov_bai.configure(state="disabled")
            
            self.btn_alerta_normal.configure(state="normal")
            self.btn_alerta_aviso.configure(state="normal")
            self.btn_alerta_critico.configure(state="normal")
            self.btn_silenciar.configure(state="normal")
            
        elif modo == "RECEPTOR":
            # Plugar a Sirene libera a GRAVAÇÃO DE IDs, mas bloqueia o Disparo
            self.entry_prov_est.configure(state="normal")
            self.entry_prov_mun.configure(state="normal")
            self.entry_prov_bai.configure(state="normal")
            self.btn_gravar_ids.configure(state="normal", fg_color="#228B22", hover_color="#006400")
            
            self.btn_alerta_normal.configure(state="disabled")
            self.btn_alerta_aviso.configure(state="disabled")
            self.btn_alerta_critico.configure(state="disabled")
            self.btn_silenciar.configure(state="disabled")

    # ==========================================
    # LÓGICA DE CADASTRO E DISPARO
    # ==========================================
    def adicionar_no_geografico(self):
        estado = self.entry_estado.get().strip().upper()
        municipio = self.entry_municipio.get().strip().upper()
        bairro = self.entry_bairro.get().strip().upper()
        id_no = self.entry_id_no.get().strip()

        if not estado:
            self.log_dinamico("⚠️ Preencha pelo menos o Estado.", "orange")
            return
        if not id_no.isdigit() or len(id_no) > 5:
            self.log_dinamico("⚠️ ID inválido. Use números de 1 a 99999.", "orange")
            return

        id_formatado = f"{int(id_no):05d}"
        
        if not municipio:
            municipio = "TODOS OS MUNICÍPIOS"
            bairro = "TODOS OS BAIRROS"
            display_text = f"[{id_formatado}] {estado} (Alerta Estadual)"
        elif not bairro:
            bairro = "TODOS OS BAIRROS"
            display_text = f"[{id_formatado}] {municipio} (Alerta Municipal)"
        else:
            display_text = f"[{id_formatado}] {bairro}"

        self.dados_hierarquia[id_formatado] = {"estado": estado, "municipio": municipio, "bairro": bairro, "display": display_text}
        
        self.atualizar_arvore()
        self.entry_bairro.delete(0, 'end')
        self.entry_municipio.delete(0, 'end')
        self.entry_id_no.delete(0, 'end')
        self.log_dinamico(f"🗺️ Nó Lógico {id_formatado} salvo no software.", "blue")

    def filtrar_arvore(self, event=None):
        self.atualizar_arvore(self.entry_busca.get().strip().upper())

    def atualizar_arvore(self, termo_busca=""):
        self.tree.delete(*self.tree.get_children())
        for id_no, dados in self.dados_hierarquia.items():
            est = dados["estado"]
            mun = dados["municipio"]
            bai = dados["bairro"]
            display = dados["display"]

            texto_concat = f"{est} {mun} {bai} {id_no}".upper()
            if termo_busca and termo_busca not in texto_concat: continue 

            if id_no == "00000":
                self.tree.insert("", "end", iid="ID_00000", text=display, values=("00000",), open=True)
                continue

            iid_est = f"EST_{est}"
            if not self.tree.exists(iid_est): self.tree.insert("", "end", iid=iid_est, text=est, open=True)

            if mun == "TODOS OS MUNICÍPIOS":
                self.tree.insert(iid_est, "end", iid=f"ID_{id_no}", text=display, values=(id_no,))
            else:
                iid_mun = f"MUN_{est}_{mun}"
                if not self.tree.exists(iid_mun): self.tree.insert(iid_est, "end", iid=iid_mun, text=mun, open=True)
                self.tree.insert(iid_mun, "end", iid=f"ID_{id_no}", text=display, values=(id_no,))

    def on_tree_select(self, event):
        selecao = self.tree.selection()
        if selecao:
            item = selecao[0]
            valores = self.tree.item(item, "values")
            if valores:
                self.id_alvo_selecionado = valores[0]
                texto_no = self.tree.item(item, "text")
                self.lbl_alvo.configure(text=f"Alvo: {texto_no}", text_color="black")
                
                # Preenche os campos do provisionamento automaticamente para facilitar
                self.entry_prov_est.delete(0, 'end'); self.entry_prov_mun.delete(0, 'end'); self.entry_prov_bai.delete(0, 'end')
                if self.id_alvo_selecionado != "00000":
                    self.entry_prov_bai.insert(0, self.id_alvo_selecionado)
            else:
                self.id_alvo_selecionado = None
                self.lbl_alvo.configure(text="⚠️ Selecione um nó [XXXXX]", text_color="orange")

    # ==========================================
    # LÓGICA DE PROVISIONAMENTO E SERIAL
    # ==========================================
    def gravar_ids_na_placa(self):
        est = self.entry_prov_est.get().strip()
        mun = self.entry_prov_mun.get().strip()
        bai = self.entry_prov_bai.get().strip()

        if not est.isdigit() or not mun.isdigit() or not bai.isdigit():
            self.log_dinamico("⚠️ Erro: Os IDs devem ser apenas números.", "orange")
            return

        est_fmt = f"{int(est):05d}"
        mun_fmt = f"{int(mun):05d}"
        bai_fmt = f"{int(bai):05d}"

        payload = f"GRAVAR_IDS:{est_fmt},{mun_fmt},{bai_fmt}\n"
        if self.porta_serial and self.porta_serial.is_open:
            try:
                self.porta_serial.write(payload.encode('utf-8'))
                self.porta_serial.flush()
                self.log_dinamico(f"💾 Enviando config via USB: {est_fmt} (Est) | {mun_fmt} (Mun) | {bai_fmt} (Bai)", "blue")
            except Exception as e:
                self.log_dinamico(f"❌ Erro ao gravar: {e}", "red")

    def enviar_alarme(self, comando):
        if not self.id_alvo_selecionado:
            self.log_dinamico("⚠️ ERRO: Clique em uma Região na árvore à esquerda antes de disparar.", "orange")
            return
            
        payload = f"{self.id_alvo_selecionado}{comando}\n"
        if self.porta_serial and self.porta_serial.is_open:
            try:
                self.porta_serial.write(payload.encode('utf-8'))
                self.porta_serial.flush()
                self.log_dinamico(f"📡 RADIODIFUSÃO RDS: Pacote enviado ao ar -> [{payload.strip()}]", "black")
            except Exception as e:
                self.log_dinamico(f"❌ Erro de transmissão: {e}", "red")

    def conectar_serial(self):
        if self.porta_serial and self.porta_serial.is_open:
            self.porta_serial.close()
            self.log_dinamico("Conexão encerrada.")
            self.btn_conectar.configure(text="CONECTAR DISPOSITIVO", fg_color="#3b8ed0")
            self.combo_portas.configure(state="normal")
            self.modo_atual = "DESCONHECIDO"
            self.gerenciar_botoes_por_dispositivo(self.modo_atual)
            return

        porta_nome = self.combo_portas.get()
        if porta_nome == "Nenhuma porta encontrada" or not porta_nome:
            self.log_dinamico("⚠️ Selecione uma porta COM válida.", "orange")
            return

        try:
            self.porta_serial = serial.Serial(porta_nome, 115200, timeout=0.1)
            self.porta_serial.setDTR(False); self.porta_serial.setRTS(False)

            self.btn_conectar.configure(state="disabled", text="CONECTANDO...")
            self.combo_portas.configure(state="disabled")
            self.gerenciar_botoes_por_dispositivo("DESCONHECIDO") # Garante bloqueio
            self.log_dinamico(f"✅ Interrogando hardware na porta {porta_nome}...")

            threading.Thread(target=self.ler_serial_thread, daemon=True).start()
            threading.Thread(target=self.enviar_ping_id, daemon=True).start()

        except Exception as e:
            self.log_dinamico(f"❌ Falha: {e}", "red")
            self.btn_conectar.configure(state="normal", text="CONECTAR DISPOSITIVO")
            self.combo_portas.configure(state="normal")

    def enviar_ping_id(self):
        time.sleep(2.0) 
        if self.porta_serial and self.porta_serial.is_open:
            self.porta_serial.reset_input_buffer()
            self.porta_serial.reset_output_buffer()
            self.porta_serial.write("PING_ID\n".encode('utf-8'))
            self.porta_serial.flush()

    def ler_serial_thread(self):
        while self.porta_serial and self.porta_serial.is_open:
            try:
                if self.porta_serial.in_waiting > 0:
                    linha = self.porta_serial.readline().decode('utf-8', errors='ignore').strip()
                    if linha:
                        self.after(0, self.processar_linha_serial, linha)
            except Exception:
                break

    def processar_linha_serial(self, linha):
        if self.modo_atual == "DESCONHECIDO":
            if "SYS_ID:TRANSMISSOR" in linha or "TX: Comando" in linha:
                self.modo_atual = "TRANSMISSOR"
                self.gerenciar_botoes_por_dispositivo(self.modo_atual)
                self.log_dinamico("🚀 TX: Antena de Transmissão Detectada. Disparos liberados.", COR_VERDE_SEGURO)
                self.btn_conectar.configure(state="normal", text="DESCONECTAR", fg_color=COR_VERMELHA_CRITICO)
                return 
            
            elif "SYS_ID:RECEPTOR" in linha:
                self.modo_atual = "RECEPTOR"
                self.gerenciar_botoes_por_dispositivo(self.modo_atual)
                self.log_dinamico("🎧 RX: Sirene Local detectada. Modo de Provisionamento habilitado.", "blue")
                self.btn_conectar.configure(state="normal", text="DESCONECTAR", fg_color=COR_VERMELHA_CRITICO)
                return

        prefixo = ""
        # Destaca as respostas de sucesso da placa no log
        if "EEPROM_OK" in linha:
            self.log_dinamico("✅ SUCESSO: Os novos IDs foram salvos na memória física da sirene!", COR_VERDE_SEGURO)
            return

        self.log_dinamico(prefixo + linha)

if __name__ == "__main__":
    app = CommandCenterAlarme()
    app.mainloop()