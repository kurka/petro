# coding: utf-8

import subprocess
from wordcloud import WordCloud
import unicodedata
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import nltk

def rem_accents(text):
    if type(text) == str:
        text = unicode(text, 'utf8')
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore') #remove accents

def get_pdf_text(doc_name):
    #read capa
    #TODO - checar se todo documento tem so uma pagina de capa mesmo (talvez seja mais seguro tirar do texto completo)
    capa = rem_accents(subprocess.check_output("pdftotext -l 1 '{}' -".format(doc_name), shell=True))
    #read rest
    text = rem_accents(subprocess.check_output("pdftotext -f 2 '{}' -".format(doc_name), shell=True))
    return capa, text

def get_metadata(doc_info, capa):
    #date
    get_data = r'DATA:\s+(\d\d\/\d\d\/\d\d\d\d)'
    res = re.search(get_data, capa, re.M|re.I)
    if res:
        doc_info["date"] = res.group(1)
        print("date: {}".format(doc_info["date"]))
    else:
        print("date not found in file!")

    #n_pages
    get_n_pages = r'PAGINAS:\s+(\d+)'
    res = re.search(get_n_pages, capa, re.M|re.I)
    if res:
        doc_info["n_pages"] = int(res.group(1))
        print("n_pages: {}".format(doc_info["n_pages"]))
    else:
        print("n_pages not found in file!")


    #depoentes_names
    #depoentes_roles
    re_depoentes_block = r'^DEPOENTE/CONVIDADO - QUALIFICACAO\n((?:.*\n)+)^SUMARIO\s*$'
    res = re.search(re_depoentes_block, capa, re.M|re.I)
    assert res, ">>>>Big problem: Didn't find names of depoentes!!!"
    if res:
        depoentes_block = res.group(1)
        depoentes_names = []
        depoentes_cargos = []
        for l in re.split(r'\.\n', depoentes_block):
            l = l.replace('\n', ' ')
            parts = l.split(" - ")
            if len(parts) >= 2:
                nome = parts[0].strip()
                cargo = "".join(parts[1:]).strip()
                depoentes_names.append(nome)
                depoentes_cargos.append(cargo)
        doc_info["depoentes_names"] = depoentes_names
        doc_info["depoentes_cargos"] = depoentes_cargos
        for el in zip(doc_info["depoentes_names"], doc_info["depoentes_cargos"]):
            print(el)

    return doc_info


def clean_text(doc_info, text):
    #limpa texto
    clean_header = r'CAMARA DOS DEPUTADOS - DETAQ(?:.*\n)*?\d\d\/\d\d\/\d\d\d\d'
    clean_num = r'\n\s*\d+\s*\n'
    clean_mult_n = r'\n\n+'

    #remove headers
    text, subs = re.subn(clean_header, "", text, flags=re.M)
    print(subs)
    assert subs == doc_info["n_pages"], "doing more substitutions than pages!"

    #remove page numbers
    text, subs = re.subn(clean_num, "\n", text, flags=re.M)
    print(subs)
    assert subs == doc_info["n_pages"], "doing more substitutions than pages!"

    #remove double newlines
    text, subs = re.subn(clean_mult_n, "", text, flags=re.M)
    print(subs)

    return text

def get_falas(doc_info, text):
    doc_info["text"] = dict()
    for depoente in doc_info["depoentes_names"]:
        doc_info["text"][depoente] = dict()
        doc_info["text"][depoente]["falas"] = []
        regex_str = r'^.+{}\s+-\s+(.*\n(?:.*\n)*?)(?:^(?:O\s+SR|A\s+SRA|SR|SRA))'.format(depoente)
        #regex_str = r'^.+{}\s+-\s+(.*\n(?:.*\n)*?)(?:^O\s+SR|A\s+SRA)'.format(depoente)
        frases_regex = re.compile(regex_str, re.M)
        frases = frases_regex.findall(text)
        print("\n>>>>>{}".format(depoente))
        print(len(frases))
        for i,f in enumerate(frases):
            ff = re.sub(r'([^.])\n', r'\1 ', f, flags=re.M)
            ff = ff.strip()
            doc_info["text"][depoente]["falas"].append(ff)
            print("{}: {}".format(i+1, ff))

    return doc_info


