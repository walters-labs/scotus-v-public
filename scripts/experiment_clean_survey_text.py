"""Build a separate survey-only index with conservative text cleanup."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sqlite3
import unicodedata

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scvpublic.build import digest, write_index


def clean_text(document):
    text = unicodedata.normalize('NFKC', document['question'])
    # Remove survey administration annotations, not substantive parentheses.
    text = re.sub(r'\([^()]*\b(?:19|20)\d{2}[^()]*\)', ' ', text)
    text = re.sub(r'\((?:RESPONDENT BOOKLET|IF YES|7-POINT SCALE SHOWN TO R)[^()]*\)', ' ', text, flags=re.I)
    text = re.sub(r'\(CARD WITH RESPONSE CHOICES SHOWN TO R:[^)]*\)', ' ', text, flags=re.I)
    text = re.sub(r'\bV\d{5,}\w*\b|\bfedspend_\w+\b', ' ', text)
    text = re.sub(r'(?m)^\s*(?:(?:19|20)\d{2}[, –-]*)+(?:LATER)?\s*:\s*', '', text)
    # Sentence selection is deliberately generic, not topic-specific. Drop
    # interviewer introductions; keep actual policy questions/statements.
    sentences = re.split(r'(?<=[.?!])\s+', ' '.join(text.split()))
    excluded = ('around election time', 'now i would like', 'of course,',
                'i would like you to look', 'if you don’t have an opinion',
                'have you been interested', 'do you have an opinion',
                'where would you place yourself', 'some people have opinions')
    seen=set(); kept=[]
    for sentence in sentences:
        if sentence.lower().startswith(excluded): continue
        key=re.sub(r'\W+', '', sentence.lower())
        if key and key not in seen:
            seen.add(key); kept.append(sentence)
    return document.get('title','')+'. '+' '.join(kept)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    shutil.copyfile(args.artifact,args.output)
    with sqlite3.connect(args.output) as db:
        corpora=[c for c, in db.execute("SELECT DISTINCT corpus FROM documents WHERE corpus != 'court'")]
        for corpus in corpora:
            rows=list(db.execute('SELECT id,payload FROM documents WHERE corpus=? ORDER BY id',(corpus,)))
            assert [i for i,_ in rows]==list(range(len(rows)))
            docs=[json.loads(p) for _,p in rows]
            for d in docs: d['search_text']=clean_text(d)
            v=TfidfVectorizer(ngram_range=(1,2),stop_words='english',dtype=np.float32,
                min_df=.0001 if corpus=='public' else 1,max_df=.30 if corpus=='public' else 1.)
            matrix=v.fit_transform(d['search_text'] for d in docs)
            db.execute('DELETE FROM postings WHERE corpus=?',(corpus,))
            db.execute('DELETE FROM documents WHERE corpus=?',(corpus,))
            write_index(db,corpus,matrix,v.get_feature_names_out(),docs)
        db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('survey_text_experiment',json.dumps(dict(
            source_sha256=digest(args.artifact),script_sha256=digest(Path(__file__))))))
    print(args.output)


if __name__=='__main__':main()
