"""
Gerador de senhas (back-end + front-end em um único arquivo).

Como funciona:
  - O back-end (Flask) recebe uma lista de IMEIs e devolve a senha de cada um.
  - O front-end (HTML/CSS/JS) fica dentro da variável PAGINA e é entregue na rota "/".
  - A resposta é mostrada no formato de comando:  PRLOCK,SENHA,0#  (abrir)
                                                  PRLOCK,SENHA,1#  (fechar)

Rodar localmente:
    pip install -r requirements.txt
    python app.py
    -> abra http://localhost:5000

Na Vercel:
    O arquivo precisa se chamar app.py e a variável do Flask precisa se chamar "app".
"""
import hashlib

from flask import Flask, jsonify, request

# Cria a aplicação Flask. A Vercel procura exatamente por esta variável "app".
app = Flask(__name__)


def gerar_codigo(base: str) -> str:
    """Recebe o IMEI como texto e devolve a senha de 6 dígitos."""
    # 1. Calcula o MD5 do texto (codificado em UTF-8) e pega em formato hexadecimal
    md5_hex = hashlib.md5(base.encode("utf-8")).hexdigest()

    # 2. Converte o hexadecimal em inteiro (base 16) e pega o resto da divisão por 1.000.000
    resultado = int(md5_hex, 16) % 1_000_000

    # 3. Garante 6 dígitos, completando com zeros à esquerda (ex.: 12345 -> 012345)
    return str(resultado).zfill(6)


# ---------------------------------------------------------------------------
# FRONT-END: página HTML completa guardada como texto
# ---------------------------------------------------------------------------
PAGINA = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gerador de Senhas</title>
<style>
  /* Estilo geral da página */
  body { font-family: system-ui, sans-serif; background:#f3f4f6; margin:0; padding:24px; color:#111; }
  .wrap { max-width:720px; margin:auto; }   /* centraliza o conteúdo */
  h1 { font-size:22px; }

  /* Os dois retângulos: caixa de entrada (textarea) e caixa de resposta (.saida) */
  textarea, .saida { width:100%; box-sizing:border-box; min-height:180px; padding:12px; border:2px solid #c7cbd1;
    border-radius:10px; font-family:ui-monospace, monospace; font-size:15px; background:#fff; }
  .saida { white-space:pre-wrap; overflow:auto; }  /* mantém as quebras de linha da resposta */

  /* Botões */
  button { margin:12px 8px 12px 0; padding:10px 18px; border:0; border-radius:8px; background:#2563eb;
    color:#fff; font-size:15px; cursor:pointer; }
  button.sec { background:#6b7280; }   /* botões secundários (cinza) */
  label { font-weight:600; display:block; margin-top:8px; }

  /* Seletor ABRIR / FECHAR: o botão ativo fica destacado */
  .modo { display:flex; gap:8px; margin:8px 0; }
  .modo button { margin:0; background:#e5e7eb; color:#111; border:2px solid transparent; }
  .modo button.ativo { background:#2563eb; color:#fff; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Gerador de Senhas</h1>

  <!-- Retângulo de ENTRADA: o usuário cola os IMEIs, um por linha -->
  <label for="entrada">IMEIs (um por linha)</label>
  <textarea id="entrada" placeholder="866557080450242&#10;866557080562137"></textarea>

  <!-- Botões de ação -->
  <button onclick="gerar()">GERAR TODAS AS SENHAS</button>
  <button class="sec" onclick="copiar()">Copiar resultado</button>
  <button class="sec" onclick="limpar()">Limpar</button>

  <!-- Seletor do comando: ABRIR usa 0 no final, FECHAR usa 1 -->
  <label>Comando</label>
  <div class="modo">
    <button id="btn-abrir" class="ativo" onclick="definirModo(0)">ABRIR (0)</button>
    <button id="btn-fechar" onclick="definirModo(1)">FECHAR (1)</button>
  </div>

  <!-- Retângulo de RESPOSTA: aqui aparece PRLOCK,"SENHA",0# -->
  <label>Resposta</label>
  <div id="saida" class="saida"></div>
</div>

<script>
let resultados = [];  // guarda as senhas geradas para poder trocar ABRIR/FECHAR sem recalcular
let modo = 0;         // 0 = abrir, 1 = fechar

// Monta a resposta: uma linha de comando para cada senha
function mostrar() {
  const saida = document.getElementById("saida");
  saida.textContent = resultados
    .map(d => 'PRLOCK,"' + d.senha + '",' + modo + '#')
    .join("\\n");
}

// Troca entre ABRIR (0) e FECHAR (1) e atualiza a resposta na hora
function definirModo(novo) {
  modo = novo;
  document.getElementById("btn-abrir").classList.toggle("ativo", novo === 0);
  document.getElementById("btn-fechar").classList.toggle("ativo", novo === 1);
  mostrar();
}

// Envia os IMEIs para o back-end e mostra os comandos na caixa de resposta
async function gerar() {
  const saida = document.getElementById("saida");
  try {
    // Chama a rota POST /api/gerar mandando o texto digitado
    const r = await fetch("/api/gerar", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({imeis: document.getElementById("entrada").value})
    });
    resultados = await r.json();   // lista de {imei, senha}

    if (resultados.length) {
      mostrar();
    } else {
      saida.textContent = "Nenhum IMEI informado.";
    }
  } catch (e) {
    // Se o servidor não responder, avisa o usuário
    saida.textContent = "Erro ao falar com o servidor.";
  }
}

// Copia o conteúdo da caixa de resposta para a área de transferência
function copiar() {
  navigator.clipboard.writeText(document.getElementById("saida").textContent);
}

// Esvazia as duas caixas
function limpar() {
  resultados = [];
  document.getElementById("entrada").value = "";
  document.getElementById("saida").textContent = "";
}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# ROTAS DO BACK-END
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    """Entrega a página (front-end) quando o usuário abre o site."""
    return PAGINA


@app.post("/api/gerar")
def gerar():
    """Recebe {"imeis": "texto com um IMEI por linha"} e devolve a lista de senhas."""
    # Lê o JSON enviado pelo front-end (se vier vazio/inválido, usa texto vazio)
    texto = (request.get_json(silent=True) or {}).get("imeis", )

    # Para cada linha: tira espaços das pontas, ignora linhas vazias e calcula a senha.
    # Cada IMEI é calculado de forma independente e sempre tratado como texto.
    resultados = [
        {"imei": linha.strip(), "senha": gerar_codigo(linha.strip())}
        for linha in texto.splitlines()
        if linha.strip()
    ]
    return jsonify(resultados)


# Só roda o servidor local quando você executa "python app.py".
# Na Vercel este bloco é ignorado: ela usa a variável "app" diretamente.
if __name__ == "__main__":
    app.run(debug=True, port=5000)
