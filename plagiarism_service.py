import os
import re
import stanza
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from collections import Counter
from stop_words import get_stop_words

try:
    nlp = stanza.Pipeline('uk', processors='tokenize,lemma', use_gpu=False)
except:
    stanza.download('uk')
    nlp = stanza.Pipeline('uk', processors='tokenize,lemma', use_gpu=False)

STOP_WORDS = set(get_stop_words('uk'))

model = SentenceTransformer('all-MiniLM-L6-v2')

def read_texts_from_folder(folder_path):
    texts = []
    filenames = []

    if not os.path.exists(folder_path):
        print(f"Помилка: папка '{folder_path}' не знайдена.")
        return texts, filenames

    for filename in sorted(os.listdir(folder_path)):
        if filename.endswith(".txt"):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    text = file.read().strip()
                    if text:
                        texts.append(text)
                        filenames.append(filename)
            except Exception as e:
                print(f"Помилка при зчитуванні файлу {filename}: {e}")

    return texts, filenames


def preprocess_text(text):
    text = text.lower()
    text = re.sub(r"[^\w\sа-яіїєґ']", " ", text, flags=re.UNICODE)
    text = re.sub(r"\d+", " ", text)

    # лематизація прямо тут
    doc = nlp(text)

    words = []
    for sentence in doc.sentences:
        for word in sentence.words:
            lemma = word.lemma
            if lemma not in STOP_WORDS:
                words.append(lemma)

    return " ".join(words)

def get_common_words(text1, text2):
    words1 = preprocess_text(text1).split()
    words2 = preprocess_text(text2).split()

    counter1 = Counter(words1)
    counter2 = Counter(words2)

    common = {}
    for word in set(counter1) & set(counter2):
        common[word] = min(counter1[word], counter2[word])

    # сортуємо за частотою
    common_sorted = sorted(common.items(), key=lambda x: x[1], reverse=True)

    return common_sorted

def compute_tfidf(texts):
    vectorizer = TfidfVectorizer()
    return vectorizer.fit_transform(texts)

def cosine_sim(input_vector, database_vectors):
    return cosine_similarity(input_vector, database_vectors)[0]

def get_ngrams(text, n=2):
    words = text.split()
    return set(zip(*[words[i:] for i in range(n)]))

def jaccard_similarity(text1, text2, n=2):
    ngrams1 = get_ngrams(text1, n)
    ngrams2 = get_ngrams(text2, n)

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)

    return intersection / union

def semantic_similarity(database_texts, input_text):
    embeddings = model.encode(database_texts + [input_text])

    input_vec = embeddings[-1]
    db_vecs = embeddings[:-1]

    similarities = cosine_similarity([input_vec], db_vecs)[0]
    return similarities

def calculate_plagiarism_similarity(database_texts, input_text, ngram_n):
    processed_database = [preprocess_text(t) for t in database_texts]
    processed_input = preprocess_text(input_text)

    all_texts = processed_database + [processed_input]

    tfidf_matrix = compute_tfidf(all_texts)

    input_vec = tfidf_matrix[-1]
    db_vecs = tfidf_matrix[:-1]

    cosine_scores = cosine_sim(input_vec, db_vecs)

    jaccard_scores = [
        jaccard_similarity(processed_input, text, n=ngram_n)
        for text in processed_database
    ]

    plagiarism_scores = [
        (c + j) / 2
        for c, j in zip(cosine_scores, jaccard_scores)
    ]

    return plagiarism_scores

def get_results(database_texts, filenames, input_text, ngram_n):
    similarities = calculate_plagiarism_similarity(database_texts, input_text, ngram_n)

    results = list(zip(filenames, similarities, database_texts))
    results.sort(key=lambda x: x[1], reverse=True)

    max_similarity = results[0][1]
    most_similar_file = results[0][0]
    most_similar_text = results[0][2]
    uniqueness = max(0.0, 1 - max_similarity) * 100

    input_words = preprocess_text(input_text).split()
    similar_words = preprocess_text(most_similar_text).split()

    common_words = Counter(input_words) & Counter(similar_words)

    return {
        "most_similar_file": most_similar_file,
        "similarity": round(max_similarity * 100, 2),
        "uniqueness": round(uniqueness, 2),
        "common_words": [
            {"word": word, "count": count}
            for word, count in common_words.most_common()
        ],
        "all_results": [
            {
                "filename": filename,
                "similarity": round(similarity * 100, 2)
            }
            for filename, similarity, _ in results
        ]
    }

