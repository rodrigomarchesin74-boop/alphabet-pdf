"""
ALPHAbet Web - Versão 4.1
Interface web com ABA DE DATAS para facilitar alterações!
"""

from flask import Flask, render_template_string, request, jsonify
import os
import json
import unicodedata
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pathlib import Path

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ============================================================================
# DATAS CONFIGURÁVEIS (Salvas em arquivo JSON)
# ============================================================================

DATES_FILE = "datas_configuracao.json"

# Datas padrão
DEFAULT_DATES = {
    "NP1_inicio": "15/09/2025",
    "NP1_fim": "27/09/2025",
    "NP2_inicio": "03/11/2025",
    "NP2_fim": "14/11/2025",
    "SUB_inicio": "17/11/2025",
    "SUB_fim": "25/11/2025",
    "EXAME_inicio": "04/12/2025",
    "EXAME_fim": "12/12/2025",
    "PIM_prazo": "30/10/2025",
    "GERAL_prazo": "20/10/2025",
    "atendimento_info": "quintas-feiras, das 18h30 às 21h00",
    "download_path": ""
}

def load_dates():
    """Carrega datas do arquivo ou usa padrão"""
    if os.path.exists(DATES_FILE):
        try:
            with open(DATES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return DEFAULT_DATES
    return DEFAULT_DATES

def save_dates(dates):
    """Salva datas em arquivo"""
    with open(DATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(dates, f, ensure_ascii=False, indent=2)

CURRENT_DATES = load_dates()

# ============================================================================
# FUNÇÕES DE PDF
# ============================================================================

def wrap_text(text, c, max_width, font_name, font_size):
    """Quebra o texto em linhas"""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if c.stringWidth(test_line, font_name, font_size) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

def draw_page_footer(c, page_num, width, height):
    """Desenha número da página"""
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 50, 30, f"Página {page_num}")

def generate_study_report(data):
    """Gera o PDF com melhor tratamento de caminhos"""
    # Limpar nome do aluno removendo acentos e caracteres especiais
    student_name = data.get('student_name', 'Aluno')
    # Remover acentos
    student_name_nfd = unicodedata.normalize('NFD', student_name)
    student_name_clean = ''.join(char for char in student_name_nfd if unicodedata.category(char) != 'Mn')
    # Remover caracteres especiais
    student_name_clean = student_name_clean.replace(' ', '_').replace('/', '_').replace('\\', '_').replace('(', '').replace(')', '')
    
    # Usar a pasta especificada ou pasta atual
    download_path = data.get('download_path', '').strip()
    output_filename = None
    
    # Tentar usar a pasta especificada
    if download_path:
        try:
            # Verificar se a pasta existe
            if os.path.isdir(download_path):
                # Tentar criar o arquivo no caminho especificado
                test_filename = os.path.join(download_path, f"DP_{student_name_clean}.pdf")
                # Testar se consegue escrever na pasta
                test_file = os.path.join(download_path, ".test_write")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                output_filename = test_filename
            else:
                print(f"Aviso: Pasta não encontrada: {download_path}")
        except Exception as e:
            print(f"Aviso: Erro ao acessar pasta ({download_path}): {e}")
    
    # Se não conseguiu usar a pasta especificada, usar pasta padrão
    if not output_filename:
        # Tentar usar Downloads do usuário
        try:
            if os.name == 'nt':  # Windows
                downloads_path = os.path.expanduser("~\\Downloads")
            else:  # Linux/Mac
                downloads_path = os.path.expanduser("~/Downloads")
            
            if os.path.isdir(downloads_path):
                output_filename = os.path.join(downloads_path, f"DP_{student_name_clean}.pdf")
            else:
                output_filename = f"DP_{student_name_clean}.pdf"
        except:
            output_filename = f"DP_{student_name_clean}.pdf"
    
    c = canvas.Canvas(output_filename, pagesize=A4)
    
    width, height = A4
    page_num = 1
    
    # Cabeçalho
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, "Regime de Adaptação/Dependência (AD/DP)")
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 70, "Programa de Estudo")
    
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 110, "Aluno/RA/Curso/Grade:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(180, height - 110, f"{data.get('student_name', 'N/A')}")
    
    c.setFont("Helvetica", 11)
    regime_str = "Sim" if data.get("regime_grade") else "Não"
    c.drawString(50, height - 125, f"Participa do regime de grade? {regime_str}")
    c.drawString(50, height - 140, f"Possui disciplinas para cumprir em semestre(s) subsequente(s)? {'Sim' if data.get('has_subsequent_semester') else 'Não'}")
    
    y_position = height - 155
    
    if data.get("has_subsequent_semester"):
        y_position -= 15
        note_text = (
            "ATENÇÃO!! Em conformidade às Diretrizes Curriculares da UNIP, você terá disciplinas em AD/DP para cumprir neste e no(s) próximo(s) semestre(s).\n"
            "As indicações a seguir correspondem ao conteúdo a ser integralizado NESTE SEMESTRE.\n"
            "Para o(s) próximo(s), você deverá entrar em contato com a Coordenação, para receber novas instruções."
        )
        c.setFont("Helvetica-Oblique", 12)
        for line_text in note_text.split("\n"):
            wrapped = wrap_text(line_text, c, width - 100, "Helvetica-Oblique", 12)
            for line in wrapped:
                c.drawString(50, y_position, line)
                y_position -= 15
                if y_position < 50:
                    draw_page_footer(c, page_num, width, height)
                    c.showPage()
                    page_num += 1
                    y_position = height - 50
        c.setFont("Helvetica", 12)
        y_position -= 10
    
    y_position -= 10
    is_regime_grade = data.get("regime_grade", False)
    
    # Customizações por tarefa
    ava_custom = []
    if data.get("AVA_disciplines"):
        ava_custom.append("Disciplina(s): " + ", ".join(data["AVA_disciplines"]) + ".")
        
    if is_regime_grade:
        ava_custom.extend([
            "Acessar Área do Aluno/AVA/Conteúdos Acadêmicos/Minhas Disciplinas.",
            "Para NP1, responder, salvar e ENVIAR TODOS os questionários de TODAS as unidades.",
            "Para NP2, SUB e EXAME, agendar as provas de cada disciplina no sistema e realizá-las PRESENCIALMENTE no Laboratório de Informática.",
            "O aluno deverá realizar o EXAME apenas se a Média Semestral (MS) for inferior a 7,0 (sete).",
        ])
        # Adicionar datas
        ava_custom.append(f"NP1: de {data.get('NP1_inicio', CURRENT_DATES['NP1_inicio'])} a {data.get('NP1_fim', CURRENT_DATES['NP1_fim'])}.")
        ava_custom.append(f"NP2: de {data.get('NP2_inicio', CURRENT_DATES['NP2_inicio'])} a {data.get('NP2_fim', CURRENT_DATES['NP2_fim'])}.")
        ava_custom.append(f"SUB: de {data.get('SUB_inicio', CURRENT_DATES['SUB_inicio'])} a {data.get('SUB_fim', CURRENT_DATES['SUB_fim'])}.")
        ava_custom.append(f"EXAME: de {data.get('EXAME_inicio', CURRENT_DATES['EXAME_inicio'])} a {data.get('EXAME_fim', CURRENT_DATES['EXAME_fim'])}.")
    else:
        ava_custom.extend([
            "Acessar Área do Aluno/AVA/Conteúdos Acadêmicos/Minhas Disciplinas.",
            "Responder, salvar e ENVIAR TODOS os questionários de TODAS as unidades.",
            "A nota dos exercícios realizados será replicada para NP1 e NP2.",
            "Para fins de aprovação, o aluno deve alcançar uma média (nota) igual ou superior a 5,0 (cinco)."
        ])
    
    pim_custom = []
    if data.get("PIM_disciplines"):
        pim_custom.append("Disciplina(s): " + ", ".join(data["PIM_disciplines"]) + ".")
        
    if is_regime_grade:
        pim_custom.extend([
            "Elaborar o trabalho, conforme o Manual anexo.",
            "O trabalho deve ser DIGITADO conforme as normas da ABNT.",
            "Após o término da redação, CONVERTER o(s) arquivo(s) para o formato PDF.",
            "Enviar o conteúdo elaborado para: rodrigo.oliveira@docente.unip.br",
            "Prazo: 30/10/2025.",
        ])
    else:
        pim_custom.extend([
            "Elaborar o trabalho, conforme o Manual anexo.",
            "O trabalho deve ser DIGITADO conforme as normas da ABNT.",
            "Após o término da redação, CONVERTER o(s) arquivo(s) para o formato PDF.",
            "Enviar o conteúdo elaborado para: rodrigo.oliveira@docente.unip.br"
        ])
    
    ed_custom = []
    if data.get("ED_disciplines"):
        ed_custom.append("Disciplina(s): " + ", ".join(data["ED_disciplines"]) + ".")
    ed_custom.extend([
        "Responder TODAS as questões (35) de cada módulo que estiver em AD/DP.",
        "Acertar, para fins de aprovação, pelo menos 10 questões para cada módulo que estiver em AD/DP."
    ])
    
    online_custom = []
    if data.get("ONLINE_disciplines"):
        online_custom.append("Disciplina(s): " + ", ".join(data["ONLINE_disciplines"]) + ".")
    if is_regime_grade:
        online_custom.extend([
            "Atenção à plataforma de ACESSO para responder estas disciplinas, que é DIFERENTE das disciplinas AVA.",
            "Acessar Área do Aluno/Disciplinas On-line.",
            "Responder TODOS OS MÓDULOS DE QUESTÕES.",
        ])
        online_custom.append(f"NP1: de {data.get('NP1_inicio', CURRENT_DATES['NP1_inicio'])} a {data.get('NP1_fim', CURRENT_DATES['NP1_fim'])}.")
        online_custom.append(f"NP2: de {data.get('NP2_inicio', CURRENT_DATES['NP2_inicio'])} a {data.get('NP2_fim', CURRENT_DATES['NP2_fim'])}.")
    else:
        online_custom.extend([
            "Atenção à plataforma de ACESSO para responder estas disciplinas.",
            "Acessar Área do Aluno/Disciplinas On-line.",
            "Responder TODOS OS MÓDULOS DE QUESTÕES."
        ])
    
    online_especial_custom = []
    if data.get("ONLINE_ESPECIAL_disciplines"):
        online_especial_custom.append("Disciplina(s): " + ", ".join(data["ONLINE_ESPECIAL_disciplines"]) + ".")
    online_especial_custom.extend([
        "Acessar Área do Aluno/AVA/Conteúdos Acadêmicos/Minhas Disciplinas.",
        "Responder, salvar e ENVIAR TODOS os questionários de TODAS as unidades.",
        "A nota dos exercícios realizados será replicada para NP1 e NP2."
    ])
    
    optativa_custom = []
    if data.get("OPTATIVA_disciplines"):
        optativa_custom.append("Disciplina(s): " + ", ".join(data["OPTATIVA_disciplines"]) + ".")
    optativa_custom.extend([
        "Acessar Área do Aluno/AVA/Conteúdos Acadêmicos/Minhas Disciplinas.",
        "Para NP1, responder, salvar e ENVIAR TODOS os questionários de TODAS as unidades."
    ])
    
    task_details = {
        "AC": "Carga horária exigida: 100 horas. A entrega das AC é feita on-line, exclusivamente via Área do Aluno/AC.",
        "EXT": "Carga horária exigida: 210 horas. A entrega das Atividades de Extensão é feita on-line, exclusivamente via Área do Aluno/EXT.",
        "AVA": "Disciplina(s) AVA",
        "ONLINE": "Disciplina(s) On-line",
        "ONLINE_ESPECIAL": "Disciplina(s) On-line - Casos Especiais",
        "OPTATIVA": "Disciplina Optativa",
        "ED": "Estudos Disciplinares (ED)",
        "PIM": "Projeto Integrado Multidisciplinar (PIM)"
    }

    max_text_width = width - 100
    
    for task in data["selected_tasks"]:
        # Título da tarefa em cor verde escuro
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(0.2, 0.5, 0.8)  # Azul intermediário
        c.drawString(50, y_position, data["task_options"].get(task, task))
        c.setFillColorRGB(0, 0, 0)  # Voltar para preto
        y_position -= 20
        c.setFont("Helvetica", 12)

        bullet_items = []
        if task == "AC":
            for part in task_details["AC"].split(". "):
                if part.strip():
                    bullet_items.append(part.strip())
        elif task == "EXT":
            for part in task_details["EXT"].split(". "):
                if part.strip():
                    bullet_items.append(part.strip())
        elif task == "AVA":
            bullet_items = ava_custom
        elif task == "ONLINE":
            bullet_items = online_custom
        elif task == "ONLINE_ESPECIAL":
            bullet_items = online_especial_custom
        elif task == "OPTATIVA":
            bullet_items = optativa_custom
        elif task == "ED":
            bullet_items = ed_custom
        elif task == "PIM":
            bullet_items = pim_custom

        for item in bullet_items:
            bullet_text = "• " + item.strip()
            if not bullet_text.endswith("."):
                bullet_text += "."
            wrapped_lines = wrap_text(bullet_text, c, max_text_width, "Helvetica", 12)
            for line in wrapped_lines:
                c.drawString(50, y_position, line)
                y_position -= 15
                if y_position < 50:
                    draw_page_footer(c, page_num, width, height)
                    c.showPage()
                    page_num += 1
                    y_position = height - 50

        y_position -= 20

    y_position -= 20
    c.setFont("Helvetica-Bold", 12)
    atendimento_text = "Em caso de dúvidas, comparecer no ATENDIMENTO DA COORDENAÇÃO, às quintas-feiras, das 18h30 às 21h00."
    wrapped_lines = wrap_text(atendimento_text, c, max_text_width, "Helvetica-Bold", 12)
    for line in wrapped_lines:
        c.drawString(50, y_position, line)
        y_position -= 15

    draw_page_footer(c, page_num, width, height)
    c.save()
    
    return os.path.abspath(output_filename)

