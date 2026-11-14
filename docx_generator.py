import os
import re
from datetime import datetime
from typing import List, Dict, Any
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex: str):
    """Устанавливает цвет фона ячейки таблицы."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Внутренние отступы в ячейке таблицы."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def create_exam_document(
    topic: str,
    multiple_choice_questions: List[Dict[str, Any]],
    written_questions: List[Dict[str, Any]],
    output_dir: str = "generated_docs"
) -> str:
    """
    Создает красивый и профессионально оформленный Word (.docx) документ.
    - 50 тестовых вопросов с 4 вариантами (A, B, C, D)
    - 10 открытых письменных заданий
    - Итоговая таблица ключей и методические ответы/критерии
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Очистка имени файла
    safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic).strip()[:40] or "Test_Ekzamen"
    filename = f"Test_{safe_topic}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    file_path = os.path.join(output_dir, filename)

    doc = Document()

    # Настройка полей документа (1.8 см)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Цветовая палитра
    PRIMARY_COLOR = RGBColor(26, 54, 93)     # Deep Navy
    SECONDARY_COLOR = RGBColor(49, 130, 206) # Accent Blue
    TEXT_COLOR = RGBColor(45, 55, 72)        # Charcoal Body Text
    GRAY_COLOR = RGBColor(113, 128, 150)

    # 1. Заголовочная карточка документа
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run("НАЦИОНАЛЬНЫЙ СЕРТИФИКАТ И ВСТУПИТЕЛЬНЫЕ ЭКЗАМЕНЫ")
    title_run.font.name = "Calibri"
    title_run.font.size = Pt(11)
    title_run.font.bold = True
    title_run.font.color.rgb = SECONDARY_COLOR

    subtitle_p = doc.add_paragraph()
    subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = subtitle_p.add_run("Комплексный экзаменационный тест и письменные задания")
    sub_run.font.name = "Calibri"
    sub_run.font.size = Pt(18)
    sub_run.font.bold = True
    sub_run.font.color.rgb = PRIMARY_COLOR

    meta_p = doc.add_paragraph()
    meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_p.paragraph_format.space_after = Pt(16)
    m1 = meta_p.add_run(f"Тема: «{topic}»\n")
    m1.bold = True
    m1.font.size = Pt(12)
    m1.font.color.rgb = PRIMARY_COLOR
    
    m2 = meta_p.add_run(f"Количество заданий: 50 тестовых + 10 письменных  |  Дата: {datetime.now().strftime('%d.%m.%Y')}")
    m2.font.size = Pt(9.5)
    m2.font.color.rgb = GRAY_COLOR

    # Горизонтальный разделитель
    div_p = doc.add_paragraph()
    div_p.paragraph_format.space_after = Pt(14)
    div_run = div_p.add_run("―" * 58)
    div_run.font.color.rgb = SECONDARY_COLOR
    div_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ----------------------------------------------------
    # ЧАСТЬ I. ТЕСТОВЫЕ ВОПРОСЫ (1-50)
    # ----------------------------------------------------
    h1 = doc.add_paragraph()
    h1.paragraph_format.space_before = Pt(10)
    h1.paragraph_format.space_after = Pt(8)
    h1_run = h1.add_run("ЧАСТЬ I. ТЕСТОВЫЕ ЗАДАНИЯ С ВЫБОРОМ ОТВЕТА (1–50)")
    h1_run.font.name = "Calibri"
    h1_run.font.size = Pt(14)
    h1_run.font.bold = True
    h1_run.font.color.rgb = PRIMARY_COLOR

    instr_p = doc.add_paragraph()
    instr_p.paragraph_format.space_after = Pt(12)
    instr_run = instr_p.add_run("Инструкция: Внимательно прочитайте каждое задание. Из четырех предложенных вариантов ответа (A, B, C, D) выберите только один правильный.")
    instr_run.font.italic = True
    instr_run.font.size = Pt(10)
    instr_run.font.color.rgb = GRAY_COLOR

    for i, q in enumerate(multiple_choice_questions, start=1):
        qp = doc.add_paragraph()
        qp.paragraph_format.space_before = Pt(6)
        qp.paragraph_format.space_after = Pt(2)
        qp.paragraph_format.keep_with_next = True
        
        num_run = qp.add_run(f"{i}. ")
        num_run.bold = True
        num_run.font.color.rgb = PRIMARY_COLOR
        num_run.font.size = Pt(11)
        
        q_text_run = qp.add_run(q.get("question", ""))
        q_text_run.font.name = "Calibri"
        q_text_run.font.size = Pt(11)
        q_text_run.bold = True
        q_text_run.font.color.rgb = TEXT_COLOR

        # Варианты ответов A, B, C, D
        options = q.get("options", [])
        for opt in options:
            op_p = doc.add_paragraph()
            op_p.paragraph_format.left_indent = Inches(0.25)
            op_p.paragraph_format.space_before = Pt(1)
            op_p.paragraph_format.space_after = Pt(1)
            
            key_run = op_p.add_run(f"{opt.get('key', '')}) ")
            key_run.bold = True
            key_run.font.color.rgb = PRIMARY_COLOR
            key_run.font.size = Pt(10.5)
            
            opt_text_run = op_p.add_run(opt.get("text", ""))
            opt_text_run.font.name = "Calibri"
            opt_text_run.font.size = Pt(10.5)
            opt_text_run.font.color.rgb = TEXT_COLOR

    # ----------------------------------------------------
    # ЧАСТЬ II. ПИСЬМЕННЫЕ ЗАДАНИЯ (51-60)
    # ----------------------------------------------------
    doc.add_page_break()

    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(8)
    h2_run = h2.add_run("ЧАСТЬ II. ОТКРЫТЫЕ ПИСЬМЕННЫЕ ЗАДАНИЯ (51–60)")
    h2_run.font.name = "Calibri"
    h2_run.font.size = Pt(14)
    h2_run.font.bold = True
    h2_run.font.color.rgb = PRIMARY_COLOR

    instr2 = doc.add_paragraph()
    instr2.paragraph_format.space_after = Pt(12)
    instr2_run = instr2.add_run("Инструкция: На следующие вопросы требуется дать развернутый аргументированный письменный ответ, провести анализ текста или сформулировать правило с примерами.")
    instr2_run.font.italic = True
    instr2_run.font.size = Pt(10)
    instr2_run.font.color.rgb = GRAY_COLOR

    start_num = len(multiple_choice_questions) + 1
    for i, wq in enumerate(written_questions, start=start_num):
        w_p = doc.add_paragraph()
        w_p.paragraph_format.space_before = Pt(8)
        w_p.paragraph_format.space_after = Pt(4)
        w_p.paragraph_format.keep_with_next = True
        
        num_run = w_p.add_run(f"Задание {i}. ")
        num_run.bold = True
        num_run.font.color.rgb = PRIMARY_COLOR
        num_run.font.size = Pt(11)

        task_run = w_p.add_run(wq.get("task", wq.get("question", "")))
        task_run.font.name = "Calibri"
        task_run.font.size = Pt(11)
        task_run.bold = True
        task_run.font.color.rgb = TEXT_COLOR

        # Место для ответа (линии)
        lines_p = doc.add_paragraph()
        lines_p.paragraph_format.space_before = Pt(2)
        lines_p.paragraph_format.space_after = Pt(8)
        lines_run = lines_p.add_run("Место для ответа:\n" + ("." * 90 + "\n") * 3)
        lines_run.font.size = Pt(8.5)
        lines_run.font.color.rgb = GRAY_COLOR

    # ----------------------------------------------------
    # ЧАСТЬ III. КЛЮЧИ И ОБЪЯСНЕНИЯ (Javoblar kaliti)
    # ----------------------------------------------------
    doc.add_page_break()

    h3 = doc.add_paragraph()
    h3.paragraph_format.space_before = Pt(10)
    h3.paragraph_format.space_after = Pt(8)
    h3_run = h3.add_run("ЧАСТЬ III. КЛЮЧИ И МЕТОДИЧЕСКИЕ РАЗБОРЫ")
    h3_run.font.name = "Calibri"
    h3_run.font.size = Pt(14)
    h3_run.font.bold = True
    h3_run.font.color.rgb = PRIMARY_COLOR

    doc.add_paragraph("Таблица правильных ответов к части I (1–50):").runs[0].bold = True

    # Создаем аккуратную таблицу ключей (например, 5 колонок по 10 вопросов)
    table = doc.add_table(rows=11, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Заголовок таблицы
    headers = ["№ 1-10", "№ 11-20", "№ 21-30", "№ 31-40", "№ 41-50"]
    for col_idx, header_text in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.text = header_text
        set_cell_background(cell, "1A365D")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(9.5)
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)

    # Заполнение таблицы ключами
    total_q = len(multiple_choice_questions)
    for row_idx in range(1, 11):
        for col_idx in range(5):
            q_num = col_idx * 10 + row_idx
            cell = table.cell(row_idx, col_idx)
            if q_num <= total_q:
                correct_ans = multiple_choice_questions[q_num - 1].get("correct_key", "-")
                cell.text = f"{q_num} — {correct_ans}"
            else:
                cell.text = "-"
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if row_idx % 2 == 0:
                set_cell_background(cell, "F7FAFC")
            for run in p.runs:
                run.font.name = "Calibri"
                run.font.size = Pt(9.5)
                run.font.color.rgb = TEXT_COLOR

    # Разбор и модельные ответы к письменным заданиям
    doc.add_paragraph().paragraph_format.space_after = Pt(10)
    w_ans_h = doc.add_paragraph()
    w_ans_h.paragraph_format.space_before = Pt(14)
    w_ans_h.paragraph_format.space_after = Pt(6)
    w_ans_h_run = w_ans_h.add_run("Модельные ответы и критерии оценивания письменных заданий (51–60):")
    w_ans_h_run.bold = True
    w_ans_h_run.font.size = Pt(12)
    w_ans_h_run.font.color.rgb = PRIMARY_COLOR

    for i, wq in enumerate(written_questions, start=start_num):
        wp = doc.add_paragraph()
        wp.paragraph_format.space_before = Pt(6)
        wp.paragraph_format.space_after = Pt(2)
        wp.paragraph_format.keep_with_next = True
        
        t_run = wp.add_run(f"Задание {i}: {wq.get('task', wq.get('question', ''))}\n")
        t_run.bold = True
        t_run.font.size = Pt(10.5)
        t_run.font.color.rgb = PRIMARY_COLOR

        ans_run = wp.add_run("Примерный ответ / критерии: ")
        ans_run.bold = True
        ans_run.font.size = Pt(10)
        
        detail_run = wp.add_run(f"{wq.get('model_answer', wq.get('criteria', 'Развернутый аргументированный ответ.'))}\n")
        detail_run.font.size = Pt(10)
        detail_run.font.color.rgb = TEXT_COLOR

    doc.save(file_path)
    return file_path
