# app.py (обновлённая версия)
import os
import requests
from bs4 import BeautifulSoup
import gradio as gr
from openai import OpenAI
from fpdf import FPDF

# Инициализация OpenAI клиента
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Стоп-слова для фильтрации
STOPWORDS = {"в", "и", "на", "с", "по", "для", "что", "как", "это", "то"}

def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        main_content = soup.find('main')
        return main_content.get_text(strip=True) if main_content else "Не удалось извлечь текст с вакансии."
    except Exception as e:
        return f"Ошибка при извлечении вакансии: {e}"

def compare_keywords(job_desc, resume_text):
    job_words = set(job_desc.lower().split()) - STOPWORDS
    resume_words = set(resume_text.lower().split()) - STOPWORDS
    common = job_words & resume_words
    percent = round(len(common) / len(job_words) * 100, 2) if job_words else 0
    return f"Общие слова: {', '.join(sorted(common))}\nСовпадение: {percent}%"

def full_analysis(job_desc, resume_text):
    prompt = f"""
Ты — эксперт по подбору персонала. Проанализируй соответствие кандидата требованиям вакансии.
Выведи:
1. Насколько кандидат подходит;
2. Его сильные и слабые стороны;
3. Оценочный процент соответствия;

Вакансия:
{job_desc}

Резюме:
{resume_text}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        ai_analysis = response.choices[0].message.content.strip()
    except Exception as e:
        ai_analysis = f"Ошибка от OpenAI: {e}"

    keyword_analysis = compare_keywords(job_desc, resume_text)
    return f"{ai_analysis}\n\n=== Сравнение по ключевым словам ===\n{keyword_analysis}"

def generate_pdf(content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in content.split('\n'):
        pdf.multi_cell(0, 10, line)
    file_path = "resume_analysis.pdf"
    pdf.output(file_path)
    return file_path

def process_inputs(job_desc, job_url, resume_text):
    if not resume_text.strip():
        return "Пожалуйста, вставьте текст резюме.", None
    if not job_desc.strip() and job_url.strip():
        job_desc = extract_text_from_url(job_url.strip())
    elif not job_desc.strip():
        return "Пожалуйста, введите описание вакансии или ссылку.", None

    result = full_analysis(job_desc, resume_text)
    return result, generate_pdf(result)

def load_example():
    job = "Требуется Product Manager с опытом в B2B, управлением командами и знанием ИИ. Необходим английский язык уровня B2+."
    resume = "Работал менеджером продуктов, запускал SaaS, координировал разработчиков. Нет опыта в ИИ, но быстро обучаюсь."
    return [job, "", resume]

iface = gr.Interface(
    fn=process_inputs,
    inputs=[
        gr.Textbox(lines=6, label="Описание вакансии (или оставьте пустым и вставьте ссылку)"),
        gr.Textbox(lines=1, label="Ссылка на вакансию"),
        gr.Textbox(lines=15, label="Резюме кандидата")
    ],
    outputs=[
        gr.Textbox(label="Результат анализа"),
        gr.File(label="Скачать PDF")
    ],
    title="AI Resume Matcher v3",
    description="Сравнение резюме с вакансией (ИИ + ключевые слова) + выгрузка в PDF. Поддержка ссылок (например hh.ru)",
    examples=[load_example()]
)

if __name__ == "__main__":
    iface.launch()
