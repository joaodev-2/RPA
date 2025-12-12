import os

# --- DADOS DE ACESSO ---
#URL_LOGIN = ""
#USUARIO = ""
#SENHA = "" 

# --- PERFIL ---
DIR_PERFIL = os.path.abspath("./perfil_robo_softexpert")

# --- SELETORES LOGIN ---
SEL_CAMPO_USUARIO = 'input[id="user"]'
SEL_CAMPO_SENHA = 'input[id="password"]'
SEL_BOTAO_ENTRAR = 'button[id="loginButton"]'
SEL_BOTAO_DESCONECTAR = 'button:has-text("Desconectar")' 
SEL_BOTAO_ALERT_CONFIRM = 'button[id="alertConfirm"]'

# --- SELETOR CORRIGIDO DA BARRA DE PESQUISA ---
# Agora pegamos apenas o input 85 que está dentro do container de filtro
# O atributo debounce="100" diferencia ele da barra do menu (que é 250)
SEL_BARRA_PESQUISA = 'input[data-test-id="85"][debounce="100"]'