# ============================================================================
# ROTAS FLASK
# ============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ALPHAbet - Gerador de Programa de Estudos</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .content {
            padding: 40px;
        }
        
        .tabs {
            display: flex;
            border-bottom: 2px solid #e0e0e0;
            margin-bottom: 30px;
        }
        
        .tab-btn {
            flex: 1;
            padding: 15px;
            border: none;
            background: none;
            cursor: pointer;
            font-size: 1em;
            font-weight: 500;
            color: #666;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
        }
        
        .tab-btn.active {
            color: #2E86AB;
            border-bottom-color: #2E86AB;
        }
        
        .tab-btn:hover {
            color: #2E86AB;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
            animation: fadeIn 0.3s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        
        input[type="text"],
        input[type="email"],
        textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1em;
            font-family: inherit;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus,
        textarea:focus {
            outline: none;
            border-color: #2E86AB;
            box-shadow: 0 0 0 3px rgba(46, 134, 171, 0.1);
        }
        
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }
        
        .task-item {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            border-left: 4px solid #2E86AB;
        }
        
        .task-item label {
            margin-bottom: 10px;
        }
        
        .task-item input[type="text"] {
            margin-top: 10px;
        }
        
        .btn-group {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 40px;
        }
        
        button {
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
            color: white;
            flex: 1;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(46, 134, 171, 0.3);
        }
        
        .btn-secondary {
            background: #e0e0e0;
            color: #333;
        }
        
        .btn-secondary:hover {
            background: #d0d0d0;
        }
        
        .message {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }
        
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .message.show {
            display: block;
        }
        
        .spinner {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        
        .spinner.show {
            display: block;
        }
        
        .spinner::after {
            content: '';
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #2E86AB;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 ALPHAbet</h1>
            <p>Gerador de Programa de Estudos - Regime de Adaptação/Dependência (AD/DP)</p>
        </div>
        
        <div class="content">
            <div class="message" id="message"></div>
            <div class="spinner" id="spinner"></div>
            
            <form id="form">
                <div class="tabs">
                    <button class="tab-btn" type="button" data-tab="config">⚙️ Configurações</button>
                    <button class="tab-btn active" type="button" data-tab="info">ℹ️ Informações</button>
                    <button class="tab-btn" type="button" data-tab="tasks">📋 Tarefas</button>
                    <button class="tab-btn" type="button" data-tab="generate">📄 Gerar PDF</button>
                </div>
                
                <!-- TAB 1: Informações -->
                <div id="info" class="tab-content">
                    <div class="form-group">
                        <label>Nome do Aluno / RA / Curso / Grade *</label>
                        <input type="text" id="student_name" required placeholder="Ex: João Silva / RA123456">
                    </div>
                    
                    <div class="form-group">
                        <div class="checkbox-group">
                            <input type="checkbox" id="regime_grade">
                            <label for="regime_grade">Aluno participante do regime de grade</label>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <div class="checkbox-group">
                            <input type="checkbox" id="has_subsequent_semester">
                            <label for="has_subsequent_semester">Aluno possui disciplinas em DP para cursar em semestre subsequente</label>
                        </div>
                    </div>
                </div>
                
                <!-- TAB 2: Tarefas -->
                <div id="tasks" class="tab-content">
                    <div class="task-item">
                        <div class="checkbox-group">
                            <input type="checkbox" id="task_AC" class="task-checkbox">
                            <label for="task_AC">Atividades Complementares (AC)</label>
                        </div>
                    </div>
                    
                    <div class="task-item">
                        <div class="checkbox-group">
                            <input type="checkbox" id="task_EXT" class="task-checkbox">
                            <label for="task_EXT">Atividades de Extensão (EXT)</label>
                        </div>
                    </div>
                    
                    <div class="task-item">
                        <div class="checkbox-group">
                            <input type="checkbox" id="task_AVA" class="task-checkbox">
                            <label for="task_AVA">Disciplina(s) AVA</label>
                        </div>
                        <input type="text" id="AVA_disciplines" placeholder="Separe com vírgula" class="discipline-input" disabled>
                    </div>
                    
                    <div class="task-item">
                        <div class="checkbox-group">
                            <input type="checkbox" id="task_ONLINE" class="task-checkbox">
                            <label for="task_ONLINE">Disciplina(s) On-line</label>
                        </div>
                        <input type="text" id="ONLINE_disciplines" placeholder="Separe com vírgula" class="discipline-input" disabled>
                    </div>
                    
                    <div class="task-item">
                        <div class="checkbox-group">
                            <input type="checkbox" id="task_ONLINE_ESPECIAL" class="task-checkbox">
                            <label for="task_ONLINE_ESPECIAL">Disciplina(s) On-line - Casos Especiais</label>
                        </div>
                        <input type="text" id="ONLINE_ESPECIAL_disciplines" placeholder="Separe com vírgula" class="discipline-input" disabled>
                    </div>
                    
                    <div class="task-item">
                        <div class="checkbox-group">
                            <input type="checkbox" id="task_OPTATIVA" class="task-checkbox">
                            <label for="task_OPTATIVA">Disciplina Optativa</label>
                        </div>
                        <input type="text" id="OPTATIVA_disciplines" placeholder="Separe com vírgula" class="discipline-input" disabled>
                    </div>
                    
                    <div class="task-item">
                        <div class="checkbox-group">
                            <input type="checkbox" id="task_ED" class="task-checkbox">
                            <label for="task_ED">Estudos Disciplinares (ED)</label>
                        </div>
                        <input type="text" id="ED_disciplines" placeholder="Separe com vírgula" class="discipline-input" disabled>
                    </div>
                    
                    <div class="task-item">
                        <div class="checkbox-group">
                            <input type="checkbox" id="task_PIM" class="task-checkbox">
                            <label for="task_PIM">Projeto Integrado Multidisciplinar (PIM)</label>
                        </div>
                        <input type="text" id="PIM_disciplines" placeholder="Separe com vírgula" class="discipline-input" disabled>
                    </div>
                </div>
                
                <!-- TAB 1: Configurações -->
                <div id="config" class="tab-content active">
                    <div style="background-color: #fff3cd; padding: 12px 15px; border-radius: 5px; margin-bottom: 25px; border-left: 4px solid #ff9800; display: flex; align-items: center;">
                        <span style="font-size: 1.2em; margin-right: 10px;">📋</span>
                        <span style="color: #333; font-weight: 500;">Edite as datas conforme necessário. Elas serão salvas automaticamente e usadas em todos os PDFs gerados.</span>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                        <!-- COLUNA 1: Provas -->
                        <div style="border-left: 4px solid #2E86AB; padding-left: 15px;">
                            <h4 style="color: #2E86AB; margin-bottom: 20px; display: flex; align-items: center;">
                                <span style="margin-right: 8px;">📝</span> Provas - Regime de Grade
                            </h4>
                            
                            <div style="margin-bottom: 18px;">
                                <label style="font-weight: 600; color: #333; margin-bottom: 8px; display: block;">NP1</label>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                    <input type="text" id="NP1_inicio" placeholder="De" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                    <input type="text" id="NP1_fim" placeholder="Até" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                </div>
                            </div>
                            
                            <div style="margin-bottom: 18px;">
                                <label style="font-weight: 600; color: #333; margin-bottom: 8px; display: block;">NP2</label>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                    <input type="text" id="NP2_inicio" placeholder="De" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                    <input type="text" id="NP2_fim" placeholder="Até" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                </div>
                            </div>
                            
                            <div style="margin-bottom: 18px;">
                                <label style="font-weight: 600; color: #333; margin-bottom: 8px; display: block;">SUB</label>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                    <input type="text" id="SUB_inicio" placeholder="De" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                    <input type="text" id="SUB_fim" placeholder="Até" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                </div>
                            </div>
                            
                            <div style="margin-bottom: 18px;">
                                <label style="font-weight: 600; color: #333; margin-bottom: 8px; display: block;">EXAME</label>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                    <input type="text" id="EXAME_inicio" placeholder="De" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                    <input type="text" id="EXAME_fim" placeholder="Até" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                </div>
                            </div>
                        </div>
                        
                        <!-- COLUNA 2: Prazos Gerais -->
                        <div>
                            <div style="border-left: 4px solid #c41e3a; padding-left: 15px; margin-bottom: 30px;">
                                <h4 style="color: #c41e3a; margin-bottom: 20px; display: flex; align-items: center;">
                                    <span style="margin-right: 8px;">⏰</span> Prazos Gerais
                                </h4>
                                
                                <div style="margin-bottom: 18px;">
                                    <label style="font-weight: 600; color: #333; margin-bottom: 8px; display: block;">Prazo Geral (para regime sem grade)</label>
                                    <input type="text" id="GERAL_prazo" placeholder="DD/MM/YYYY" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                </div>
                                
                                <div style="margin-bottom: 18px;">
                                    <label style="font-weight: 600; color: #333; margin-bottom: 8px; display: block;">Prazo PIM</label>
                                    <input type="text" id="PIM_prazo" placeholder="DD/MM/YYYY" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                </div>
                                
                                <div style="margin-bottom: 18px; padding: 15px; background-color: #f9f9f9; border-radius: 5px; border: 1px solid #eee;">
                                    <label style="font-weight: 600; color: #333; margin-bottom: 8px; display: block;">Atendimento da Coordenação</label>
                                    <input type="text" id="atendimento_info" placeholder="Ex: quintas-feiras, das 18h30 às 21h00" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                </div>
                            </div>
                            
                            <div style="border-left: 4px solid #4CAF50; padding-left: 15px;">
                                <h4 style="color: #4CAF50; margin-bottom: 20px; display: flex; align-items: center;">
                                    <span style="margin-right: 8px;">📂</span> Pasta de Download
                                </h4>
                                
                                <div>
                                    <label style="font-weight: 600; color: #333; margin-bottom: 8px; display: block;">Caminho da pasta destino</label>
                                    <input type="text" id="download_path" placeholder="Ex: pasta/Downloads ou deixe em branco" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em;">
                                    <small style="color: #999; display: block; margin-top: 5px;">Deixe em branco para usar a pasta padrão do navegador</small>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 30px;">
                        <button type="button" class="btn-primary" id="btn-save-dates" style="width: 100%; padding: 12px;">💾 Salvar Configuração</button>
                        <button type="button" id="btn-reset-dates" style="width: 100%; padding: 12px; background: #ccc; color: #333; border: none; border-radius: 5px; cursor: pointer; font-weight: 600;">🔄 Restaurar Padrões</button>
                    </div>
                </div>
                
                <!-- TAB 4: Gerar PDF -->
                <div id="generate" class="tab-content">
                    <p style="text-align: center; color: #666; margin-bottom: 30px;">
                        Clique em "Gerar PDF" para criar o relatório com os dados preenchidos.
                    </p>
                    
                    <div class="btn-group">
                        <button type="button" class="btn-primary" id="btn-generate">🔄 Gerar PDF Agora</button>
                        <button type="reset" class="btn-secondary">🔄 Limpar Tudo</button>
                    </div>
                </div>
            </form>
        </div>
    </div>

    <script>
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = btn.dataset.tab;
                
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                btn.classList.add('active');
                document.getElementById(tabName).classList.add('active');
            });
        });
        
        // Toggle discipline inputs
        document.querySelectorAll('.task-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const taskId = e.target.id.replace('task_', '');
                const input = document.getElementById(taskId + '_disciplines');
                if (input) {
                    input.disabled = !e.target.checked;
                    if (!e.target.checked) {
                        input.value = '';
                    }
                }
            });
        });
        
        // Carregar configurações ao abrir a aba
        document.querySelector('[data-tab="config"]').addEventListener('click', async () => {
            try {
                const response = await fetch('/load_dates');
                const dates = await response.json();
                
                Object.keys(dates).forEach(key => {
                    const input = document.getElementById(key);
                    if (input) input.value = dates[key];
                });
            } catch (error) {
                console.error('Erro ao carregar configurações:', error);
            }
        });
        
        // Salvar configurações
        document.getElementById('btn-save-dates').addEventListener('click', async () => {
            const dates = {};
            document.querySelectorAll('[id^="NP"], [id^="SUB"], [id^="EXAME"], [id^="PIM"], [id^="GERAL"], [id="atendimento_info"], [id="download_path"]').forEach(input => {
                if (input.value) dates[input.id] = input.value;
            });
            
            try {
                const response = await fetch('/save_dates', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(dates)
                });
                
                const result = await response.json();
                if (result.success) {
                    showMessage('✅ Configuração salva com sucesso!', 'success');
                } else {
                    showMessage('❌ Erro ao salvar configuração', 'error');
                }
            } catch (error) {
                showMessage('❌ Erro: ' + error.message, 'error');
            }
        });
        
        // Restaurar padrões
        document.getElementById('btn-reset-dates').addEventListener('click', async () => {
            if (confirm('Tem certeza que deseja restaurar as configurações padrão?')) {
                const defaultDates = {
                    "NP1_inicio": "15/09/2025",
                    "NP1_fim": "27/09/2025",
                    "NP2_inicio": "03/11/2025",
                    "NP2_fim": "14/11/2025",
                    "SUB_inicio": "17/11/2025",
                    "SUB_fim": "25/11/2025",
                    "EXAME_inicio": "04/12/2025",
                    "EXAME_fim": "12/12/2025",
                    "PIM_prazo": "30/10/2025",
                    "GERAL_prazo": "20/10/2025",
                    "atendimento_info": "quintas-feiras, das 18h30 às 21h00",
                    "download_path": ""
                };
                
                Object.keys(defaultDates).forEach(key => {
                    const input = document.getElementById(key);
                    if (input) input.value = defaultDates[key];
                });
                
                try {
                    await fetch('/save_dates', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(defaultDates)
                    });
                    showMessage('✅ Configurações restauradas aos padrões!', 'success');
                } catch (error) {
                    showMessage('❌ Erro: ' + error.message, 'error');
                }
            }
        });
        
        // Form submission
        document.getElementById('btn-generate').addEventListener('click', async () => {
            const studentName = document.getElementById('student_name').value.trim();
            
            if (!studentName) {
                showMessage('Por favor, insira o nome do aluno!', 'error');
                return;
            }
            
            const selectedTasks = [];
            document.querySelectorAll('.task-checkbox:checked').forEach(cb => {
                selectedTasks.push(cb.id.replace('task_', ''));
            });
            
            if (selectedTasks.length === 0) {
                showMessage('Por favor, selecione pelo menos uma tarefa!', 'error');
                return;
            }
            
            const data = {
                student_name: studentName,
                regime_grade: document.getElementById('regime_grade').checked,
                has_subsequent_semester: document.getElementById('has_subsequent_semester').checked,
                selected_tasks: selectedTasks,
                task_options: {
                    "AC": "Atividades Complementares (AC)",
                    "EXT": "Atividades de Extensão (EXT)",
                    "AVA": "Disciplina(s) AVA",
                    "ONLINE": "Disciplina(s) On-line",
                    "ONLINE_ESPECIAL": "Disciplina(s) On-line - Casos Especiais",
                    "OPTATIVA": "Disciplina Optativa",
                    "ED": "Estudos Disciplinares (ED)",
                    "PIM": "Projeto Integrado Multidisciplinar (PIM)"
                },
                AVA_disciplines: document.getElementById('AVA_disciplines').value.split(',').filter(d => d.trim()),
                ONLINE_disciplines: document.getElementById('ONLINE_disciplines').value.split(',').filter(d => d.trim()),
                ONLINE_ESPECIAL_disciplines: document.getElementById('ONLINE_ESPECIAL_disciplines').value.split(',').filter(d => d.trim()),
                OPTATIVA_disciplines: document.getElementById('OPTATIVA_disciplines').value.split(',').filter(d => d.trim()),
                ED_disciplines: document.getElementById('ED_disciplines').value.split(',').filter(d => d.trim()),
                PIM_disciplines: document.getElementById('PIM_disciplines').value.split(',').filter(d => d.trim())
            };
            
            showSpinner(true);
            
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    showMessage(result.message, 'success');
                } else {
                    const error = await response.json();
                    showMessage('❌ Erro: ' + error.error, 'error');
                }
            } catch (error) {
                showMessage('❌ Erro: ' + error.message, 'error');
            } finally {
                showSpinner(false);
            }
        });
        
        function showMessage(text, type) {
            const msg = document.getElementById('message');
            msg.textContent = text;
            msg.className = `message ${type} show`;
            setTimeout(() => msg.classList.remove('show'), 5000);
        }
        
        function showSpinner(show) {
            document.getElementById('spinner').classList.toggle('show', show);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/load_dates', methods=['GET'])
def load_dates_route():
    """Retorna as datas atuais"""
    return jsonify(CURRENT_DATES)

@app.route('/save_dates', methods=['POST'])
def save_dates_route():
    """Salva as datas no arquivo JSON"""
    try:
        global CURRENT_DATES
        new_dates = request.json
        CURRENT_DATES.update(new_dates)
        save_dates(CURRENT_DATES)
        return jsonify({"success": True, "message": "Datas salvas com sucesso!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        # Adicionar datas ao contexto
        data.update(CURRENT_DATES)
        pdf_path = generate_study_report(data)
        
        # Apenas retornar sucesso - o arquivo já foi salvo na pasta
        return jsonify({
            "success": True, 
            "message": f"✅ PDF gerado com sucesso em: {pdf_path}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    import webbrowser
    import threading
    import time
    
    print("\n" + "="*60)
    print("  ALPHAbet Web - Iniciando...".center(60))
    print("="*60)
    print("\n🚀 Iniciando servidor...")
    print("🌐 Abrindo navegador: http://localhost:5000")
    print("⚙️  Pressione Ctrl+C para parar\n")
    
    # Abrir navegador em uma thread separada (esperar o servidor iniciar)
    def open_browser():
        time.sleep(2)  # Esperar 2 segundos para o servidor iniciar
        webbrowser.open('http://localhost:5000')
    
    thread = threading.Thread(target=open_browser, daemon=True)
    thread.start()
    
    app.run(debug=False, host='localhost', port=5000, use_reloader=False)