def check_plagiarism_with_progress(database_texts, filenames, input_text, ngram_n):
    total = len(database_texts)

    if total == 0:
        yield {
            "type": "error",
            "message": "База текстів порожня"
        }
        return

    processed_input = preprocess_text(input_text)

    results = []

    for index, (filename, db_text) in enumerate(zip(filenames, database_texts), start=1):
        processed_db_text = preprocess_text(db_text)

        tfidf_matrix = compute_tfidf([processed_db_text, processed_input])
        cosine_score = cosine_similarity(tfidf_matrix[1], tfidf_matrix[0])[0][0]

        jaccard_score = jaccard_similarity(
            processed_input,
            processed_db_text,
            n=ngram_n
        )

        combined_score = (cosine_score + jaccard_score) / 2

        results.append({
            "filename": filename,
            "similarity": combined_score,
            "database_text": db_text
        })

        progress = round((index / total) * 100)

        yield {
            "type": "progress",
            "processed": index,
            "total": total,
            "progress": progress,
            "current_file": filename
        }

    results.sort(key=lambda x: x["similarity"], reverse=True)

    best_result = results[0]
    max_similarity = best_result["similarity"]
    uniqueness = max(0.0, 1 - max_similarity) * 100

    input_words = preprocess_text(input_text).split()
    similar_words = preprocess_text(best_result["database_text"]).split()
    common_words = Counter(input_words) & Counter(similar_words)

    top_results = results[:10]

    yield {
        "type": "result",
        "mode": "plagiarism",
        "most_similar_file": best_result["filename"],
        "similarity": round(max_similarity * 100, 2),
        "uniqueness": round(uniqueness, 2),
        "input_text": input_text,
        "most_similar_text": best_result["database_text"],

        "common_words": [
            {"word": word, "count": count}
            for word, count in common_words.most_common()
        ],

        "top_results": [
            {
                "filename": item["filename"],
                "similarity": round(item["similarity"] * 100, 2),
                "text": item["database_text"]
            }
            for item in top_results
        ],

        "all_results": [
            {
                "filename": item["filename"],
                "similarity": round(item["similarity"] * 100, 2),
                "text": item["database_text"]
            }
            for item in results
        ]
    }

def check_semantic_with_progress(database_texts, filenames, input_text):
    total = len(database_texts)

    if total == 0:
        yield {
            "type": "error",
            "message": "База текстів порожня"
        }
        return

    results = []

    for index, (filename, db_text) in enumerate(zip(filenames, database_texts), start=1):
        semantic_score = float(semantic_similarity([db_text], input_text)[0])

        results.append({
            "filename": filename,
            "similarity": semantic_score,
            "database_text": db_text
        })

        progress = round((index / total) * 100)

        yield {
            "type": "progress",
            "processed": index,
            "total": total,
            "progress": progress,
            "current_file": filename
        }

    results.sort(key=lambda x: x["similarity"], reverse=True)

    best_result = results[0]
    max_similarity = best_result["similarity"]
    uniqueness = max(0.0, 1 - max_similarity) * 100

    top_results = results[:10]

    yield {
        "type": "result",
        "mode": "semantic",
        "most_similar_file": best_result["filename"],
        "similarity": round(max_similarity * 100, 2),
        "uniqueness": round(uniqueness, 2),
        "input_text": input_text,
        "most_similar_text": best_result["database_text"],
        "common_words": [],

        "top_results": [
            {
                "filename": item["filename"],
                "similarity": round(item["similarity"] * 100, 2),
                "text": item["database_text"]
            }
            for item in top_results
        ],

        "all_results": [
            {
                "filename": item["filename"],
                "similarity": round(item["similarity"] * 100, 2),
                "text": item["database_text"]
            }
            for item in results
        ]
    }