def text_statistics(doc_info):
    #each document statistics
    for n in doc_info["depoentes_names"]:
        doc_info["text"][n]["n_answers"] = len(doc_info["text"][n]["falas"])
        doc_info["text"][n]["len_char_answers"] = sum(len(f) for f in doc_info["text"][n]["falas"])
        doc_info["text"][n]["avg_len_char_answers"] = doc_info["text"][n]["len_char_answers"] / doc_info["text"][n]["n_answers"]
        doc_info["text"][n]["len_words_answers"] = sum(len(re.split(r'\W+', f)) for f in doc_info["text"][n]["falas"])
        doc_info["text"][n]["avg_len_words_answers"] = doc_info["text"][n]["len_words_answers"] / doc_info["text"][n]["n_answers"]
        doc_info["text"][n]["silence_answers"] = sum(1 if re.search(r'silenci', f, re.I) else 0 for f in doc_info["text"][n]["falas"])
        ## non-silence stats
        doc_info["text"][n]["n_answers_ns"] = doc_info["text"][n]["n_answers"] - doc_info["text"][n]["silence_answers"]
        doc_info["text"][n]["len_char_answers_ns"] = sum(len(f) for f in doc_info["text"][n]["falas"] if not re.search(r'silenci', f, re.I))
        doc_info["text"][n]["avg_len_char_answers_ns"] = doc_info["text"][n]["len_char_answers_ns"] / doc_info["text"][n]["n_answers_ns"]
        doc_info["text"][n]["len_words_answers_ns"] = sum(len(re.split(r'\W+', f)) for f in doc_info["text"][n]["falas"] if not re.search(r'silenci', f, re.I))
        doc_info["text"][n]["avg_len_words_answers_ns"] = doc_info["text"][n]["len_words_answers_ns"] / doc_info["text"][n]["n_answers_ns"]


    #general statistics
    doc_info["text"]["general"] = dict()
    doc_info["text"]["general"]["n_answers"] = sum(doc_info["text"][n]["n_answers"] for n in doc_info["depoentes_names"])
    doc_info["text"]["general"]["len_char_answers"] = sum(doc_info["text"][n]["len_char_answers"] for n in doc_info["depoentes_names"])
    doc_info["text"]["general"]["avg_len_char_answers"] = doc_info["text"]["general"]["len_char_answers"] / doc_info["text"]["general"]["n_answers"]
    doc_info["text"]["general"]["len_words_answers"] = sum(doc_info["text"][n]["len_words_answers"] for n in doc_info["depoentes_names"])
    doc_info["text"]["general"]["avg_len_words_answers"] = doc_info["text"]["general"]["len_words_answers"] / doc_info["text"]["general"]["n_answers"]
    doc_info["text"]["general"]["silence_answers"] = sum(doc_info["text"][n]["silence_answers"] for n in doc_info["depoentes_names"])
    ## non-silence stats
    doc_info["text"]["general"]["n_answers_ns"] = doc_info["text"]["general"]["n_answers"] - doc_info["text"]["general"]["silence_answers"]
    doc_info["text"]["general"]["len_char_answers_ns"] = sum(doc_info["text"][n]["len_char_answers_ns"] for n in doc_info["depoentes_names"])
    doc_info["text"]["general"]["avg_len_char_answers_ns"] = doc_info["text"]["general"]["len_char_answers_ns"] / doc_info["text"]["general"]["n_answers_ns"]
    doc_info["text"]["general"]["len_words_answers_ns"] = sum(doc_info["text"][n]["len_words_answers_ns"] for n in doc_info["depoentes_names"])
    doc_info["text"]["general"]["avg_len_words_answers_ns"] = doc_info["text"]["general"]["len_words_answers_ns"] / doc_info["text"]["general"]["n_answers_ns"]

    print(doc_info["text"]["general"])

    return doc_info


def do_wordcloud(doc_info):

    stemmer = nltk.stem.RSLPStemmer()
    stemmer.stem("trabalhar")

    STOPWORDS = {rem_accents(x) for x in nltk.corpus.stopwords.words('portuguese')} | \
        {"sr", "senhor", "deputado", "presidente", "vou", "deputado", "pergunta",
        "silencio", "permanecer", "permanecerei", "acho", "falei","entao",
        "processo", "manter", "inclusive", "questao", "momento", "falar", "seguinte"}
    STOPWORDS_STEM = {stemmer.stem(x) for x in STOPWORDS}


    all_falas = " ".join(f for n in doc_info["depoentes_names"] for f in doc_info["text"][n]["falas"] if not re.search(r'silenci', f, re.I))

    all_falas_stem = " ".join(stemmer.stem(w) for w in re.split(r'\W+', all_falas) if w)
    wordcloud = WordCloud(stopwords=STOPWORDS, max_font_size=40).generate(all_falas)
    plt.imshow(wordcloud)
    plt.axis("off")


def process_doc(doc_name):
    doc_info = dict()
    capa, text = get_pdf_text(doc_name)
    # Treat cover page
    doc_info = get_metadata(doc_info, capa)
    # Treat the rest of the text
    text = clean_text(doc_info, text)
    # Get people phrases
    doc_info = get_falas(doc_info, text)
    doc_info = text_statistics(doc_info)
    #do_wordcloud(doc_info)

    return doc_info

if __name__ == '__main__':
    process_doc('01.09-2015-  Odebrecht.pdf')
